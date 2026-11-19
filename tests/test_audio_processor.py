"""
Tests for PCMProcessor: RMS calculation, mute zeroing, and resampling.
"""

import math
import struct
import pytest
from gemini_voice.audio.processor import PCMProcessor


def generate_sine_pcm(sample_rate: int, freq: float, duration_sec: float, amplitude: float = 0.5) -> bytes:
    sample_count = int(sample_rate * duration_sec)
    buf = bytearray(sample_count * 2)
    angular_step = 2.0 * math.pi * freq / sample_rate
    phase = 0.0
    for i in range(sample_count):
        val = int(math.sin(phase) * amplitude * 32767)
        val = max(-32768, min(32767, val))
        struct.pack_into("<h", buf, i * 2, val)
        phase += angular_step
    return bytes(buf)


def test_compute_rms_silence():
    silent_pcm = b"\x00" * 3200  # 100ms at 16kHz
    rms = PCMProcessor.compute_rms(silent_pcm)
    assert rms == 0.0


def test_compute_rms_sine():
    sine_pcm = generate_sine_pcm(16000, 440.0, 0.1, amplitude=0.5)
    rms = PCMProcessor.compute_rms(sine_pcm)
    # Sine wave RMS is amplitude / sqrt(2) = 0.5 / 1.414 ~= 0.353
    assert 0.33 < rms < 0.37


def test_mute_chunk():
    sine_pcm = generate_sine_pcm(16000, 440.0, 0.1, amplitude=0.5)
    muted = PCMProcessor.mute_chunk(sine_pcm)
    assert len(muted) == len(sine_pcm)
    assert all(b == 0 for b in muted)
    assert PCMProcessor.compute_rms(muted) == 0.0


def test_resample_linear():
    in_pcm = generate_sine_pcm(16000, 440.0, 0.1, amplitude=0.5)
    # 100ms at 16kHz = 1600 samples = 3200 bytes
    assert len(in_pcm) == 3200

    # Resample to 24000Hz (should be 2400 samples = 4800 bytes)
    out_pcm = PCMProcessor.resample_linear(in_pcm, 16000, 24000)
    assert len(out_pcm) == 4800

    # Resample back to 16000Hz
    down_pcm = PCMProcessor.resample_linear(out_pcm, 24000, 16000)
    assert len(down_pcm) == 3200
