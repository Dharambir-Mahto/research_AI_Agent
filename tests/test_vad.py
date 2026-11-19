"""
Tests for VoiceActivityDetector (VAD).
"""

import pytest
from gemini_voice.audio.processor import VoiceActivityDetector
from tests.test_audio_processor import generate_sine_pcm


def test_vad_silence():
    vad = VoiceActivityDetector(threshold_rms=0.02)
    silence = b"\x00" * 3200
    is_active, rms = vad.process_frame(silence, frame_duration_ms=100)
    assert not is_active
    assert rms == 0.0


def test_vad_speech_start_and_end():
    events = []

    def on_start(rms):
        events.append(("start", rms))

    def on_end(duration_ms, rms):
        events.append(("end", duration_ms))

    vad = VoiceActivityDetector(
        threshold_rms=0.02,
        min_speech_duration_ms=150,
        silence_duration_ms=300,
        on_speech_start=on_start,
        on_speech_end=on_end,
    )

    sine_frame = generate_sine_pcm(16000, 440.0, 0.1, amplitude=0.4)
    silent_frame = b"\x00" * 3200

    # Frame 1: Speech (100ms) - not yet min_speech_duration (150ms)
    vad.process_frame(sine_frame, 100)
    assert not vad.is_speaking
    assert len(events) == 0

    # Frame 2: Speech (another 100ms -> 200ms total) - triggers speech start!
    vad.process_frame(sine_frame, 100)
    assert vad.is_speaking
    assert len(events) == 1
    assert events[0][0] == "start"

    # Frame 3: Silence (100ms) - silence counter starts
    import time
    time.sleep(0.35)  # Simulate wall-clock silence beyond 300ms
    vad.process_frame(silent_frame, 100)

    assert not vad.is_speaking
    assert len(events) == 2
    assert events[1][0] == "end"
