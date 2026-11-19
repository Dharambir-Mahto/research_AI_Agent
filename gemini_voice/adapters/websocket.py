"""
WebSocket Server Adapter allowing web, mobile, and desktop frontends
to stream real-time audio and events without exposing API keys.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any, Union
try:
    from websockets.asyncio.server import ServerConnection as WebSocketConn, serve
except ImportError:
    from websockets.server import WebSocketServerProtocol as WebSocketConn, serve  # type: ignore

from ..config import VoiceConfig
from ..session import VoiceSession
from ..audio.sources import AsyncQueueAudioSource
from ..audio.sinks import AsyncQueueAudioSink
from ..events import (
    StateChangeEvent,
    TranscriptEvent,
    ToolCallEvent,
    ToolResultEvent,
    InterruptedEvent,
    ErrorEvent,
)

logger = logging.getLogger(__name__)


class WebSocketVoiceServer:
    """
    WebSocket server gateway bridging remote clients with Gemini Live VoiceSessions.
    Transfers binary PCM frames and JSON control messages.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        session_factory: Optional[Callable[[], VoiceSession]] = None,
        config: Optional[VoiceConfig] = None,
        tools: Optional[list] = None,
        system_instruction: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.config = config or VoiceConfig()
        self.tools = tools or []
        self.system_instruction = system_instruction
        self.session_factory = session_factory
        self._server = None

    def _create_session_for_client(self) -> tuple[VoiceSession, AsyncQueueAudioSource, AsyncQueueAudioSink]:
        """Creates an isolated VoiceSession with queue-based I/O for each client connection."""
        if self.session_factory:
            session = self.session_factory()
            # If session already has input/output sources, return
            return session, session._input_source, session._output_sink  # type: ignore

        input_source = AsyncQueueAudioSource()
        output_sink = AsyncQueueAudioSink()

        session = VoiceSession(
            config=self.config,
            input_source=input_source,
            output_sink=output_sink,
            tools=self.tools,
            system_instruction=self.system_instruction,
        )
        return session, input_source, output_sink

    async def _handle_connection(self, websocket: WebSocketConn, path: str = "/") -> None:
        """Handle individual client WebSocket connection."""
        client_addr = websocket.remote_address
        logger.info(f"New client connected from {client_addr}")

        session, input_source, output_sink = self._create_session_for_client()

        # Wire session events to JSON WebSocket messages
        @session.on("state_change")
        async def on_state(evt: StateChangeEvent):
            await self._send_json(websocket, {
                "type": "state_change",
                "old_state": evt.old_state.value,
                "new_state": evt.new_state.value,
            })

        @session.on("transcript")
        async def on_transcript(evt: TranscriptEvent):
            await self._send_json(websocket, {
                "type": "transcript",
                "role": evt.role,
                "text": evt.text,
                "is_final": evt.is_final,
            })

        @session.on("tool_call")
        async def on_tool_call(evt: ToolCallEvent):
            await self._send_json(websocket, {
                "type": "tool_call",
                "name": evt.name,
                "args": evt.args,
                "call_id": evt.call_id,
            })

        @session.on("tool_result")
        async def on_tool_result(evt: ToolResultEvent):
            await self._send_json(websocket, {
                "type": "tool_result",
                "name": evt.name,
                "result": evt.result,
                "call_id": evt.call_id,
            })

        @session.on("interrupted")
        async def on_interrupted(evt: InterruptedEvent):
            await self._send_json(websocket, {
                "type": "interrupted",
                "reason": evt.reason,
            })

        @session.on("error")
        async def on_error(evt: ErrorEvent):
            await self._send_json(websocket, {
                "type": "error",
                "error": evt.error,
                "recoverable": evt.recoverable,
            })

        @session.on("audio_level_in")
        async def on_audio_level(data: dict):
            await self._send_json(websocket, {
                "type": "audio_level",
                "rms": round(data.get("rms", 0.0), 4),
            })

        # Start session
        await session.start()

        # Task 1: Stream synthesized audio from output_sink to client via binary WebSocket frames
        async def audio_sender():
            try:
                while True:
                    chunk = await output_sink.get_chunk()
                    if chunk is None:
                        break
                    await websocket.send(chunk)
            except (websockets.ConnectionClosed, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.error(f"Error streaming output audio to client: {e}")

        # Task 2: Ingest binary PCM audio and JSON commands from client
        async def message_receiver():
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        # Binary frame: microphone PCM chunk
                        await input_source.push(message)
                    elif isinstance(message, str):
                        # JSON control message
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")

                            if msg_type == "text":
                                await session.send_text(data.get("content", ""))
                            elif msg_type == "interrupt":
                                await session.interrupt()
                            elif msg_type == "mute":
                                session.mute()
                            elif msg_type == "unmute":
                                session.unmute()
                            elif msg_type == "pause":
                                session.pause()
                            elif msg_type == "resume":
                                session.resume()
                            else:
                                logger.warning(f"Unknown message type from client: {msg_type}")
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON received: {message}")
            except (websockets.ConnectionClosed, asyncio.CancelledError):
                pass
            except Exception as e:
                logger.error(f"Error receiving from client: {e}")

        sender_task = asyncio.create_task(audio_sender())
        receiver_task = asyncio.create_task(message_receiver())

        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        logger.info(f"Client {client_addr} disconnected, stopping session...")
        await session.stop()

    async def _send_json(self, websocket: WebSocketConn, payload: Dict[str, Any]) -> None:
        """Helper to send JSON safely across websocket."""
        try:
            await websocket.send(json.dumps(payload))
        except (websockets.ConnectionClosed, Exception):
            pass

    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting Voice AI WebSocket server on ws://{self.host}:{self.port}...")
        self._server = await serve(self._handle_connection, self.host, self.port)

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        await self.start()
        await self._server.wait_closed()

    async def close(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
