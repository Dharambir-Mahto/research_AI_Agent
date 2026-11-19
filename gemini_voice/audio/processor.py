"""
Audio processing utilities: PCM framing, RMS calculation, resampling, and VAD.
Pure Python implementation with optional NumPy acceleration.
"""

from __future__ import annotations

import math
import struct
import time
from typing import Optional, Tuple, Callable

# Check if numpy is available
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore
    HAS_NUMPY = False


class PCMProcessor:
    """Utilities for raw 16-bit linear PCM audio manipulation."""

    @staticmethod
    def compute_rms(pcm_data: bytes) -> float:
        """
        Calculates Root Mean Square (RMS) amplitude normalized between 0.0 and 1.0.
        Expects 16-bit signed integer PCM bytes.
        """
        if not pcm_data:
            return 0.0

        sample_count = len(pcm_data) // 2
        if sample_count == 0:
            return 0.0

        if HAS_NUMPY:
            try:
                samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
                mean_square = np.mean(samples ** 2)
                rms = math.sqrt(float(mean_square)) / 32768.0
                return min(1.0, rms)
            except Exception:
                pass

        # Pure Python fallback
        sum_squares = 0.0
        # Read as shorts
        for i in range(0, sample_count * 2, 2):
            val = struct.unpack_from("<h", pcm_data, i)[0]
            sum_squares += val * val

        mean_square = sum_squares / sample_count
        rms = math.sqrt(mean_square) / 32768.0
        return min(1.0, rms)

    @staticmethod
    def mute_chunk(pcm_data: bytes) -> bytes:
        """Returns silent bytes of the exact same length to preserve stream pacing."""
        return b"\x00" * len(pcm_data)

    @staticmethod
    def resample_linear(pcm_data: bytes, in_rate: int, out_rate: int) -> bytes:
        """
        Resamples 16-bit mono PCM audio from in_rate to out_rate using linear interpolation.
        """
        if in_rate == out_rate or not pcm_data:
            return pcm_data

        sample_count = len(pcm_data) // 2
        if sample_count == 0:
            return b""

        ratio = float(out_rate) / float(in_rate)
        target_len = int(sample_count * ratio)
        if target_len == 0:
            return b""

        if HAS_NUMPY:
            samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
            orig_indices = np.arange(sample_count)
            target_indices = np.linspace(0, sample_count - 1, target_len)
            resampled = np.interp(target_indices, orig_indices, samples).astype(np.int16)
            return resampled.tobytes()

        # Pure Python fallback
        samples = [struct.unpack_from("<h", pcm_data, i * 2)[0] for i in range(sample_count)]
        output = bytearray(target_len * 2)

        for i in range(target_len):
            orig_idx = (i * (sample_count - 1)) / max(1, (target_len - 1))
            low_idx = int(orig_idx)
            high_idx = min(sample_count - 1, low_idx + 1)
            frac = orig_idx - low_idx

            val = int(samples[low_idx] * (1.0 - frac) + samples[high_idx] * frac)
            val = max(-32768, min(32767, val))
            struct.pack_into("<h", output, i * 2, val)

        return bytes(output)


class VoiceActivityDetector:
    """
    Real-time energy-based Voice Activity Detection (VAD) with adaptive noise tracking.
    Emits speech start and speech end events.
    """

    def __init__(
        self,
        threshold_rms: float = 0.015,
        silence_duration_ms: int = 800,
        min_speech_duration_ms: int = 150,
        on_speech_start: Optional[Callable[[float], None]] = None,
        on_speech_end: Optional[Callable[[float, float], None]] = None,
    ) -> None:
        self.threshold_rms = threshold_rms
        self.silence_duration_ms = silence_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

        self.is_speaking = False
        self._speech_start_time: Optional[float] = None
        self._last_speech_time: Optional[float] = None
        self._consecutive_speech_ms = 0.0

    def process_frame(self, pcm_chunk: bytes, frame_duration_ms: float) -> Tuple[bool, float]:
        """
        Processes a single frame of PCM audio.
        Returns: (is_voice_active, current_rms)
        """
        rms = PCMProcessor.compute_rms(pcm_chunk)
        now = time.time()
        is_above_threshold = rms >= self.threshold_rms

        if is_above_threshold:
            self._consecutive_speech_ms += frame_duration_ms
            self._last_speech_time = now

            if not self.is_speaking and self._consecutive_speech_ms >= self.min_speech_duration_ms:
                self.is_speaking = True
                self._speech_start_time = now - (self._consecutive_speech_ms / 1000.0)
                if self.on_speech_start:
                    self.on_speech_start(rms)
        else:
            self._consecutive_speech_ms = 0.0
            if self.is_speaking:
                silence_ms = (now - (self._last_speech_time or now)) * 1000.0
                if silence_ms >= self.silence_duration_ms:
                    total_duration = (now - (self._speech_start_time or now)) * 1000.0
                    self.is_speaking = False
                    if self.on_speech_end:
                        self.on_speech_end(total_duration, rms)
                    self._speech_start_time = None
                    self._last_speech_time = None

        return self.is_speaking, rms

    def reset(self) -> None:
        """Reset internal VAD states."""
        self.is_speaking = False
        self._speech_start_time = None
        self._last_speech_time = None
        self._consecutive_speech_ms = 0.0
