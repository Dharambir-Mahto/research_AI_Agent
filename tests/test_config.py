"""
Tests for VoiceConfig configuration management.
"""

import os
import pytest
from pydantic import ValidationError
from gemini_voice.config import VoiceConfig


def test_voice_config_defaults():
    cfg = VoiceConfig(api_key="test_key")
    assert cfg.api_key == "test_key"
    assert cfg.model == "gemini-2.5-flash-native-audio-latest"
    assert cfg.voice_name == "Puck"
    assert cfg.input_sample_rate == 16000
    assert cfg.output_sample_rate == 24000
    assert cfg.temperature == 0.7
    assert cfg.vad_enabled is True
    assert cfg.chunk_size_ms == 100


def test_voice_config_custom_overrides():
    cfg = VoiceConfig(
        api_key="custom_key",
        model="gemini-3.8-live",
        voice_name="Kore",
        temperature=1.2,
        vad_threshold_rms=0.03,
    )
    assert cfg.api_key == "custom_key"
    assert cfg.model == "gemini-3.8-live"
    assert cfg.voice_name == "Kore"
    assert cfg.temperature == 1.2
    assert cfg.vad_threshold_rms == 0.03


def test_voice_config_missing_api_key_validation():
    # If GEMINI_API_KEY is not in env or passed as None
    cfg = VoiceConfig(api_key=None)
    with pytest.raises(ValueError, match="Gemini API key is required"):
        cfg.validate_api_key()


def test_voice_config_temperature_bounds():
    with pytest.raises(ValidationError):
        VoiceConfig(temperature=2.5)  # Max allowed is 2.0

    with pytest.raises(ValidationError):
        VoiceConfig(temperature=-0.1)  # Min allowed is 0.0
