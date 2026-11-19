"""
Example: Basic Python Agent integrated with Gemini Voice AI.
Demonstrates adding custom agent tools, system instructions, and handling live voice events.
"""

import asyncio
import os
from dotenv import load_dotenv

from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
    SimpleAgentAdapter,
)

load_dotenv()


# -----------------------------------------------------------------------------
# 1. Define custom tools for your agent
# -----------------------------------------------------------------------------
def get_current_weather(location: str) -> str:
    """Get current weather forecast for a given city."""
    print(f"\n[Tool Executed] get_current_weather called for: {location}")
    weather_db = {
        "london": "14°C, rainy with light breeze",
        "tokyo": "19°C, clear sky",
        "san francisco": "16°C, foggy",
        "new york": "22°C, sunny",
        "paris": "18°C, partly cloudy",
    }
    return weather_db.get(location.lower().strip(), f"20°C, pleasant in {location}")


def calculate_math(expression: str) -> str:
    """Safely calculate a basic mathematical expression."""
    print(f"\n[Tool Executed] calculate_math called with: {expression}")
    try:
        # Evaluate simple math expressions
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "Error: Unsupported math characters"
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


def check_calendar(date: str) -> str:
    """Check scheduled appointments for a specific date."""
    print(f"\n[Tool Executed] check_calendar called for: {date}")
    return f"On {date}, you have: Team Standup at 10:00 AM, Product Review at 2:30 PM."


# -----------------------------------------------------------------------------
# 2. Main agent orchestration
# -----------------------------------------------------------------------------
async def main():
    config = VoiceConfig(
        model=os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        voice_name="Puck",
        system_instruction=(
            "You are Jarvis, a personal voice assistant. "
            "You have access to tools for weather, math calculations, and calendar. "
            "Always be polite, concise, and helpful."
        ),
    )

    # Use queue-based I/O for headless / network environments
    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    # Create adapter with agent tools
    adapter = SimpleAgentAdapter(
        tools=[get_current_weather, calculate_math, check_calendar],
        system_prompt=config.system_instruction,
    )

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
    )
    adapter.attach(session)

    # Subscribe to live events
    @session.on("state_change")
    def on_state(evt):
        print(f"[State] {evt.old_state.value} -> {evt.new_state.value}")

    @session.on("transcript")
    def on_transcript(evt):
        prefix = "User" if evt.role == "user" else "Assistant"
        final_tag = " (final)" if evt.is_final else ""
        print(f"[{prefix} Speech{final_tag}]: {evt.text}")

    @session.on("tool_call")
    def on_tool_call(evt):
        print(f"[Tool Call Request]: {evt.name}({evt.args})")

    @session.on("tool_result")
    def on_tool_result(evt):
        print(f"[Tool Response Returned]: {evt.result}")

    print("Starting Voice Session with Gemini Live...")
    await session.start()

    # Simulate an interactive dialogue query
    print("\nSending user text query to voice assistant...")
    await session.send_text("What is 45 * 12, and how is the weather in Tokyo right now?")

    # Allow time for model response and tool execution
    await asyncio.sleep(6)

    print("\nConversation history:")
    for turn in session.get_history():
        print(f"  {turn['role'].capitalize()}: {turn['content']}")

    print("\nStopping voice session...")
    await session.stop()
    print("Voice session closed cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
