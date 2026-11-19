"""
Event types and event emitter for the Gemini Voice AI module.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from enum import Enum
from typing import Callable, Dict, List, Any, Optional
from pydantic import BaseModel, Field
import time

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Voice session lifecycle states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    PAUSED = "paused"
    MUTED = "muted"
    CLOSED = "closed"
    ERROR = "error"


class VoiceEvent(BaseModel):
    """Base event model."""
    timestamp: float = Field(default_factory=time.time)
    event_type: str


class StateChangeEvent(VoiceEvent):
    """Emitted when the voice session transitions between states."""
    event_type: str = "state_change"
    old_state: SessionState
    new_state: SessionState


class AudioChunkEvent(VoiceEvent):
    """Emitted when an audio chunk is sent or received."""
    event_type: str = "audio_chunk"
    direction: str  # "in" (user microphone) or "out" (agent speaker)
    data: bytes
    sample_rate: int
    rms: float = 0.0


class TranscriptEvent(VoiceEvent):
    """Emitted when speech is transcribed (user or agent)."""
    event_type: str = "transcript"
    role: str  # "user" or "assistant"
    text: str
    is_final: bool = False


class SpeechActivityEvent(VoiceEvent):
    """Emitted by VAD when user speech starts or ends."""
    event_type: str = "speech_activity"
    activity: str  # "speech_start" or "speech_end"
    rms: float = 0.0
    duration_ms: Optional[float] = None


class InterruptedEvent(VoiceEvent):
    """Emitted when the model response is interrupted by the user."""
    event_type: str = "interrupted"
    reason: str = "user_barge_in"


class ToolCallEvent(VoiceEvent):
    """Emitted when Gemini requests a tool/function call."""
    event_type: str = "tool_call"
    call_id: str
    name: str
    args: Dict[str, Any]


class ToolResultEvent(VoiceEvent):
    """Emitted when a tool execution completes."""
    event_type: str = "tool_result"
    call_id: str
    name: str
    result: Any


class ErrorEvent(VoiceEvent):
    """Emitted on an unhandled error or connection drop."""
    event_type: str = "error"
    error: str
    recoverable: bool = False


class EventEmitter:
    """
    Asynchronous event dispatcher allowing subscription to voice session events.
    Supports both sync and async callback handlers.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Any], Any]]] = {}

    def on(self, event_name: str, handler: Callable[[Any], Any]) -> Callable[[Any], Any]:
        """Subscribe a handler to an event. Can also be used as a decorator."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
        return handler

    def off(self, event_name: str, handler: Callable[[Any], Any]) -> None:
        """Unsubscribe a handler from an event."""
        if event_name in self._handlers and handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    async def emit(self, event_name: str, event_data: Any) -> None:
        """Dispatch an event to all registered listeners asynchronously."""
        handlers = self._handlers.get(event_name, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event_data)
                else:
                    handler(event_data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event_name}': {e}", exc_info=True)
