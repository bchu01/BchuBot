# BchuBot — Agent Instructions

## 1. Project Identity

BchuBot is a privacy-focused, personal agentic AI assistant being developed as a learning project.

The long-term goal is for BchuBot to:

* Communicate naturally through text and voice
* Maintain short-term and long-term memory
* Understand the primary user and their preferences
* Access approved tools
* Manage calendar events, reminders, alarms, and other productivity tasks
* Control smart-home devices
* Communicate with ESP32 devices
* Eventually automate routines in the user's physical environment
* Run primarily on the user's own computer
* Keep personal information private whenever practical

The project prioritizes:

1. Correctness
2. Security
3. Privacy
4. Understandability
5. Modularity
6. Reliability
7. Performance
8. Convenience

---

# 2. Project Roadmap

The long-term architecture, development phases, and project vision are documented in:

`PROJECT_ROADMAP.md`

Treat `PROJECT_ROADMAP.md` as the canonical source of truth for the project's long-term direction.

Before making significant architectural decisions:

1. Check `PROJECT_ROADMAP.md`.
2. Check the existing implementation.
3. Determine which development phase the requested change belongs to.
4. Do not implement future architecture prematurely.

If the roadmap and existing code appear inconsistent, do not blindly rewrite the project. Explain the discrepancy and preserve working functionality unless a change is explicitly requested.

---

# 3. Current Development Milestone

BchuBot is currently completing:

## Agent Core v0.1

The current foundation includes:

* Python
* Ollama
* Qwen3 8B
* Agent class
* Conversation history
* BchuBot system prompt/personality
* Tool definitions
* Tool registry
* Tool arguments
* Generic tool execution
* Multi-step agent loop

The immediate objective is to verify that this foundation works reliably.

Do not jump ahead and implement the complete memory, voice, smart-home, or automation architecture unless explicitly asked.

---

# 4. Current Project Structure

The project currently follows approximately:

```text
BchuBot/
├── AGENTS.md
├── PROJECT_ROADMAP.md
│
├── agent/
│   ├── __init__.py
│   └── agent.py
│
├── tools/
│   ├── __init__.py
│   ├── basic.py
│   └── registry.py
│
├── main.py
├── requirements.txt
└── .gitignore
```

This structure will evolve as the project grows.

Do not create large numbers of empty directories or files simply to match the future architecture.

Introduce components when they are actually needed.

---

# 5. Development Environment

The primary development environment is macOS.

The repository is located at:

```text
/Users/brandonchu/Documents/BC_Projects/BchuBot
```

Do not hardcode this absolute path into application code.

The local Git repository is already connected to a remote GitHub repository.

Do not recreate the Git repository or remote.

---

# 6. Technology Principles

## LLM

The current local LLM runtime is:

```text
Ollama
```

The current model is:

```text
Qwen3 8B
```

The model should remain configurable.

Avoid tightly coupling the entire application to one specific model.

---

## Python

Python is the primary application language.

Use standard Python features and simple dependencies whenever possible.

Avoid introducing frameworks or libraries without a concrete reason.

---

## Memory

SQLite is the planned first persistent-memory solution.

Do not introduce a vector database unless the project actually needs semantic retrieval at scale.

---

## Smart Home

The planned smart-home architecture is:

```text
BchuBot
    ↓
Home Assistant
    ↓
ESP32 / smart devices
    ↓
Physical appliances
```

Prefer Home Assistant as the abstraction layer rather than giving BchuBot direct unrestricted access to individual devices.

---

# 7. Agent Architecture

The core agent should conceptually work like:

```text
User
 ↓
BchuBot Agent
 ↓
Local LLM
 ↓
Tool decision
 ↓
Tool Registry
 ↓
Python Tool
 ↓
Tool Result
 ↓
Local LLM
 ↓
Final Response
```

The agent should support multiple tool calls:

```text
User
 ↓
LLM
 ↓
Tool A
 ↓
LLM
 ↓
Tool B
 ↓
LLM
 ↓
Final response
```

Do not implement tool-specific branching directly inside the Agent class.

Avoid patterns such as:

```python
if tool_name == "get_time":
    ...
elif tool_name == "get_weather":
    ...
elif tool_name == "calendar":
    ...
```

Use the tool registry architecture instead.

---

# 8. Tool Architecture

Tools should be modular and independently testable.

The intended architecture is:

```text
LLM Tool Definition
        ↓
Tool Name
        ↓
Tool Registry
        ↓
Python Function
        ↓
Tool Result
```

The registry should map tool names to callable Python functions.

Example:

```python
TOOL_REGISTRY = {
    "get_time": get_time,
    "calculator": calculator,
}
```

Tool definitions exposed to the LLM should clearly specify:

* Name
* Description
* Parameters
* Required parameters
* Expected argument types

Tools should validate their inputs.

Tools should return useful, structured results whenever practical.

---

# 9. Tool Safety

The LLM must never receive unrestricted access to:

* The operating system
* Shell commands
* Arbitrary Python execution
* The filesystem
* Network resources
* Physical devices

Tools should provide narrow, explicit capabilities.

For example:

```text
turn_on_light("desk_lamp")
```

is preferable to:

```text
execute_arbitrary_command(...)
```

Never use unrestricted `eval()` in production.

The current calculator may use `eval()` temporarily as a prototype for demonstrating tool arguments, but it must eventually be replaced with a safe expression evaluator.

---

# 10. Permissions

As BchuBot gains more powerful tools, introduce explicit permissions.

Possible permission levels:

```text
READ_ONLY
CONFIRMATION_REQUIRED
AUTOMATIC
DISABLED
```

Examples:

```text
get_time()
→ AUTOMATIC

read_calendar()
→ AUTOMATIC

create_calendar_event()
→ potentially CONFIRMATION_REQUIRED

turn_off_light()
→ AUTOMATIC if explicitly configured

unlock_door()
→ CONFIRMATION_REQUIRED or DISABLED
```

Do not allow the LLM to decide its own permission level.

Permissions must be controlled by the application/user.

---

# 11. Action Confirmation

BchuBot must never claim an action succeeded unless the underlying tool actually succeeded.

For example:

User:

> Turn off my desk lamp.

If the tool succeeds:

> Done — your desk lamp is off.

If the tool fails:

> I couldn't turn off your desk lamp because the device was unreachable.

Never say:

> Done!
