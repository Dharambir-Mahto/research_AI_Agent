"""
Tests for SimpleAgentAdapter and LangGraphAdapter.
"""

import pytest
from unittest.mock import AsyncMock
from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    SimpleAgentAdapter,
    LangGraphAdapter,
    TranscriptEvent,
)


def sample_tool(query: str) -> str:
    """Sample agent tool."""
    return f"Result for {query}"


def test_simple_agent_adapter_attach():
    adapter = SimpleAgentAdapter(
        tools=[sample_tool],
        system_prompt="Custom agent prompt",
    )
    session = VoiceSession(config=VoiceConfig(api_key="dummy_key"))
    adapter.attach(session)

    assert "sample_tool" in session.tools._tools
    assert session.config.system_instruction == "Custom agent prompt"


async def test_langgraph_adapter_delegation():
    # Mock LangGraph compiled graph
    class MockGraph:
        async def ainvoke(self, payload):
            query = payload["messages"][-1]["content"]
            return {"output": f"Graph answer to: {query}"}

    mock_graph = MockGraph()
    adapter = LangGraphAdapter(
        graph=mock_graph,
        delegate_to_graph=True,
    )

    session = VoiceSession(config=VoiceConfig(api_key="dummy_key"))
    session.send_text = AsyncMock()
    adapter.attach(session)

    # Trigger transcript event
    evt = TranscriptEvent(role="user", text="What is the forecast?", is_final=True)
    await session.events.emit("transcript", evt)

    # Verify session.send_text was called with the graph output
    assert session.send_text.called
    call_args = session.send_text.call_args[0][0]
    assert "Graph answer to: What is the forecast?" in call_args
