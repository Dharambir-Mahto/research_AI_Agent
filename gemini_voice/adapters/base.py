"""
Base Agent Adapter interface for hooking external agents into Voice AI sessions.
"""

from __future__ import annotations

import abc
from typing import Optional, List, Any
from ..session import VoiceSession
from ..tools import VoiceTool


class BaseAgentAdapter(abc.ABC):
    """
    Abstract adapter for bridging an arbitrary AI Agent framework
    (e.g., custom Python agent, LangGraph, CrewAI, AutoGen) with a VoiceSession.
    """

    @abc.abstractmethod
    def get_tools(self) -> List[Any]:
        """Return tools exposed by the agent to Gemini Live."""
        return []

    @abc.abstractmethod
    def get_system_prompt(self) -> Optional[str]:
        """Return system prompt / personality configured for the agent."""
        return None

    @abc.abstractmethod
    def attach(self, session: VoiceSession) -> None:
        """Bind agent listeners and tool definitions to the active VoiceSession."""
        pass
