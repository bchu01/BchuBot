# BchuBot User Manual

BchuBot is a personal, privacy-focused assistant that runs on your computer. A local language model (Ollama + Qwen3 8B by default) decides whether to answer directly or call a Python tool. The GitHub repository contains **code only**. The model, Python packages, Google login, memories, alarms, and API tokens are stored on the machine that runs it.

This manual covers:

1. [Setup from scratch](#1-setup-from-scratch)
2. [Adding tools (modules)](#2-adding-tools-modules)
3. [System architecture](#3-system-architecture)

A shorter new-device checklist also lives in `SETUP.md`.

---

## 1. Setup from scratch

These steps replicate a working BchuBot on a new Mac (or another Unix-like machine). Windows notes are called out where they differ.

### 1.1 What you need

Install these before cloning:

| Requirement | Why |
|---|---|
| [Git](https://git-scm.com) | Clone the repository |
| [Python 3.10+](https://www.python.org/downloads/) | Application language (`python3 --version` to check) |
| [Ollama](https://ollama.com) | Local model runtime |

You also need enough RAM for the model. `qwen3:8b` typically wants **8GB+ free RAM**.

BchuBot is a **local** app. The chat page binds to `127.0.0.1` (this computer only). It is not a public server.

### 1.2 Install and start Ollama

1. Install Ollama from [https://ollama.com](https://ollama.com).
2. Confirm the CLI is available:

```bash
ollama --version
```

3. Pull the default model (one-time download, several GB):

```bash
ollama pull qwen3:8b
```

4. Keep the Ollama service running while you use BchuBot.

On macOS, opening the Ollama app is usually enough. If chat later says it failed to connect to Ollama, start it in a terminal:

```bash
ollama serve
```

Leave that terminal open. The API listens on `127.0.0.1:11434` by default.

Check that the model is present:

```bash
ollama list
```

You should see `qwen3:8b`. The model name is configurable in `agent/prompt.py` (`MODEL`). If you change it, pull that model with Ollama too.

### 1.3 Clone the repository

```bash
git clone https://github.com/bchu01/BchuBot.git
cd BchuBot
```

Do not copy a virtual environment from another computer. Recreate it on this machine (next step).

### 1.4 Create a virtual environment and install packages

macOS / Linux:

```bash
python3 -m venv BchuBot-env
source BchuBot-env/bin/activate
pip install -r requirements.txt
```

Windows (Command Prompt):

```bat
python -m venv BchuBot-env
BchuBot-env\Scripts\activate
pip install -r requirements.txt
```

`python3 -m venv BchuBot-env` means “run the `venv` module with this Python,” which creates an isolated package folder named `BchuBot-env`. After `source BchuBot-env/bin/activate`, the `python` command is that environment’s interpreter, not the system one.

Confirm you are in the venv: the shell prompt usually starts with `(BchuBot-env)`, and this should print a path inside `BchuBot-env`:

```bash
which python
```

On Windows: `where python`.

### 1.5 Run the tests

From the repo root, with the venv active:

```bash
python -m unittest discover -s tests -v
```

`python -m unittest` runs Python’s unit-test module. `-s tests` is the test folder. `-v` is verbose. All tests should pass. Google, weather, and Canvas network calls are mocked in tests; you do not need those accounts for this step.

### 1.6 Private files (`~/.bchubot`)

Create the config directory:

```bash
mkdir -p ~/.bchubot
```

On Windows, that directory is `%USERPROFILE%\.bchubot`.

Nothing in this folder is in Git. Never commit these files.

| File | Required? | Purpose |
|---|---|---|
| `~/.bchubot/google_credentials.json` | Only for Google Calendar / Tasks | Desktop OAuth client JSON from Google Cloud |
| `~/.bchubot/google_token.json` | Created on first Google login | Saved OAuth token (prefer a fresh sign-in on this device) |
| `~/.bchubot/memory.sqlite` | Optional | Long-term memories and profile notes |
| `~/.bchubot/alarms.sqlite` | Created when you set a timer/alarm | Local timers and alarms |

You can copy `memory.sqlite` from another machine if you want the same long-term notes. Prefer a **new** Google sign-in on each device rather than copying `google_token.json`.

### 1.7 Google Calendar and Tasks (optional)

Skip this section if you only want local tools (time, weather, calculator, memory, alarms).

1. In [Google Cloud Console](https://console.cloud.google.com/), create or open a project.
2. Enable **Google Calendar API** and **Google Tasks API**.
3. Configure the OAuth consent screen. Add your Google account as a **test user**.
4. Create an OAuth client ID of type **Desktop app**.
5. Download the JSON and save it as:

```text
~/.bchubot/google_credentials.json
```

6. The first time BchuBot calls a Calendar or Tasks tool, a browser window opens **on this computer**. Sign in and accept. That writes `~/.bchubot/google_token.json` (mode `600`).

Headless machines (no browser) will get stuck on that login.

### 1.8 Run the terminal chat

From the repo root, with the venv active and Ollama running:

```bash
source BchuBot-env/bin/activate   # Windows: BchuBot-env\Scripts\activate
python main.py
```

You should see `BchuBot is online.` Type a message and press Enter. Type `exit` to quit.

Try:

```text
What time is it?
What's the weather in Boston?
```

Calendar (after Google setup): `What's on my calendar today?`  
Memory: `Remember that I prefer oat milk.` Then ask what it remembers.  
Timers: `Set a timer for 1 minute.` Timers and local alarms only fire while `main.py` or the web server is running.

Actions such as deleting calendar events or forgetting memories ask for confirmation: type `y` or `N` in this terminal.

### 1.9 Run the local chat page

From the repo root, with the venv active and Ollama running:

```bash
source BchuBot-env/bin/activate
python -m web.server
```

`python -m web.server` means “run the `web.server` package as a program.” Use that form, not `python web.server`.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser on **this** computer.

That page talks to the same `Agent` as `main.py`. Confirmations appear as Allow / Deny in the browser. Replies stream as tokens; a toast and chime fire when a reply finishes. The first click or keypress unlocks audio (browser autoplay rules).

If port 8000 is already in use, stop the other process (the terminal that is running `python -m web.server`, Ctrl+C) and start it again.

After you change Python files, restart this server so it loads the new code.

### 1.10 Everyday use

Each session:

1. Activate the venv (`source BchuBot-env/bin/activate`).
2. Make sure Ollama is running (`ollama list` should work).
3. Start either `python main.py` or `python -m web.server`.

Python packages live in `BchuBot-env`. The model lives in Ollama. Memories and alarms live in `~/.bchubot`. Updating the git repo does not replace those.

### 1.11 Setup checklist

- [ ] Git, Python 3.10+, and Ollama installed
- [ ] `ollama pull qwen3:8b` completed; Ollama running
- [ ] Repo cloned; `cd BchuBot`
- [ ] `BchuBot-env` created on this machine (not copied)
- [ ] venv active; `pip install -r requirements.txt`
- [ ] `python -m unittest discover -s tests -v` passes
- [ ] `~/.bchubot` exists
- [ ] `google_credentials.json` in place only if you want Calendar / Tasks
- [ ] Browser Google login completed on this device (if using Google)
- [ ] `memory.sqlite` copied only if you want old notes
- [ ] `python main.py` or `python -m web.server` then http://127.0.0.1:8000

---

## 2. Adding tools (modules)

A **tool** is a narrow Python function BchuBot is allowed to call: get the time, set a timer, create a calendar event, and so on. The language model never gets a shell, unrestricted files, or arbitrary code execution. You add capability by registering another function.

The `Agent` class does **not** need an `if tool_name == ...` branch. If you follow the registry pattern, the model can call the new tool on the next run.

### 2.1 What you are wiring

```text
LLM tool definition (name, description, parameters)
        ↓
Tool name (string)
        ↓
TOOL_REGISTRY  →  Python function
        ↓
Permission check (AUTOMATIC / CONFIRMATION_REQUIRED / DISABLED)
        ↓
Function result  →  back to the model
```

### 2.2 Files you usually touch

| File | Change |
|---|---|
| `tools/<module>.py` | Implement the function(s), plus `*_DEFINITIONS` and `*_CAPABILITIES` |
| `tools/registry.py` | Import, map the name in `TOOL_REGISTRY`, unpack definitions and capabilities |
| `tools/permissions.py` | Set `AUTOMATIC`, `CONFIRMATION_REQUIRED`, or `DISABLED` |
| `tests/test_<module>.py` | Unit tests that do not need a live model |
| `agent/prompt.py` | Only if the model needs extra usage rules (see §2.7) |
| `web/server.py` | Only if the tool must notify the browser outside a chat reply (alarms do this) |

Do **not** edit `agent/agent.py` to special-case the new tool name.

### 2.3 Write the Python function

Put it in `tools/`. Keep it independently testable. Validate arguments. Return a structured dict when practical (`ok`, plus data or `error`). Never claim success unless the work actually succeeded.

Good (narrow):

```python
def turn_on_light(device_id):
    ...
```

Bad (too broad — do not add tools like this):

```python
def execute_arbitrary_command(command):
    ...
```

Rules:

- No unrestricted `eval()`, shell, filesystem, or network “do anything” APIs.
- Cap string lengths and numeric ranges.
- Catch exceptions and return `{"ok": False, "error": "..."}` rather than crashing the agent.
- Destructive or physical actions should not be `AUTOMATIC` unless you explicitly want that.

### 2.4 Export the LLM schema and a capability blurb

Follow the pattern in `tools/alarms.py`, `tools/memory.py`, and `tools/calendar.py`. Example for a fictional read-only device tool in `tools/lights.py`:

```python
def read_light_status(device_id):
    if not isinstance(device_id, str) or not device_id.strip():
        return {"ok": False, "error": "A device_id is required."}
    device_id = device_id.strip()
    # Call your real backend here (for example Home Assistant).
    return {"ok": True, "device_id": device_id, "on": False}


def set_light_state(device_id, on):
    if not isinstance(device_id, str) or not device_id.strip():
        return {"ok": False, "error": "A device_id is required."}
    if not isinstance(on, bool):
        return {"ok": False, "error": "on must be true or false."}
    # Call your real backend here.
    return {"ok": True, "device_id": device_id.strip(), "on": on}


LIGHT_CAPABILITIES = {
    "read_light_status": (
        "Reads whether a named light is on. Requires a configured home hub."
    ),
    "set_light_state": (
        "Turns a named light on or off. Requires a configured home hub."
    ),
}

LIGHT_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_light_status",
            "description": (
                "Get whether a light is on. Use a device_id such as 'desk_lamp'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Light id, such as desk_lamp.",
                    }
                },
                "required": ["device_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_light_state",
            "description": "Turn a light on or off. Never guess that it worked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Light id, such as desk_lamp.",
                    },
                    "on": {
                        "type": "boolean",
                        "description": "True to turn on, false to turn off.",
                    },
                },
                "required": ["device_id", "on"],
            },
        },
    },
]
```

The `description` on the function is what the model reads when it decides whether to call the tool. Be explicit about when to use it and what not to confuse it with.

Older tools (`get_time`, `get_date`, `calculator`, `get_weather`) still keep their schemas inside `tools/registry.py`. New tools should keep schemas in their own module.

### 2.5 Register the tool

In `tools/registry.py`:

1. Import the functions, `LIGHT_CAPABILITIES`, and `LIGHT_DEFINITIONS`.
2. Add each name to `TOOL_REGISTRY`.
3. Unpack capabilities into `TOOL_CAPABILITIES`.
4. Unpack definitions into `TOOL_DEFINITIONS`.

```python
from tools.lights import (
    LIGHT_CAPABILITIES,
    LIGHT_DEFINITIONS,
    read_light_status,
    set_light_state,
)

TOOL_REGISTRY = {
    # ...existing tools...
    "read_light_status": read_light_status,
    "set_light_state": set_light_state,
}

TOOL_CAPABILITIES = {
    # ...existing blurbs...
    **LIGHT_CAPABILITIES,
}

TOOL_DEFINITIONS = [
    # ...existing schemas...
    *LIGHT_DEFINITIONS,
]
```

`describe_capabilities()` builds the “you have these tools” section of the system prompt from `TOOL_CAPABILITIES`. If a name is in `TOOL_REGISTRY` but missing from `TOOL_CAPABILITIES`, `tests/test_registry.py` fails.

### 2.6 Set a permission

In `tools/permissions.py`:

```python
TOOL_PERMISSIONS = {
    # ...
    "read_light_status": AUTOMATIC,
    "set_light_state": CONFIRMATION_REQUIRED,
}
```

| Level | Meaning |
|---|---|
| `AUTOMATIC` | Run without asking (time, weather, list alarms, read calendar) |
| `CONFIRMATION_REQUIRED` | CLI asks `y/N`; the web UI shows Allow / Deny |
| `DISABLED` | The agent tells the model the tool is disabled |

The **user/application** chooses the level, not the model. If you omit a name, `permission_for()` defaults to `CONFIRMATION_REQUIRED`.

Use `CONFIRMATION_REQUIRED` (or `DISABLED`) for anything that writes to an external account, deletes data, or changes the physical world.

### 2.7 Optional prompt rules

`agent/prompt.py` already injects `describe_capabilities()`. Add extra bullets only when the model needs disambiguation, for example:

- Prefer `set_timer` over Google Calendar for “in 10 minutes.”
- Never claim a light changed unless `ok` is true.

Keep those rules factual. Do not invent tools that are not registered.

### 2.8 Tests

Add `tests/test_lights.py` (or similar) that calls the Python functions directly. Mock network or hardware. Then:

```bash
python -m unittest discover -s tests -v
```

Restart `python main.py` or `python -m web.server` before trying the tool in chat.

### 2.9 Browser-only extras

Most tools need no UI work: the model calls them, and the reply text is enough.

Add a web hook only when something must happen **outside** the chat transcript (local alarms toast and chime via `add_alarm_listener` in `web/server.py`). Device control that only reports success in the assistant message does not need that.

### 2.10 Current registered tools

These names are in `TOOL_REGISTRY` today:

| Tool | Role |
|---|---|
| `get_time`, `get_date` | Local clock |
| `calculator` | Local arithmetic |
| `get_weather` | Open-Meteo, needs a place name |
| `read_calendar`, `create_calendar_event`, `create_reminder`, `delete_calendar_event` | Google Calendar |
| `read_task_lists`, `read_tasks`, `create_task`, `create_task_list` | Google Tasks |
| `read_today` | Combined local day view (calendar + tasks) |
| `write_memory`, `read_memory`, `update_memory`, `forget_memory` | SQLite long-term notes |
| `set_timer`, `set_alarm`, `list_alarms`, `cancel_alarm` | Local timers/alarms |

### 2.11 Checklist for a new tool

- [ ] Function in `tools/` with validation and structured results
- [ ] `*_DEFINITIONS` and `*_CAPABILITIES` in that module
- [ ] Name mapped in `TOOL_REGISTRY`
- [ ] Capabilities and definitions unpacked in `tools/registry.py`
- [ ] Permission set in `tools/permissions.py`
- [ ] Tests pass
- [ ] Prompt extras only if needed
- [ ] Server/CLI restarted
- [ ] You verified the tool actually succeeded before expecting the bot to say it did

---

## 3. System architecture

BchuBot is still in **Agent Core v0.1**. The long-term plan is in `PROJECT_ROADMAP.md`. The running system is a local agent plus tools, not the full smart-home / voice stack.

### 3.1 High-level flow

```text
You (terminal or http://127.0.0.1:8000)
        ↓
main.py  or  FastAPI + WebSocket (web/server.py)
        ↓
Agent (agent/agent.py) via create_agent() (agent/factory.py)
        ↓
Ollama chat API  →  local model (default qwen3:8b)
        ↓
Answer directly, or request one or more tools
        ↓
Permission check (tools/permissions.py)
        ↓
Python function (tools/registry.py → tools/*.py)
        ↓
Tool result appended to the conversation
        ↓
Model sees the result and either calls another tool or replies
```

Multi-step example: “What’s on my calendar today, then set a 10-minute timer.”

```text
You → Agent → LLM → read_today → LLM → set_timer → LLM → final reply
```

There is a cap on tool rounds per turn (`DEFAULT_MAX_TOOL_ROUNDS` in `agent/agent.py`) so a confused model cannot loop forever.

### 3.2 Main components

| Piece | Location | Job |
|---|---|---|
| CLI | `main.py` | Stdin chat loop; prints alarm fires |
| Web UI | `web/static/index.html`, `web/server.py` | Local page, streaming, confirmations, stats, alarm toasts |
| Host stats | `web/stats.py` | CPU / RAM / load chips (macOS commands; not sent to the model) |
| Agent | `agent/agent.py` | History, Ollama call, generic tool loop, streaming |
| Factory | `agent/factory.py` | Builds an Agent with the system prompt and memory retrieval hook |
| Prompt | `agent/prompt.py` | Personality, tool usage rules, `MODEL` name |
| Registry | `tools/registry.py` | Name → function, schemas sent to Ollama |
| Permissions | `tools/permissions.py` | Who may run a tool without asking |
| Tools | `tools/*.py` | Narrow capabilities (weather, calendar, memory, alarms, …) |
| Google auth | `tools/google_auth.py` | OAuth token for Calendar and Tasks |
| Tests | `tests/` | Unit tests; run without a live model |

### 3.3 Conversation and memory

**Short-term:** the `Agent.messages` list for this process. Closing the CLI or restarting the web server clears it.

**Long-term:** SQLite at `~/.bchubot/memory.sqlite`. The model can `write_memory` / `read_memory` / `update_memory` / `forget_memory`. On each user turn, `memories_for_prompt()` may attach profile notes plus a few related memories to the **first system message only**. Stored chat history stays as your raw text. The web UI may show “Using stored notes…”.

The model is instructed not to invent stored facts. If nothing was attached and `read_memory` is empty, it should say so.

### 3.4 Interfaces and data stores

```text
                    ┌─────────────┐
                    │   Ollama    │  127.0.0.1:11434
                    │  qwen3:8b   │
                    └──────▲──────┘
                           │
┌────────┐  stdin   ┌──────┴──────┐  tools   ┌─────────────────────┐
│  You   ├─────────►│   Agent     ├─────────►│  Python tools        │
│        │◄─────────┤             │◄─────────┤  registry+permissions│
└────▲───┘  reply   └──────▲──────┘          └──────────┬──────────┘
     │                     │                            │
     │    WebSocket        │                            ├── ~/.bchubot/memory.sqlite
     │    127.0.0.1:8000   │                            ├── ~/.bchubot/alarms.sqlite
     └─────────────────────┘                            ├── Google Calendar / Tasks
                                                        └── Open-Meteo (weather)
```

- **Ollama** is the only LLM. The app does not send chat to a cloud model provider.
- **Open-Meteo** is used for weather (public geocoding + forecast).
- **Google** is used only if you added credentials and the model calls Calendar/Tasks tools.
- **Alarms** use a background scheduler thread. They notify this Mac (and the web page) only while the CLI or web server is running.

Home Assistant, ESP32, wake-word, and speech I/O are roadmap items, not part of the current runtime.

### 3.5 Permissions and honesty

The model proposes a tool call. The application decides whether it runs. After it runs, the model must use the tool’s return value. BchuBot is prompted never to say an action succeeded unless the tool returned success (`ok: True` where that pattern is used).

### 3.6 Trust boundary

The model is untrusted with the operating system. Tools are the only way it can affect the world, and each tool should stay small. Adding a module is the supported way to grow BchuBot. Giving it a general shell or `eval` tool is not.

---

## Related files

| File | Contents |
|---|---|
| `SETUP.md` | Short new-device checklist |
| `PROJECT_ROADMAP.md` | Phases and long-term direction |
| `AGENTS.md` | Conventions for people (and coding agents) working in this repo |
| `requirements.txt` | Python packages to `pip install` |
