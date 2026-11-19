"""
End-to-End integration test with Gemini Live API.
"""

import os
import pytest
from dotenv import load_dotenv
from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
)

load_dotenv()


async def test_live_session_roundtrip():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not configured, skipping live roundtrip test.")

    config = VoiceConfig(
        api_key=api_key,
        model=os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        voice_name="Puck",
        system_instruction="Reply in exactly one word: 'Acknowledged'.",
    )

    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
    )

    try:
        await session.start()
        assert session.client.is_connected

        # Send text turn
        await session.send_text("Hello Gemini Voice!")

        # Wait for audio or response
        received_audio = False
        import asyncio
        for _ in range(30):
            chunk = output_sink.get_chunk_nowait()
            if chunk:
                received_audio = True
                break
            await asyncio.sleep(0.2)

        assert received_audio, "Expected to receive audio bytes from Gemini Live session"

    except Exception as e:
        # If in offline sandbox without network access, mark skipped
        if "name resolution" in str(e) or "Temporary failure" in str(e):
            pytest.skip(f"Network offline in sandbox: {e}")
        else:
            raise
    finally:
        await session.stop()
