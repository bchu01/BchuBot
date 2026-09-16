import asyncio
import queue
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from agent.factory import create_agent
from tools.alarms import (
    add_alarm_listener,
    fired_message,
    remove_alarm_listener,
    start_scheduler,
    stop_scheduler,
)
from web.stats import collect_stats


STATIC_DIR = Path(__file__).parent / "static"
HOST = "127.0.0.1"
PORT = 8000


@asynccontextmanager
async def lifespan(_app):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="BchuBot", lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/stats")
def stats():
    return collect_stats()


@app.websocket("/ws")
async def chat_socket(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    confirm_answers = queue.Queue()
    busy = threading.Event()

    def send(payload):
        asyncio.run_coroutine_threadsafe(websocket.send_json(payload), loop)

    def confirm(tool_name, arguments):
        send(
            {
                "type": "confirm",
                "tool": tool_name,
                "arguments": arguments or {},
            }
        )
        try:
            return bool(confirm_answers.get(timeout=300))
        except queue.Empty:
            send(
                {
                    "type": "status",
                    "text": "Confirmation timed out. The action was not allowed.",
                }
            )
            return False

    def on_tool(tool_name, _arguments):
        send({"type": "status", "text": f"Using {tool_name}…"})

    def on_context(_text):
        send({"type": "status", "text": "Using stored notes…"})

    def on_alarm(item):
        send(
            {
                "type": "alarm",
                "text": fired_message(item),
                "kind": item.get("kind"),
                "label": item.get("label"),
                "status": item.get("status"),
            }
        )

    add_alarm_listener(on_alarm)
    started_tokens = {"sent": False}
    last_think = {"at": 0.0}

    def on_token(piece):
        if not started_tokens["sent"]:
            started_tokens["sent"] = True
            send({"type": "progress", "phase": "writing"})
        send({"type": "token", "text": piece})

    def on_thinking(_piece):
        now = time.monotonic()
        if now - last_think["at"] < 0.25:
            return
        last_think["at"] = now
        send({"type": "progress", "phase": "thinking"})

    agent = create_agent(
        confirm=confirm,
        on_tool=on_tool,
        on_token=on_token,
        on_thinking=on_thinking,
        on_context=on_context,
    )

    def run_chat(text):
        started_tokens["sent"] = False
        try:
            reply = agent.chat(text)
            send({"type": "reply", "text": reply or ""})
        except Exception as exc:
            send({"type": "error", "text": str(exc)})
        finally:
            busy.clear()

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "confirm":
                confirm_answers.put(bool(data.get("allow")))
                continue

            if message_type != "message":
                continue

            text = (data.get("text") or "").strip()
            if not text:
                continue
            if busy.is_set():
                await websocket.send_json(
                    {"type": "status", "text": "Wait for the current reply to finish."}
                )
                continue

            busy.set()
            await websocket.send_json({"type": "progress", "phase": "thinking"})
            threading.Thread(target=run_chat, args=(text,), daemon=True).start()
    except WebSocketDisconnect:
        while True:
            try:
                confirm_answers.get_nowait()
            except queue.Empty:
                break
        confirm_answers.put(False)
    finally:
        remove_alarm_listener(on_alarm)


if __name__ == "__main__":
    uvicorn.run("web.server:app", host=HOST, port=PORT, reload=False)
