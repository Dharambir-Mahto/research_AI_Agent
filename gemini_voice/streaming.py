"""
Streaming manager coordinating bidirectional audio flows, VAD, and flow controls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Any

from .config import VoiceConfig
from .audio.processor import PCMProcessor, VoiceActivityDetector
from .audio.sources import AudioInputSource
from .audio.sinks import AudioOutputSink
from .client import GeminiLiveClient

logger = logging.getLogger(__name__)


class StreamingManager:
    """
    Manages the real-time audio pipeline:
    - Ingests audio from AudioInputSource
    - Runs VAD and RMS level tracking
    - Sends PCM frames to GeminiLiveClient
    - Receives model output audio and forwards to AudioOutputSink
    - Handles pause, mute, and interruption flushes
    """

    def __init__(
        self,
        config: VoiceConfig,
        client: GeminiLiveClient,
        input_source: Optional[AudioInputSource] = None,
        output_sink: Optional[AudioOutputSink] = None,
        on_speech_start: Optional[Callable[[float], Any]] = None,
        on_speech_end: Optional[Callable[[float, float], Any]] = None,
        on_audio_in_level: Optional[Callable[[float], Any]] = None,
        on_audio_out_chunk: Optional[Callable[[bytes], Any]] = None,
        on_interruption_needed: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self.client = client
        self.input_source = input_source
        self.output_sink = output_sink
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_audio_in_level = on_audio_in_level
        self.on_audio_out_chunk = on_audio_out_chunk
        self.on_interruption_needed = on_interruption_needed

        self._is_streaming = False
        self._is_paused = False
        self._is_muted = False
        self._input_task: Optional[asyncio.Task] = None

        self.vad = VoiceActivityDetector(
            threshold_rms=config.vad_threshold_rms,
            silence_duration_ms=config.vad_silence_duration_ms,
            min_speech_duration_ms=config.vad_min_speech_duration_ms,
            on_speech_start=self._handle_vad_speech_start,
            on_speech_end=self._handle_vad_speech_end,
        )

    @property
    def is_streaming(self) -> bool:
        return self._is_streaming

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_paused(self, paused: bool) -> None:
        """Pause or resume input streaming."""
        self._is_paused = paused
        logger.info(f"Streaming paused state set to: {paused}")

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute microphone (sends silence while muted)."""
        self._is_muted = muted
        logger.info(f"Streaming muted state set to: {muted}")

    def _handle_vad_speech_start(self, rms: float) -> None:
        logger.debug(f"VAD: Speech start detected (RMS={rms:.4f})")
        if self.on_speech_start:
            res = self.on_speech_start(rms)
            if asyncio.iscoroutine(res):
                asyncio.create_task(res)

        # Trigger interruption if model is currently speaking
        if self.on_interruption_needed:
            res = self.on_interruption_needed()
            if asyncio.iscoroutine(res):
                asyncio.create_task(res)

    def _handle_vad_speech_end(self, duration_ms: float, rms: float) -> None:
        logger.debug(f"VAD: Speech end detected (duration={duration_ms:.1f}ms, RMS={rms:.4f})")
        if self.on_speech_end:
            res = self.on_speech_end(duration_ms, rms)
            if asyncio.iscoroutine(res):
                asyncio.create_task(res)

    async def start(self) -> None:
        """Initialize input/output components and start input streaming task."""
        if self._is_streaming:
            return

        if self.input_source:
            await self.input_source.open()
        if self.output_sink:
            await self.output_sink.open()

        self._is_streaming = True
        self.vad.reset()

        if self.input_source:
            self._input_task = asyncio.create_task(self._input_stream_worker())
        logger.info("StreamingManager pipeline started.")

    async def _input_stream_worker(self) -> None:
        """Continuously reads frames from input source and forwards to Gemini Live."""
        chunk_ms = self.config.chunk_size_ms

        while self._is_streaming and self.input_source:
            try:
                chunk = await self.input_source.read_chunk()
                if chunk is None:
                    # Source finished or closed
                    break

                if self._is_paused:
                    continue

                if self._is_muted:
                    # Transmit silence or discard
                    chunk = PCMProcessor.mute_chunk(chunk)

                # Run VAD if enabled
                if self.config.vad_enabled and not self._is_muted:
                    self.vad.process_frame(chunk, frame_duration_ms=chunk_ms)

                # Report input audio level
                if self.on_audio_in_level:
                    rms = PCMProcessor.compute_rms(chunk)
                    res = self.on_audio_in_level(rms)
                    if asyncio.iscoroutine(res):
                        await res

                # Stream to Gemini Live
                if self.client.is_connected:
                    await self.client.send_audio(chunk)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading/sending input audio chunk: {e}", exc_info=True)
                await asyncio.sleep(0.05)

    async def handle_output_audio(self, data: bytes, mime_type: str) -> None:
        """Route audio generated by Gemini to output sinks and callbacks."""
        if self.output_sink:
            await self.output_sink.write_chunk(data)

        if self.on_audio_out_chunk:
            res = self.on_audio_out_chunk(data)
            if asyncio.iscoroutine(res):
                await res

    async def flush_output(self) -> None:
        """Flush output buffers immediately upon user interruption."""
        if self.output_sink:
            await self.output_sink.flush()

    async def stop(self) -> None:
        """Stop streaming pipeline and release resources."""
        self._is_streaming = False
        if self._input_task and not self._input_task.done():
            self._input_task.cancel()
            try:
                await self._input_task
            except asyncio.CancelledError:
                pass

        if self.input_source:
            try:
                await self.input_source.close()
            except Exception as e:
                logger.debug(f"Error closing input source: {e}")

        if self.output_sink:
            try:
                await self.output_sink.close()
            except Exception as e:
                logger.debug(f"Error closing output sink: {e}")

        logger.info("StreamingManager pipeline stopped.")
