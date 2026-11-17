import asyncio
import json
import mimetypes
import os
from pathlib import Path
from datetime import datetime

from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Import from existing agent.py directly without any modifications to agent.py
from agent import (
    initialize_agent,
    ask_gemini,
    _safe_cleanup,
    RESEARCH_DIR,
    REPORT_DIR,
    MODEL,
)

# Global singleton agent instance with asyncio lock
_agent_instance = None
_agent_lock = asyncio.Lock()

CONVERSATIONS_FILE = RESEARCH_DIR / "conversations.json"


def _load_conversations():
    """Load persistent conversation history from JSON."""
    if not CONVERSATIONS_FILE.exists():
        return {}
    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_conversations(data):
    """Persist conversation history to JSON."""
    try:
        CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("[HISTORY] Failed to save conversations:", e)


async def get_or_create_agent():
    """Lazily initialize the agent once and keep it ready for fast requests."""
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance

    async with _agent_lock:
        if _agent_instance is None:
            _agent_instance = await initialize_agent()
        return _agent_instance


def index(request):
    """Main dashboard page."""
    context = {
        "model_name": MODEL,
        "research_dir": str(RESEARCH_DIR),
    }
    return render(request, "research_ui/index.html", context)


def _get_reports_list():
    """Helper to list all generated research reports."""
    reports = []
    if not REPORT_DIR.exists():
        return reports

    for file_path in REPORT_DIR.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith("."):
            try:
                rel = file_path.relative_to(REPORT_DIR)
                stat = file_path.stat()
                ext = file_path.suffix.lstrip(".").lower()
                topic = rel.parent.name if rel.parent.name else "general"

                # Human-friendly size
                size_bytes = stat.st_size
                if size_bytes < 1024:
                    size_human = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_human = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_human = f"{size_bytes / (1024 * 1024):.1f} MB"

                reports.append(
                    {
                        "filename": file_path.name,
                        "relpath": str(rel),
                        "topic": topic,
                        "format": ext,
                        "size_human": size_human,
                        "size_bytes": size_bytes,
                        "modified_iso": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "modified_formatted": datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%b %d, %Y · %H:%M"),
                    }
                )
            except Exception:
                continue

    # Sort newest first
    reports.sort(key=lambda r: r["modified_iso"], reverse=True)
    return reports


def reports_api(request):
    """Returns JSON list of all generated reports."""
    reports = _get_reports_list()
    return JsonResponse({"status": "success", "reports": reports, "count": len(reports)})


