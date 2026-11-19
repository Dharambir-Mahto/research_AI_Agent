"""
Audio output sinks: Abstract base, Queue-based, File-based, Multi-sink, and Local Speaker.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import wave
from typing import Optional, List

logger = logging.getLogger(__name__)


class AudioOutputSink(abc.ABC):
    """Abstract interface for receiving synthesized PCM audio chunks from Gemini."""

    @abc.abstractmethod
    async def open(self) -> None:
        """Initialize the audio sink."""
        pass

    @abc.abstractmethod
    async def write_chunk(self, data: bytes) -> None:
        """Receive and process/play an audio chunk."""
        pass

    @abc.abstractmethod
    async def flush(self) -> None:
        """
        Immediately discard any buffered audio.
        Essential for low-latency interruptions (barge-in).
        """
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Release underlying resources."""
        pass


class AsyncQueueAudioSink(AudioOutputSink):
    """
    Puts synthesized audio chunks into an asyncio Queue.
    Ideal for WebSocket servers to stream agent audio to web/mobile clients.
    """

    def __init__(self, maxsize: int = 200) -> None:
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=maxsize)
        self._is_open = False

    async def open(self) -> None:
        self._is_open = True

    async def write_chunk(self, data: bytes) -> None:
        if self._is_open:
            await self._queue.put(data)

    async def flush(self) -> None:
        """Clear all pending audio chunks in queue immediately."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break

    async def get_chunk(self) -> Optional[bytes]:
        """Fetch next output chunk for network transmission."""
        return await self._queue.get()

    def get_chunk_nowait(self) -> Optional[bytes]:
        """Fetch next chunk without blocking."""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def close(self) -> None:
        self._is_open = False
        await self.flush()
        await self._queue.put(None)


class FileAudioSink(AudioOutputSink):
    """
    Records received Gemini Live response audio into a WAV file.
    """

    def __init__(self, filepath: str, sample_rate: int = 24000, channels: int = 1) -> None:
        self.filepath = filepath
        self.sample_rate = sample_rate
        self.channels = channels
        self._wav_file: Optional[wave.Wave_write] = None
        self._is_open = False

    async def open(self) -> None:
        self._wav_file = wave.open(self.filepath, "wb")
        self._wav_file.setnchannels(self.channels)
        self._wav_file.setsampwidth(2)  # 16-bit
        self._wav_file.setframerate(self.sample_rate)
        self._is_open = True

    async def write_chunk(self, data: bytes) -> None:
        if self._is_open and self._wav_file:
            self._wav_file.writeframes(data)

    async def flush(self) -> None:
        # File sinks keep recorded chunks, but can flush OS buffers if needed
        pass

    async def close(self) -> None:
        self._is_open = False
        if self._wav_file:
            self._wav_file.close()
            self._wav_file = None


class LocalSpeakerSink(AudioOutputSink):
    """
    Plays audio chunks directly through the local sound card / speakers using sounddevice.
    Gracefully handles headless environments.
    """

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self._stream = None
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._is_open = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def open(self) -> None:
        self._loop = asyncio.get_running_loop()
        try:
            import sounddevice as sd  # type: ignore

            def callback(outdata, frames, time_info, status):
                try:
                    data = self._queue.get_nowait()
                    # Pad or truncate if chunk size differs from requested frames
                    needed = frames * 2
                    if len(data) >= needed:
                        outdata[:] = data[:needed]
                    else:
                        outdata[:len(data)] = data
                        outdata[len(data):] = b"\x00" * (needed - len(data))
                except asyncio.QueueEmpty:
                    outdata[:] = b"\x00" * (frames * 2)

            self._stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback,
            )
            self._stream.start()
            self._is_open = True
        except (ImportError, OSError) as e:
            raise RuntimeError(
                f"LocalSpeakerSink cannot initialize: {e}. "
                "Ensure `sounddevice` and PortAudio are installed, "
                "or use `AsyncQueueAudioSink` / WebSocket streaming."
            ) from e

    async def write_chunk(self, data: bytes) -> None:
        if self._is_open:
            await self._queue.put(data)

    async def flush(self) -> None:
        """Immediately drop all buffered frames in playback queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def close(self) -> None:
        self._is_open = False
        await self.flush()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class MultiAudioSink(AudioOutputSink):
    """
    Broadcasts audio chunks to multiple sinks simultaneously (e.g., speaker + recording file).
    """

    def __init__(self, sinks: List[AudioOutputSink]) -> None:
        self.sinks = sinks

    async def open(self) -> None:
        await asyncio.gather(*(s.open() for s in self.sinks))

    async def write_chunk(self, data: bytes) -> None:
        await asyncio.gather(*(s.write_chunk(data) for s in self.sinks))

    async def flush(self) -> None:
        await asyncio.gather(*(s.flush() for s in self.sinks))

    async def close(self) -> None:
        await asyncio.gather(*(s.close() for s in self.sinks))
