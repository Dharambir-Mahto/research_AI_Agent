"""
LangGraph Adapter integrating LangGraph agents and workflows with VoiceSession.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Any, Dict, Callable
from .base import BaseAgentAdapter
from ..session import VoiceSession
from ..events import TranscriptEvent

logger = logging.getLogger(__name__)


class LangGraphAdapter(BaseAgentAdapter):
    """
    Adapter bridging LangGraph compiled graphs and tools to a real-time VoiceSession.
    Supports:
    - Tool synchronization: exposes LangGraph agent tools to Gemini Live.
    - Graph execution mode: forwards transcribed user queries to the graph's `ainvoke`
      and feeds the graph's textual responses back as voice output.
    """

    def __init__(
        self,
        graph: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None,
        delegate_to_graph: bool = False,
        input_key: str = "messages",
        output_extractor: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> None:
        self.graph = graph
        self._tools = tools or []
        self._system_prompt = system_prompt
        self.delegate_to_graph = delegate_to_graph
        self.input_key = input_key
        self.output_extractor = output_extractor or self._default_output_extractor

    def get_tools(self) -> List[Any]:
        return self._tools

    def get_system_prompt(self) -> Optional[str]:
        return self._system_prompt

    def _default_output_extractor(self, result: Any) -> str:
        """Extract text content from standard LangGraph agent state outputs."""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            messages = result.get(self.input_key) or result.get("output") or result.get("messages")
            if messages and isinstance(messages, list):
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    return str(last_msg.content)
                elif isinstance(last_msg, dict):
                    return str(last_msg.get("content", ""))
            if "output" in result:
                return str(result["output"])
        return str(result)

    def attach(self, session: VoiceSession) -> None:
        """Connect tools and graph processing to VoiceSession."""
        # 1. Register tools if present
        for tool in self._tools:
            session.register_tool(tool)

        if self._system_prompt:
            session.config.system_instruction = self._system_prompt

        # 2. Graph invocation hook if delegate_to_graph is enabled
        if self.delegate_to_graph and self.graph is not None:
            _processing = False

            @session.on("transcript")
            async def _on_user_query(evt: TranscriptEvent):
                nonlocal _processing
                if _processing:
                    return

                if evt.is_final and evt.role == "user" and evt.text.strip():
                    _processing = True
                    logger.info(f"LangGraphAdapter routing query to graph: {evt.text}")
                    try:
                        # Construct input message for graph
                        payload = {self.input_key: [{"role": "user", "content": evt.text}]}
                        if hasattr(self.graph, "ainvoke"):
                            res = await self.graph.ainvoke(payload)
                        elif hasattr(self.graph, "invoke"):
                            res = self.graph.invoke(payload)
                        else:
                            raise ValueError("Graph does not have invoke or ainvoke method.")

                        output_text = self.output_extractor(res)
                        logger.info(f"LangGraph result: {output_text}")
                        # Feed response back into voice session for Gemini Live speech synthesis
                        # We send with record_transcript=False so it doesn't re-trigger user speech
                        await session.send_text(
                            f"Please say this to the user in natural spoken voice: {output_text}",
                            role="assistant",
                            record_transcript=False,
                        )
                    except Exception as e:
                        logger.error(f"Error invoking LangGraph: {e}", exc_info=True)
                    finally:
                        _processing = False