def download_report(request, relpath):
    """Safely stream a generated report file for download."""
    safe_base = REPORT_DIR.resolve()
    target_path = (REPORT_DIR / relpath).resolve()

    # Security check: prevent directory traversal outside REPORT_DIR
    if not str(target_path).startswith(str(safe_base)) or not target_path.is_file():
        raise Http404("Report not found or invalid path.")

    content_type, _ = mimetypes.guess_type(str(target_path))
    if not content_type:
        content_type = "application/octet-stream"

    response = FileResponse(open(target_path, "rb"), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{target_path.name}"'
    return response


def preview_report(request, relpath):
    """Return text content of a report for previewing (e.g. Markdown)."""
    safe_base = REPORT_DIR.resolve()
    target_path = (REPORT_DIR / relpath).resolve()

    if not str(target_path).startswith(str(safe_base)) or not target_path.is_file():
        return JsonResponse({"status": "error", "message": "File not found"}, status=404)

    ext = target_path.suffix.lower()
    if ext in [".md", ".txt", ".json", ".csv"]:
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return JsonResponse({
                "status": "success",
                "filename": target_path.name,
                "is_text": True,
                "content": content,
                "format": ext.lstrip("."),
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
        return JsonResponse({
            "status": "success",
            "filename": target_path.name,
            "is_text": False,
            "format": ext.lstrip("."),
            "download_url": f"/api/reports/download/{relpath}",
        })


def status_api(request):
    """Returns current system and agent runtime status."""
    reports_count = len(_get_reports_list())
    is_ready = _agent_instance is not None
    return JsonResponse({
        "status": "online",
        "agent_initialized": is_ready,
        "model": MODEL,
        "reports_count": reports_count,
        "capabilities": [
            "Autonomous Web Research & Scraping",
            "Live Browser Automation (Playwright Headless)",
            "MCP Dynamic Filesystem & Graph Memory",
            "Executive Reports Exporter (PDF, DOCX, Markdown)",
            "Automated Citation & Reference Tracking",
        ],
    })


def conversations_list_api(request):
    """List all saved conversations sorted by updated_at desc."""
    data = _load_conversations()
    convs = []
    for cid, c in data.items():
        msgs = c.get("messages", [])
        last_msg = msgs[-1]["content"] if msgs else ""
        convs.append({
            "id": cid,
            "title": c.get("title", "Untitled Session"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at", c.get("created_at")),
            "message_count": len(msgs),
            "preview": (last_msg[:65] + "...") if len(last_msg) > 65 else last_msg,
        })
    convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return JsonResponse({"status": "success", "conversations": convs, "count": len(convs)})


def conversation_detail_api(request, conv_id):
    """Get full messages for a specific conversation."""
    data = _load_conversations()
    if conv_id not in data:
        return JsonResponse({"status": "error", "message": "Conversation not found"}, status=404)
    return JsonResponse({"status": "success", "conversation": data[conv_id]})


@csrf_exempt
def conversation_delete_api(request, conv_id):
    """Delete a conversation from history."""
    if request.method not in ["DELETE", "POST"]:
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    data = _load_conversations()
    if conv_id in data:
        del data[conv_id]
        _save_conversations(data)
        return JsonResponse({"status": "success", "message": "Conversation deleted"})
    return JsonResponse({"status": "error", "message": "Conversation not found"}, status=404)


@csrf_exempt
def conversations_clear_api(request):
    """Clear all conversation history."""
    if request.method not in ["DELETE", "POST"]:
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
    _save_conversations({})
    return JsonResponse({"status": "success", "message": "All conversations cleared"})


@csrf_exempt
async def chat_api(request):
    """Handles chat research queries, save commands, and persistent session history."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    prompt = (data.get("prompt") or "").strip()
    last_report = data.get("last_report") or None
    conv_id = (data.get("conversation_id") or "").strip()

    if not prompt:
        return JsonResponse({"status": "error", "message": "Prompt cannot be empty"}, status=400)

    if not conv_id:
        conv_id = f"conv_{int(datetime.now().timestamp() * 1000)}"

    try:
        agent = await get_or_create_agent()
        response_text = await ask_gemini(prompt, agent, last_report)

        # Check if this was a save confirmation
        stripped = response_text.lstrip()
        is_saved = stripped.startswith("SAVED:")
        is_save_failed = stripped.startswith("SAVE_FAILED:")

        saved_path = None
        if is_saved:
            parts = stripped.split("SAVED:", 1)
            if len(parts) > 1:
                saved_path = parts[1].strip()

        # Save conversation history to JSON
        now_dt = datetime.now()
        now_iso = now_dt.isoformat()
        now_time = now_dt.strftime("%I:%M %p")

        convs = _load_conversations()
        if conv_id not in convs:
            clean_title = prompt.replace("\n", " ").strip()
            if len(clean_title) > 38:
                clean_title = clean_title[:38] + "..."
            convs[conv_id] = {
                "id": conv_id,
                "title": clean_title,
                "created_at": now_iso,
                "updated_at": now_iso,
                "last_report": response_text if not is_saved else (last_report or None),
                "messages": [],
            }

        conv_record = convs[conv_id]
        conv_record["updated_at"] = now_iso
        if not is_saved and not is_save_failed:
            conv_record["last_report"] = response_text

        conv_record["messages"].append({
            "id": f"msg_u_{int(now_dt.timestamp()*1000)}",
            "role": "user",
            "content": prompt,
            "timestamp": now_time,
        })

        conv_record["messages"].append({
            "id": f"msg_a_{int(now_dt.timestamp()*1000)}",
            "role": "assistant",
            "content": response_text,
            "is_saved": is_saved,
            "saved_path": saved_path,
            "timestamp": now_time,
        })

        _save_conversations(convs)

        return JsonResponse({
            "status": "success",
            "response": response_text,
            "is_saved": is_saved,
            "is_save_failed": is_save_failed,
            "saved_path": saved_path,
            "conversation_id": conv_id,
            "conversation_title": conv_record.get("title", ""),
        })
    except Exception as error:
        return JsonResponse({
            "status": "error",
            "message": str(error),
        }, status=500)


@csrf_exempt
async def reset_api(request):
    """Safely cleanup and reset the agent instance for a clean state."""
    global _agent_instance
    async with _agent_lock:
        if _agent_instance is not None:
            await _safe_cleanup()
            _agent_instance = None
    return JsonResponse({"status": "success", "message": "Agent session reset successfully."})
