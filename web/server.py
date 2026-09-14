import asyncio
import queue
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from agent.factory import create_agent


STATIC_DIR = Path(__file__).parent / "static"
HOST = "127.0.0.1"
PORT = 8000

app = FastAPI(title="BchuBot")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


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

    agent = create_agent(confirm=confirm, on_tool=on_tool)

    def run_chat(text):
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
            await websocket.send_json({"type": "status", "text": "Thinking…"})
            threading.Thread(target=run_chat, args=(text,), daemon=True).start()
    except WebSocketDisconnect:
        while True:
            try:
                confirm_answers.get_nowait()
            except queue.Empty:
                break
        confirm_answers.put(False)


if __name__ == "__main__":
    uvicorn.run("web.server:app", host=HOST, port=PORT, reload=False)
