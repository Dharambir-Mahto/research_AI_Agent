"""
Live speech transcript handler and conversation context manager.
"""

from __future__ import annotations

import time
from typing import List, Optional, Callable, Dict, Any
from pydantic import BaseModel, Field


class TranscriptTurn(BaseModel):
    """Represents a spoken turn in the voice dialogue."""
    role: str  # "user" or "assistant"
    text: str
    is_final: bool = False
    timestamp: float = Field(default_factory=time.time)


class TranscriptHandler:
    """
    Manages real-time streaming transcripts and conversation dialogue history.
    """

    def __init__(self, on_transcript_update: Optional[Callable[[TranscriptTurn], None]] = None) -> None:
        self.on_transcript_update = on_transcript_update
        self.history: List[TranscriptTurn] = []
        self._current_user_text: str = ""
        self._current_assistant_text: str = ""

    def append_user_delta(self, delta: str, is_final: bool = False) -> TranscriptTurn:
        """Process incoming user speech transcription chunk."""
        self._current_user_text += delta
        turn = TranscriptTurn(
            role="user",
            text=self._current_user_text,
            is_final=is_final,
        )
        if is_final:
            self.history.append(turn)
            self._current_user_text = ""

        if self.on_transcript_update:
            self.on_transcript_update(turn)
        return turn

    def append_assistant_delta(self, delta: str, is_final: bool = False) -> TranscriptTurn:
        """Process incoming assistant speech transcription chunk."""
        self._current_assistant_text += delta
        turn = TranscriptTurn(
            role="assistant",
            text=self._current_assistant_text,
            is_final=is_final,
        )
        if is_final:
            self.history.append(turn)
            self._current_assistant_text = ""

        if self.on_transcript_update:
            self.on_transcript_update(turn)
        return turn

    def complete_current_turn(self, role: str) -> Optional[TranscriptTurn]:
        """Force finalize current speech segment for a role."""
        if role == "user" and self._current_user_text:
            turn = TranscriptTurn(role="user", text=self._current_user_text, is_final=True)
            self.history.append(turn)
            self._current_user_text = ""
            if self.on_transcript_update:
                self.on_transcript_update(turn)
            return turn
        elif role == "assistant" and self._current_assistant_text:
            turn = TranscriptTurn(role="assistant", text=self._current_assistant_text, is_final=True)
            self.history.append(turn)
            self._current_assistant_text = ""
            if self.on_transcript_update:
                self.on_transcript_update(turn)
            return turn
        return None

    def clear(self) -> None:
        """Clear conversation transcripts."""
        self.history.clear()
        self._current_user_text = ""
        self._current_assistant_text = ""

    def get_conversation_context(self, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """Return formatted dialogue history for context injection."""
        items = self.history if max_turns is None else self.history[-max_turns:]
        return [{"role": t.role, "content": t.text} for t in items]
