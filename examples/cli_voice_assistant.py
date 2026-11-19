"""
CLI Voice Assistant Demonstration.
Interactive terminal voice assistant supporting keyboard input, audio streaming,
barge-in interruption, state displays, and tool calling.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dotenv import load_dotenv

from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
    LocalMicrophoneSource,
    LocalSpeakerSink,
)

load_dotenv()


def search_knowledge_base(topic: str) -> str:
    """Search internal documentation for a given topic."""
    docs = {
        "architecture": "The system uses an asynchronous event-driven pipeline with Gemini Live.",
        "deployment": "Deploy with Docker or Kubernetes. Set GEMINI_API_KEY as an env variable.",
        "latency": "Audio round-trip latency is typically under 400 milliseconds.",
    }
    return docs.get(topic.lower(), f"Information on '{topic}' is available in section 4.2 of the docs.")


async def main():
    print("=" * 65)
    print("      🎙️  GEMINI LIVE VOICE AI ASSISTANT (CLI DEMO)  🎙️      ")
    print("=" * 65)

    use_local_hardware = "--hardware" in sys.argv

    input_source = None
    output_sink = None

    if use_local_hardware:
        try:
            print("Attempting to initialize hardware microphone & speakers...")
            input_source = LocalMicrophoneSource()
            output_sink = LocalSpeakerSink()
            print("Hardware audio initialized successfully!")
        except Exception as e:
            print(f"Hardware audio not available ({e}). Falling back to Queue mode.")
            input_source = AsyncQueueAudioSource()
            output_sink = AsyncQueueAudioSink()
    else:
        input_source = AsyncQueueAudioSource()
        output_sink = AsyncQueueAudioSink()

    config = VoiceConfig(
        model=os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        voice_name="Puck",
        system_instruction="You are a friendly, witty, and concise AI assistant communicating over voice.",
    )

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
        tools=[search_knowledge_base],
    )

    @session.on("state_change")
    def on_state(evt):
        print(f"\n[Status: {evt.new_state.value.upper()}]")

    @session.on("transcript")
    def on_transcript(evt):
        role = "👤 You" if evt.role == "user" else "🤖 Assistant"
        if evt.is_final:
            print(f"\n{role}: {evt.text}")

    @session.on("tool_call")
    def on_tool(evt):
        print(f"\n⚙️  Tool Call: {evt.name}({evt.args})")

    @session.on("interrupted")
    def on_interrupt(evt):
        print("\n⚡ [Assistant speech interrupted by user barge-in!]")

    print("\nConnecting to Gemini Live API...")
    await session.start()
    print("Connected! Type a query, or commands: /mute, /unmute, /pause, /resume, /interrupt, /history, /exit")

    loop = asyncio.get_running_loop()

    try:
        while True:
            # Non-blocking terminal input
            prompt = await loop.run_in_executor(None, input, "\nPrompt > ")
            prompt = prompt.strip()

            if not prompt:
                continue

            if prompt == "/exit":
                break
            elif prompt == "/mute":
                session.mute()
                print("Microphone muted.")
            elif prompt == "/unmute":
                session.unmute()
                print("Microphone unmuted.")
            elif prompt == "/pause":
                session.pause()
                print("Voice session paused.")
            elif prompt == "/resume":
                session.resume()
                print("Voice session resumed.")
            elif prompt == "/interrupt":
                await session.interrupt()
            elif prompt == "/history":
                print("\nDialogue Context:")
                for turn in session.get_history():
                    print(f"  {turn['role']}: {turn['text']}")
            else:
                await session.send_text(prompt)
                # Wait briefly for live response
                await asyncio.sleep(2.0)

    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\nShutting down voice session...")
        await session.stop()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
