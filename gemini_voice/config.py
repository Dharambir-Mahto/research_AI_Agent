"""
Configuration management for the Gemini Voice AI module.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VoiceConfig(BaseModel):
    """
    Configuration options for Gemini Voice AI sessions.
    Reads defaults from environment variables where applicable.
    """
    # Gemini API credentials
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY"),
        description="Google Gemini API key. If omitted, uses GEMINI_API_KEY from environment."
    )
    api_version: str = Field(
        default="v1alpha",
        description="Gemini API version for Live bidirectional streaming."
    )
    
    # Model & Voice persona
    model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        description="Gemini model supporting Live bidirectional audio (bidiGenerateContent)."
    )
    voice_name: str = Field(
        default="Puck",
        description="Voice persona name: Puck, Charon, Kore, Fenrir, Aoede."
    )
    system_instruction: Optional[str] = Field(
        default="You are a helpful, responsive real-time voice AI agent. Keep your answers concise, natural, and conversational.",
        description="System prompt defining agent personality and instructions."
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for responses."
    )

    # Audio formats
    input_sample_rate: int = Field(
        default=16000,
        description="Input PCM audio sample rate in Hz (Gemini expects 16000)."
    )
    input_channels: int = Field(
        default=1,
        description="Input audio channels (1 = mono)."
    )
    output_sample_rate: int = Field(
        default=24000,
        description="Output PCM audio sample rate in Hz (Gemini produces 24000)."
    )
    output_channels: int = Field(
        default=1,
        description="Output audio channels (1 = mono)."
    )
    chunk_size_ms: int = Field(
        default=100,
        description="Duration of each audio frame sent in milliseconds (100ms = 3200 bytes at 16kHz 16-bit mono)."
    )

    # Features
    enable_input_transcription: bool = Field(
        default=True,
        description="Enable real-time transcription of user speech."
    )
    enable_output_transcription: bool = Field(
        default=True,
        description="Enable real-time transcription of agent responses."
    )

    # Voice Activity Detection (VAD)
    vad_enabled: bool = Field(
        default=True,
        description="Enable client-side voice activity detection."
    )
    vad_threshold_rms: float = Field(
        default=0.015,
        description="RMS amplitude threshold above which audio is considered speech."
    )
    vad_silence_duration_ms: int = Field(
        default=800,
        description="Duration of silence (in ms) before declaring end of user speech."
    )
    vad_min_speech_duration_ms: int = Field(
        default=150,
        description="Minimum duration of speech required before triggering speech start."
    )

    # Resilience
    max_reconnect_attempts: int = Field(
        default=5,
        description="Maximum attempts to reconnect upon unexpected disconnection."
    )
    reconnect_delay_seconds: float = Field(
        default=2.0,
        description="Base delay between reconnection attempts."
    )

    # Optional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary application metadata passed along with the session."
    )

    def validate_api_key(self) -> None:
        """Ensure an API key is present before attempting connection."""
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable "
                "or pass `api_key` to VoiceConfig."
            )
