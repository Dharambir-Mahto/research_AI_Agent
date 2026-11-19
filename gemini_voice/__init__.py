"""
Gemini Voice AI Module
A modular, reusable, plug-and-play Voice AI module powered by the Gemini Live API.
"""

from .config import VoiceConfig
from .session import VoiceSession
from .events import (
    SessionState,
    VoiceEvent,
    StateChangeEvent,
    AudioChunkEvent,
    TranscriptEvent,
    SpeechActivityEvent,
    InterruptedEvent,
    ToolCallEvent,
    ToolResultEvent,
    ErrorEvent,
)
from .tools import VoiceTool, ToolRegistry
from .transcripts import TranscriptHandler, TranscriptTurn
from .streaming import StreamingManager
from .client import GeminiLiveClient
from .audio.processor import PCMProcessor, VoiceActivityDetector
from .audio.sources import (
    AudioInputSource,
    AsyncQueueAudioSource,
    FileAudioSource,
    SimulatedAudioSource,
    LocalMicrophoneSource,
)
from .audio.sinks import (
    AudioOutputSink,
    AsyncQueueAudioSink,
    FileAudioSink,
    LocalSpeakerSink,
    MultiAudioSink,
)
from .adapters import (
    BaseAgentAdapter,
    SimpleAgentAdapter,
    LangGraphAdapter,
    WebSocketVoiceServer,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "VoiceConfig",
    "VoiceSession",
    "GeminiLiveClient",
    "StreamingManager",
    "SessionState",
    # Events
    "VoiceEvent",
    "StateChangeEvent",
    "AudioChunkEvent",
    "TranscriptEvent",
    "SpeechActivityEvent",
    "InterruptedEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "ErrorEvent",
    # Audio Processing & VAD
    "PCMProcessor",
    "VoiceActivityDetector",
    # Audio Sources & Sinks
    "AudioInputSource",
    "AsyncQueueAudioSource",
    "FileAudioSource",
    "SimulatedAudioSource",
    "LocalMicrophoneSource",
    "AudioOutputSink",
    "AsyncQueueAudioSink",
    "FileAudioSink",
    "LocalSpeakerSink",
    "MultiAudioSink",
    # Tools & Transcripts
    "VoiceTool",
    "ToolRegistry",
    "TranscriptHandler",
    "TranscriptTurn",
    # Adapters
    "BaseAgentAdapter",
    "SimpleAgentAdapter",
    "LangGraphAdapter",
    "WebSocketVoiceServer",
]
