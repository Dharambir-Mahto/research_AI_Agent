"""
SimpleAgentAdapter for connecting standard Python agents and functions.
"""

from __future__ import annotations

from typing import Optional, List, Callable, Any, Dict
from .base import BaseAgentAdapter
from ..session import VoiceSession
from ..events import TranscriptEvent, ToolCallEvent


class SimpleAgentAdapter(BaseAgentAdapter):
    """
    Adapter for vanilla Python agents. Accepts python tools, system prompt,
    and optional callbacks for speech events and tool executions.
    """

    def __init__(
        self,
        tools: Optional[List[Callable[..., Any]]] = None,
        system_prompt: Optional[str] = None,
        on_user_message: Optional[Callable[[str], Any]] = None,
        on_agent_message: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._tools = tools or []
        self._system_prompt = system_prompt
        self._on_user_message = on_user_message
        self._on_agent_message = on_agent_message

    def get_tools(self) -> List[Any]:
        return self._tools

    def get_system_prompt(self) -> Optional[str]:
        return self._system_prompt

    def attach(self, session: VoiceSession) -> None:
        """Register agent tools and bind event listeners to VoiceSession."""
        for tool_fn in self._tools:
            session.register_tool(tool_fn)

        if self._system_prompt:
            session.config.system_instruction = self._system_prompt

        @session.on("transcript")
        async def _handle_transcript(evt: TranscriptEvent):
            if evt.is_final:
                if evt.role == "user" and self._on_user_message:
                    res = self._on_user_message(evt.text)
                    if hasattr(res, "__await__"):
                        await res
                elif evt.role == "assistant" and self._on_agent_message:
                    res = self._on_agent_message(evt.text)
                    if hasattr(res, "__await__"):
                        await res
