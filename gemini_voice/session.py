"""
Top-level VoiceSession orchestrating Gemini Live bidirectional streaming,
audio pipeline, tool calling, transcripts, and session lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List, Union

from .config import VoiceConfig
from .events import (
    EventEmitter,
    SessionState,
    StateChangeEvent,
    AudioChunkEvent,
    TranscriptEvent,
    SpeechActivityEvent,
    InterruptedEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
)
from .audio.processor import PCMProcessor
from .audio.sources import AudioInputSource
from .audio.sinks import AudioOutputSink
from .client import GeminiLiveClient
from .streaming import StreamingManager
from .transcripts import TranscriptHandler, TranscriptTurn
from .tools import ToolRegistry, VoiceTool

logger = logging.getLogger(__name__)


class VoiceSession:
    """
    Main developer-facing interface for creating real-time Gemini Voice AI sessions.
    Plug-and-play into any existing AI Agent or application.
    """

    def __init__(
        self,
        config: Optional[VoiceConfig] = None,
        input_source: Optional[AudioInputSource] = None,
        output_sink: Optional[AudioOutputSink] = None,
        tools: Optional[List[Union[Callable[..., Any], VoiceTool, Any]]] = None,
        system_instruction: Optional[str] = None,
    ) -> None:
        self.config = config or VoiceConfig()
        if system_instruction:
            self.config.system_instruction = system_instruction

        self.events = EventEmitter()
        self.tools = ToolRegistry()
        if tools:
            for t in tools:
                self.tools.register(t)

        self._state = SessionState.IDLE
        self._input_source = input_source
        self._output_sink = output_sink

        self.transcripts = TranscriptHandler(
            on_transcript_update=self._handle_transcript_update
        )

        self.client = GeminiLiveClient(
            config=self.config,
            tool_registry=self.tools,
            on_audio=self._handle_client_audio,
            on_text=self._handle_client_text,
            on_tool_call=self._handle_client_tool_call,
            on_interrupted=self._handle_client_interrupted,
            on_turn_complete=self._handle_client_turn_complete,
            on_error=self._handle_client_error,
        )

        self.streaming = StreamingManager(
            config=self.config,
            client=self.client,
            input_source=self._input_source,
            output_sink=self._output_sink,
            on_speech_start=self._handle_speech_start,
            on_speech_end=self._handle_speech_end,
            on_audio_in_level=self._handle_audio_in_level,
            on_audio_out_chunk=self._handle_audio_out_chunk,
            on_interruption_needed=self.interrupt,
        )

    @property
    def state(self) -> SessionState:
        """Current session lifecycle state."""
        return self._state

    def _set_state(self, new_state: SessionState) -> None:
        if self._state == new_state:
            return
        old_state = self._state
        self._state = new_state
        logger.info(f"VoiceSession transition: {old_state.value} -> {new_state.value}")
        asyncio.create_task(
            self.events.emit(
                "state_change",
                StateChangeEvent(old_state=old_state, new_state=new_state),
            )
        )

    # -------------------------------------------------------------------------
    # Public Lifecycle and Control APIs
    # -------------------------------------------------------------------------

    async def start(self) -> None:
        """
        Starts the voice session: connects to Gemini Live API and starts the audio pipeline.
        """
        if self._state not in (SessionState.IDLE, SessionState.CLOSED):
            logger.warning(f"Session already running in state: {self._state}")
            return

        self._set_state(SessionState.CONNECTING)
        try:
            await self.client.connect()
            await self.streaming.start()
            self._set_state(SessionState.LISTENING)
        except Exception as e:
            self._set_state(SessionState.ERROR)
            await self.events.emit("error", ErrorEvent(error=str(e), recoverable=False))
            raise

    async def stop(self) -> None:
        """
        Stops the voice session and releases all resources.
        """
        if self._state == SessionState.CLOSED:
            return

        logger.info("Stopping VoiceSession...")
        await self.streaming.stop()
        await self.client.close()
        self._set_state(SessionState.CLOSED)

    def pause(self) -> None:
        """Pauses processing of incoming audio without dropping the live session."""
        if self._state in (SessionState.LISTENING, SessionState.SPEAKING):
            self.streaming.set_paused(True)
            self._set_state(SessionState.PAUSED)

    def resume(self) -> None:
        """Resumes audio processing from a paused state."""
        if self._state == SessionState.PAUSED:
            self.streaming.set_paused(False)
            self._set_state(SessionState.LISTENING)

    def mute(self) -> None:
        """Mutes audio input (transmits silence to model)."""
        self.streaming.set_muted(True)
        if self._state != SessionState.PAUSED:
            self._set_state(SessionState.MUTED)

    def unmute(self) -> None:
        """Unmutes audio input."""
        self.streaming.set_muted(False)
        if self._state == SessionState.MUTED:
            self._set_state(SessionState.LISTENING)

    async def interrupt(self) -> None:
        """
        Immediately interrupts model speech (barge-in):
        Flushes audio output buffers and resets speaking state.
        """
        if self._state == SessionState.SPEAKING:
            logger.info("Interrupting active model speech...")
            await self.streaming.flush_output()
            self._set_state(SessionState.LISTENING)
            await self.events.emit("interrupted", InterruptedEvent())

    async def send_text(self, text: str, role: str = "user", record_transcript: bool = True) -> None:
        """
        Send text directly into the voice session (e.g., user typed message or agent injection).
        """
        if record_transcript:
            if role == "assistant":
                self.transcripts.append_assistant_delta(text, is_final=True)
            else:
                self.transcripts.append_user_delta(text, is_final=True)

        self._set_state(SessionState.THINKING)
        await self.client.send_text(text)

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """
        Send a chunk of raw 16kHz 16-bit mono PCM bytes directly into the session.
        Useful when bypassing AudioInputSource.
        """
        if self._state == SessionState.MUTED:
            pcm_bytes = PCMProcessor.mute_chunk(pcm_bytes)

        if self.config.vad_enabled:
            self.streaming.vad.process_frame(pcm_bytes, self.config.chunk_size_ms)

        await self.client.send_audio(pcm_bytes)

    def register_tool(
        self,
        func_or_tool: Union[Callable[..., Any], VoiceTool, Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> VoiceTool:
        """Register a new tool callable with the voice session."""
        return self.tools.register(func_or_tool, name=name, description=description)

    def on(self, event_name: str, handler: Optional[Callable[[Any], Any]] = None):
        """Subscribe to an event or use as a decorator."""
        if handler is None:
            def decorator(fn: Callable[[Any], Any]):
                self.events.on(event_name, fn)
                return fn
            return decorator
        return self.events.on(event_name, handler)

    def get_history(self, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """Retrieve conversation transcripts formatted as role/content pairs."""
        return self.transcripts.get_conversation_context(max_turns=max_turns)

    # -------------------------------------------------------------------------
    # Internal Event Routing and Callbacks
    # -------------------------------------------------------------------------

    async def _handle_client_audio(self, data: bytes, mime_type: str) -> None:
        """Received output audio chunk from Gemini Live."""
        if self._state != SessionState.SPEAKING and self._state != SessionState.MUTED:
            self._set_state(SessionState.SPEAKING)

        await self.streaming.handle_output_audio(data, mime_type)

    async def _handle_client_text(self, role: str, text: str, is_final: bool) -> None:
        """Received text/transcript chunk from Gemini Live."""
        if role == "assistant":
            self.transcripts.append_assistant_delta(text, is_final=is_final)
        else:
            self.transcripts.append_user_delta(text, is_final=is_final)

    async def _handle_client_turn_complete(self) -> None:
        """Model finished speaking current turn."""
        self.transcripts.complete_current_turn("assistant")
        if self._state == SessionState.SPEAKING:
            self._set_state(SessionState.LISTENING)

    async def _handle_client_interrupted(self) -> None:
        """Gemini confirmed barge-in interruption."""
        await self.streaming.flush_output()
        if self._state == SessionState.SPEAKING:
            self._set_state(SessionState.LISTENING)
        await self.events.emit("interrupted", InterruptedEvent())

    async def _handle_client_tool_call(self, call_id: str, name: str, args: Dict[str, Any]) -> None:
        """Execute tool requested by Gemini Live."""
        self._set_state(SessionState.THINKING)
        await self.events.emit(
            "tool_call",
            ToolCallEvent(call_id=call_id, name=name, args=args),
        )

        response = await self.tools.execute_tool(name, call_id, args)

        await self.events.emit(
            "tool_result",
            ToolResultEvent(call_id=call_id, name=name, result=response.response),
        )

        # Dispatch response back to Gemini Live
        await self.client.send_tool_response(response)

    async def _handle_client_error(self, error: Exception) -> None:
        """Error reported by Gemini client."""
        logger.error(f"VoiceSession client error: {error}")
        self._set_state(SessionState.ERROR)
        await self.events.emit(
            "error",
            ErrorEvent(error=str(error), recoverable=False),
        )

    def _handle_transcript_update(self, turn: TranscriptTurn) -> None:
        asyncio.create_task(
            self.events.emit(
                "transcript",
                TranscriptEvent(
                    role=turn.role,
                    text=turn.text,
                    is_final=turn.is_final,
                ),
            )
        )

    async def _handle_speech_start(self, rms: float) -> None:
        await self.events.emit(
            "speech_activity",
            SpeechActivityEvent(activity="speech_start", rms=rms),
        )

    async def _handle_speech_end(self, duration_ms: float, rms: float) -> None:
        self.transcripts.complete_current_turn("user")
        await self.events.emit(
            "speech_activity",
            SpeechActivityEvent(activity="speech_end", duration_ms=duration_ms, rms=rms),
        )
        if self._state == SessionState.LISTENING:
            self._set_state(SessionState.THINKING)

    async def _handle_audio_in_level(self, rms: float) -> None:
        await self.events.emit(
            "audio_level_in",
            {"rms": rms},
        )

    async def _handle_audio_out_chunk(self, data: bytes) -> None:
        rms = PCMProcessor.compute_rms(data)
        await self.events.emit(
            "audio_chunk_out",
            AudioChunkEvent(
                direction="out",
                data=data,
                sample_rate=self.config.output_sample_rate,
                rms=rms,
            ),
        )
