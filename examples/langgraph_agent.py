"""
Example: Integrating a LangGraph Agent with the Gemini Voice AI module.
Demonstrates StateGraph workflow orchestration with real-time bidirectional voice I/O.
"""

from __future__ import annotations

import asyncio
import os
from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
    LangGraphAdapter,
)

load_dotenv()


# -----------------------------------------------------------------------------
# 1. Define LangGraph State & Agent Nodes
# -----------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Sequence[dict]
    agent_thought: str
    output: str


def analyzer_node(state: AgentState) -> dict:
    """Analyze incoming user query and determine intent."""
    last_message = state["messages"][-1]["content"]
    print(f"\n[LangGraph: analyzer_node] Processing query: '{last_message}'")
    
    thought = f"User is asking about '{last_message}'. Querying knowledge base."
    return {"agent_thought": thought}


def resolver_node(state: AgentState) -> dict:
    """Resolve query and generate concise voice-ready response."""
    thought = state.get("agent_thought", "")
    last_message = state["messages"][-1]["content"].lower()

    if "product" in last_message or "pricing" in last_message:
        reply = "Our Enterprise plan is $49 per user per month, with full 24/7 priority support and custom integrations."
    elif "status" in last_message or "health" in last_message:
        reply = "All backend services and API gateways are currently operating with 99.98% uptime."
    else:
        reply = f"Thank you for your question about '{state['messages'][-1]['content']}'. All systems are running optimally."

    print(f"[LangGraph: resolver_node] Formulated reply: '{reply}'")
    return {"output": reply}


# -----------------------------------------------------------------------------
# 2. Build and compile the LangGraph workflow
# -----------------------------------------------------------------------------
def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("analyzer", analyzer_node)
    workflow.add_node("resolver", resolver_node)

    workflow.set_entry_point("analyzer")
    workflow.add_edge("analyzer", "resolver")
    workflow.add_edge("resolver", END)

    return workflow.compile()


# -----------------------------------------------------------------------------
# 3. Main execution bridging LangGraph with VoiceSession
# -----------------------------------------------------------------------------
async def main():
    print("Building LangGraph workflow...")
    graph = build_agent_graph()

    config = VoiceConfig(
        model=os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        voice_name="Kore",
        system_instruction=(
            "You are the voice interface for an enterprise workflow agent. "
            "Speak clearly, authoritatively, and concisely."
        ),
    )

    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
    )

    # Attach LangGraph with query delegation enabled
    adapter = LangGraphAdapter(
        graph=graph,
        delegate_to_graph=True,
        input_key="messages",
    )
    adapter.attach(session)

    @session.on("state_change")
    def on_state(evt):
        print(f"[State] {evt.old_state.value} -> {evt.new_state.value}")

    @session.on("transcript")
    def on_transcript(evt):
        role = "User" if evt.role == "user" else "Assistant"
        tag = " (final)" if evt.is_final else ""
        print(f"[{role} Speech{tag}]: {evt.text}")

    print("Connecting VoiceSession to Gemini Live...")
    await session.start()

    # Simulate a user query
    user_query = "Can you give me the product pricing and current platform status?"
    print(f"\nSimulating user voice transcription: '{user_query}'")
    await session.send_text(user_query)

    # Allow time for LangGraph workflow and Gemini speech synthesis
    await asyncio.sleep(6)

    print("\nStopping session...")
    await session.stop()
    print("LangGraph Voice Agent finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
