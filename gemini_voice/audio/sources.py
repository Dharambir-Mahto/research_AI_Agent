"""
Audio input sources: Abstract base, Queue-based, File-based, Simulated, and Local Microphone.
"""

from __future__ import annotations

import abc
import asyncio
import math
import struct
import time
import wave
from typing import Optional, AsyncIterator
import logging

logger = logging.getLogger(__name__)


class AudioInputSource(abc.ABC):
    """Abstract interface for audio input streams providing 16-bit PCM chunks."""

    @abc.abstractmethod
    async def open(self) -> None:
        """Initialize the audio source."""
        pass

    @abc.abstractmethod
    async def read_chunk(self) -> Optional[bytes]:
        """Read the next chunk of raw PCM bytes. Returns None when exhausted or closed."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Release underlying resources."""
        pass

    async def stream(self) -> AsyncIterator[bytes]:
        """Async generator yielding chunks until closed."""
        while True:
            chunk = await self.read_chunk()
            if chunk is None:
                break
            yield chunk


class AsyncQueueAudioSource(AudioInputSource):
    """
    Queue-based audio input source. Ideal for WebSocket connections,
    network clients, or inter-thread audio ingestion.
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=maxsize)
        self._is_open = False

    async def open(self) -> None:
        self._is_open = True

    async def push(self, pcm_bytes: bytes) -> None:
        """Push an incoming audio chunk into the input buffer."""
        if self._is_open:
            await self._queue.put(pcm_bytes)

    def push_nowait(self, pcm_bytes: bytes) -> bool:
        """Push chunk without blocking. Returns False if queue is full."""
        if not self._is_open:
            return False
        try:
            self._queue.put_nowait(pcm_bytes)
            return True
        except asyncio.QueueFull:
            logger.warning("AsyncQueueAudioSource queue full, dropping frame.")
            return False

    async def read_chunk(self) -> Optional[bytes]:
        if not self._is_open and self._queue.empty():
            return None
        item = await self._queue.get()
        return item

    async def close(self) -> None:
        self._is_open = False
        # Put sentinel to unblock any pending reader
        await self._queue.put(None)


class FileAudioSource(AudioInputSource):
    """
    Reads audio from a WAV file or raw PCM file and streams chunks at real-time pacing.
    """

    def __init__(self, filepath: str, chunk_duration_ms: int = 100) -> None:
        self.filepath = filepath
        self.chunk_duration_ms = chunk_duration_ms
        self._wav_file: Optional[wave.Wave_read] = None
        self._chunk_frames: int = 0
        self._frame_interval_sec: float = chunk_duration_ms / 1000.0

    async def open(self) -> None:
        self._wav_file = wave.open(self.filepath, "rb")
        sample_rate = self._wav_file.getframerate()
        self._chunk_frames = int(sample_rate * (self.chunk_duration_ms / 1000.0))

    async def read_chunk(self) -> Optional[bytes]:
        if not self._wav_file:
            return None
        # Paced delay
        await asyncio.sleep(self._frame_interval_sec)
        frames = self._wav_file.readframes(self._chunk_frames)
        if not frames:
            return None
        return frames

    async def close(self) -> None:
        if self._wav_file:
            self._wav_file.close()
            self._wav_file = None


class SimulatedAudioSource(AudioInputSource):
    """
    Generates synthetic sine wave tones or silence frames for automated testing.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frequency_hz: float = 440.0,
        chunk_duration_ms: int = 100,
        max_chunks: Optional[int] = None,
        amplitude: float = 0.5
    ) -> None:
        self.sample_rate = sample_rate
        self.frequency_hz = frequency_hz
        self.chunk_duration_ms = chunk_duration_ms
        self.max_chunks = max_chunks
        self.amplitude = amplitude
        self._chunk_count = 0
        self._chunk_samples = int(sample_rate * (chunk_duration_ms / 1000.0))
        self._interval = chunk_duration_ms / 1000.0
        self._phase = 0.0
        self._is_open = False

    async def open(self) -> None:
        self._is_open = True
        self._chunk_count = 0

    async def read_chunk(self) -> Optional[bytes]:
        if not self._is_open:
            return None
        if self.max_chunks is not None and self._chunk_count >= self.max_chunks:
            return None

        await asyncio.sleep(self._interval)
        buf = bytearray(self._chunk_samples * 2)
        angular_step = 2.0 * math.pi * self.frequency_hz / self.sample_rate

        for i in range(self._chunk_samples):
            val = int(math.sin(self._phase) * self.amplitude * 32767)
            val = max(-32768, min(32767, val))
            struct.pack_into("<h", buf, i * 2, val)
            self._phase += angular_step
            if self._phase > 2.0 * math.pi:
                self._phase -= 2.0 * math.pi

        self._chunk_count += 1
        return bytes(buf)

    async def close(self) -> None:
        self._is_open = False


class LocalMicrophoneSource(AudioInputSource):
    """
    Captures live audio from the physical hardware microphone using PyAudio or sounddevice.
    Gracefully handles environment where physical sound card or PortAudio is unavailable.
    """

    def __init__(self, sample_rate: int = 16000, chunk_duration_ms: int = 100) -> None:
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self._chunk_samples = int(sample_rate * (chunk_duration_ms / 1000.0))
        self._stream = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_open = False

    async def open(self) -> None:
        self._loop = asyncio.get_running_loop()
        try:
            import sounddevice as sd  # type: ignore

            def callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Audio input status: {status}")
                pcm = indata.tobytes()
                if self._loop and self._is_open:
                    self._loop.call_soon_threadsafe(self._queue.put_nowait, pcm)

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._chunk_samples,
                callback=callback,
            )
            self._stream.start()
            self._is_open = True
        except (ImportError, OSError) as e:
            raise RuntimeError(
                f"LocalMicrophoneSource cannot initialize: {e}. "
                "Ensure `sounddevice` and PortAudio are installed, "
                "or use `AsyncQueueAudioSource` / WebSocket streaming."
            ) from e

    async def read_chunk(self) -> Optional[bytes]:
        if not self._is_open:
            return None
        return await self._queue.get()

    async def close(self) -> None:
        self._is_open = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
