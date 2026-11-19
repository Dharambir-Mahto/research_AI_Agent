"""
Low-level Gemini Live API client encapsulating bidirectional streaming,
speech synthesis, recognition, and tool calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from google import genai
from google.genai import types

from .config import VoiceConfig
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class GeminiLiveClient:
    """
    Client managing the low-latency bidirectional WebSocket connection to the Gemini Live API.
    """

    def __init__(
        self,
        config: VoiceConfig,
        tool_registry: Optional[ToolRegistry] = None,
        on_audio: Optional[Callable[[bytes, str], Any]] = None,
        on_text: Optional[Callable[[str, str, bool], Any]] = None,  # (role, text, is_final)
        on_tool_call: Optional[Callable[[str, str, Dict[str, Any]], Any]] = None,  # (id, name, args)
        on_interrupted: Optional[Callable[[], Any]] = None,
        on_turn_complete: Optional[Callable[[], Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None,
    ) -> None:
        self.config = config
        self.tool_registry = tool_registry or ToolRegistry()
        self.on_audio = on_audio
        self.on_text = on_text
        self.on_tool_call = on_tool_call
        self.on_interrupted = on_interrupted
        self.on_turn_complete = on_turn_complete
        self.on_error = on_error

        self._genai_client: Optional[genai.Client] = None
        self._session = None
        self._session_context = None
        self._is_connected = False
        self._receive_task: Optional[asyncio.Task] = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _build_live_config(self) -> types.LiveConnectConfig:
        """Construct LiveConnectConfig based on user configuration and tools."""
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=self.config.voice_name
                )
            )
        )

        system_instruction = None
        if self.config.system_instruction:
            system_instruction = types.Content(
                parts=[types.Part.from_text(text=self.config.system_instruction)]
            )

        tools = self.tool_registry.to_gemini_tools()

        input_transcription = None
        if self.config.enable_input_transcription:
            input_transcription = types.AudioTranscriptionConfig()

        output_transcription = None
        if self.config.enable_output_transcription:
            output_transcription = types.AudioTranscriptionConfig()

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=speech_config,
            system_instruction=system_instruction,
            tools=tools,
            temperature=self.config.temperature,
            input_audio_transcription=input_transcription,
            output_audio_transcription=output_transcription,
        )

    async def connect(self) -> None:
        """Establish the bidirectional live streaming session."""
        self.config.validate_api_key()

        self._genai_client = genai.Client(
            api_key=self.config.api_key,
            http_options={"api_version": self.config.api_version},
        )

        live_config = self._build_live_config()
        logger.info(f"Connecting to Gemini Live API with model '{self.config.model}'...")

        self._session_context = self._genai_client.aio.live.connect(
            model=self.config.model,
            config=live_config,
        )
        self._session = await self._session_context.__aenter__()
        self._is_connected = True
        logger.info("Successfully connected to Gemini Live session.")

        # Start background receiver task
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Send a chunk of raw PCM audio to the active session."""
        if not self._is_connected or not self._session:
            raise RuntimeError("Cannot send audio: Gemini Live session is not connected.")

        mime = f"audio/pcm;rate={self.config.input_sample_rate}"
        blob = types.Blob(data=pcm_bytes, mime_type=mime)
        await self._session.send_realtime_input(audio=blob)

    async def send_text(self, text: str, turn_complete: bool = True) -> None:
        """Send explicit text message to the live session."""
        if not self._is_connected or not self._session:
            raise RuntimeError("Cannot send text: Gemini Live session is not connected.")

        await self._session.send_client_content(
            turns=types.Content(
                role="user",
                parts=[types.Part.from_text(text=text)],
            ),
            turn_complete=turn_complete,
        )

    async def send_tool_response(self, function_responses: types.FunctionResponse) -> None:
        """Send function/tool output back to Gemini Live."""
        if not self._is_connected or not self._session:
            raise RuntimeError("Cannot send tool response: session not connected.")

        await self._session.send_tool_response(function_responses=function_responses)

    async def _receive_loop(self) -> None:
        """Background coroutine processing incoming messages from Gemini Live."""
        try:
            async for response in self._session.receive():
                await self._handle_server_message(response)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Gemini Live receive loop: {e}", exc_info=True)
            if self.on_error:
                res = self.on_error(e)
                if asyncio.iscoroutine(res):
                    await res
        finally:
            self._is_connected = False

    async def _handle_server_message(self, response: types.LiveServerMessage) -> None:
        """Decode and route incoming server message components."""
        # 1. Check for tool calls
        if response.tool_call:
            for call in response.tool_call.function_calls:
                call_id = call.id
                name = call.name
                args = call.args or {}
                logger.info(f"Received tool call from Gemini: {name} (id={call_id})")
                if self.on_tool_call:
                    res = self.on_tool_call(call_id, name, args)
                    if asyncio.iscoroutine(res):
                        await res

        # 2. Check server content (model turn, audio, transcription, turn completion, interruption)
        server_content = response.server_content
        if server_content is not None:
            # Handle user interruption (barge-in)
            if server_content.interrupted:
                logger.info("Gemini Live reported response interrupted by user.")
                if self.on_interrupted:
                    res = self.on_interrupted()
                    if asyncio.iscoroutine(res):
                        await res

            # Handle model turn output
            if server_content.model_turn:
                for part in server_content.model_turn.parts:
                    # Model audio data
                    if part.inline_data and part.inline_data.data:
                        audio_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type or f"audio/pcm;rate={self.config.output_sample_rate}"
                        if self.on_audio:
                            res = self.on_audio(audio_data, mime_type)
                            if asyncio.iscoroutine(res):
                                await res

                    # Model text or transcript
                    if part.text:
                        if self.on_text:
                            res = self.on_text("assistant", part.text, False)
                            if asyncio.iscoroutine(res):
                                await res

            # Handle turn completion
            if server_content.turn_complete:
                if self.on_turn_complete:
                    res = self.on_turn_complete()
                    if asyncio.iscoroutine(res):
                        await res

    async def close(self) -> None:
        """Gracefully disconnect the live session."""
        self._is_connected = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._session_context:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception as e:
                logger.debug(f"Exception during session close: {e}")
            finally:
                self._session = None
                self._session_context = None
                self._genai_client = None
