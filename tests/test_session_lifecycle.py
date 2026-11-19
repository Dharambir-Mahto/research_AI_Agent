"""
Tests for VoiceSession lifecycle, controls (pause, mute, interrupt), and state machine.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    SessionState,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
)


async def test_session_state_transitions():
    config = VoiceConfig(api_key="test_dummy_key")
    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
    )

    # Initial state
    assert session.state == SessionState.IDLE

    # Mock client connection so it doesn't make network calls in unit test
    session.client.connect = AsyncMock()
    session.client.close = AsyncMock()
    session.streaming.start = AsyncMock()
    session.streaming.stop = AsyncMock()

    # Track state events
    states_observed = []
    session.on("state_change", lambda evt: states_observed.append(evt.new_state))

    await session.start()
    assert session.state == SessionState.LISTENING

    # Mute
    session.mute()
    assert session.state == SessionState.MUTED
    assert session.streaming.is_muted is True

    # Unmute
    session.unmute()
    assert session.state == SessionState.LISTENING
    assert session.streaming.is_muted is False

    # Pause
    session.pause()
    assert session.state == SessionState.PAUSED
    assert session.streaming.is_paused is True

    # Resume
    session.resume()
    assert session.state == SessionState.LISTENING
    assert session.streaming.is_paused is False

    # Stop
    await session.stop()
    assert session.state == SessionState.CLOSED


async def test_session_barge_in_interruption():
    config = VoiceConfig(api_key="test_dummy_key")
    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
    )

    # Put dummy audio in output sink
    await output_sink.open()
    await output_sink.write_chunk(b"\x01\x02\x03\x04")

    # Set state to SPEAKING
    session._set_state(SessionState.SPEAKING)
    assert session.state == SessionState.SPEAKING

    interrupted_events = []
    session.on("interrupted", lambda evt: interrupted_events.append(evt))

    await session.interrupt()

    # State returns to LISTENING and buffers flushed
    assert session.state == SessionState.LISTENING
    assert len(interrupted_events) == 1
    assert output_sink.get_chunk_nowait() is None
