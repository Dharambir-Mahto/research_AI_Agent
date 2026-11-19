"""
Web Demo Server: Serves modern browser interface and bidirectional WebSocket voice connection.
Zero external framework dependencies beyond aiohttp.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from aiohttp import web, WSMsgType
from dotenv import load_dotenv

from gemini_voice import (
    VoiceSession,
    VoiceConfig,
    AsyncQueueAudioSource,
    AsyncQueueAudioSink,
    StateChangeEvent,
    TranscriptEvent,
    ToolCallEvent,
    ToolResultEvent,
    InterruptedEvent,
    ErrorEvent,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("VoiceServer")


# -----------------------------------------------------------------------------
# Demo Agent Tools
# -----------------------------------------------------------------------------
def get_stock_price(ticker: str) -> str:
    """Get real-time stock price and market movement for a given ticker."""
    stocks = {
        "GOOG": "$182.40 (+1.8%)",
        "AAPL": "$228.10 (+0.4%)",
        "MSFT": "$430.50 (-0.2%)",
        "NVDA": "$125.80 (+3.5%)",
        "AMZN": "$195.20 (+1.1%)",
    }
    return stocks.get(ticker.upper().strip(), f"${ticker.upper()} is currently trading at $150.00 (+0.5%)")


def control_smart_home(device: str, action: str) -> str:
    """Control smart home appliances like lights, thermostat, or locks."""
    return f"Success: {device} has been turned {action}."


def get_current_time(timezone: str = "UTC") -> str:
    """Get current time for a timezone."""
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"Current time is {now}."


# -----------------------------------------------------------------------------
# HTTP & WebSocket Handlers
# -----------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


async def index_handler(request: web.Request) -> web.Response:
    """Serve the single-page HTML application."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="Web demo UI not found.", status=404)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """Handle full-duplex voice streaming over WebSocket."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    client_ip = request.remote
    logger.info(f"Client connected to voice stream: {client_ip}")

    # Create isolated voice session
    config = VoiceConfig(
        model=os.getenv("GEMINI_VOICE_MODEL", "gemini-2.5-flash-native-audio-latest"),
        voice_name="Puck",
        system_instruction=(
            "You are a friendly, witty, and intelligent Voice AI assistant. "
            "You are conversing with the user in real-time. "
            "Keep answers concise, conversational, and natural. "
            "Use the provided tools when asked about stocks, smart home, or time."
        ),
    )

    input_source = AsyncQueueAudioSource()
    output_sink = AsyncQueueAudioSink()

    session = VoiceSession(
        config=config,
        input_source=input_source,
        output_sink=output_sink,
        tools=[get_stock_price, control_smart_home, get_current_time],
    )

    # Helper to send JSON messages
    async def send_json(payload: dict):
        if not ws.closed:
            try:
                await ws.send_str(json.dumps(payload))
            except Exception:
                pass

    # Wire session events to WebSocket messages
    @session.on("state_change")
    async def on_state(evt: StateChangeEvent):
        await send_json({
            "type": "state_change",
            "old_state": evt.old_state.value,
            "new_state": evt.new_state.value,
        })

    @session.on("transcript")
    async def on_transcript(evt: TranscriptEvent):
        await send_json({
            "type": "transcript",
            "role": evt.role,
            "text": evt.text,
            "is_final": evt.is_final,
        })

    @session.on("tool_call")
    async def on_tool(evt: ToolCallEvent):
        await send_json({
            "type": "tool_call",
            "name": evt.name,
            "args": evt.args,
            "call_id": evt.call_id,
        })

    @session.on("tool_result")
    async def on_tool_res(evt: ToolResultEvent):
        await send_json({
            "type": "tool_result",
            "name": evt.name,
            "result": evt.result,
            "call_id": evt.call_id,
        })

    @session.on("interrupted")
    async def on_interrupted(evt: InterruptedEvent):
        await send_json({"type": "interrupted", "reason": evt.reason})

    @session.on("error")
    async def on_error(evt: ErrorEvent):
        await send_json({"type": "error", "error": evt.error})

    @session.on("audio_level_in")
    async def on_audio_level(data: dict):
        await send_json({"type": "audio_level", "rms": round(data.get("rms", 0.0), 4)})

    # Start voice session
    try:
        await session.start()
    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        await send_json({"type": "error", "error": f"Failed to connect to Gemini Live: {e}"})
        await ws.close()
        return ws

    # Coroutine 1: Read audio chunks from output_sink and send binary frames to browser
    async def audio_stream_sender():
        try:
            while not ws.closed:
                chunk = await output_sink.get_chunk()
                if chunk is None:
                    break
                await ws.send_bytes(chunk)
        except (asyncio.CancelledError, Exception):
            pass

    sender_task = asyncio.create_task(audio_stream_sender())

    # Coroutine 2: Ingest browser messages
    try:
        async for msg in ws:
            if msg.type == WSMsgType.BINARY:
                # Browser mic audio frame (16kHz 16-bit PCM)
                await input_source.push(msg.data)
            elif msg.type == WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                    m_type = payload.get("type")

                    if m_type == "text":
                        await session.send_text(payload.get("content", ""))
                    elif m_type == "interrupt":
                        await session.interrupt()
                    elif m_type == "mute":
                        session.mute()
                    elif m_type == "unmute":
                        session.unmute()
                    elif m_type == "pause":
                        session.pause()
                    elif m_type == "resume":
                        session.resume()
                except Exception as e:
                    logger.warning(f"Error handling message: {e}")
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                break
    finally:
        sender_task.cancel()
        logger.info(f"Stopping voice session for {client_ip}...")
        await session.stop()

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws/voice", websocket_handler)
    if os.path.exists(STATIC_DIR):
        app.router.add_static("/static", STATIC_DIR)
    return app


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"Starting Gemini Voice Web Demo on http://localhost:{port}")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=port)
