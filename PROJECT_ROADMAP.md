# BchuBot Project Roadmap

## Vision

BchuBot is a personal, privacy-focused, agentic AI assistant designed to run primarily on the user's own computer.

Long-term goals include:
- Natural text and voice interaction
- Persistent memory
- Calendar access
- Alarms and timers
- Reminders and productivity tools
- Smart-home control
- ESP32-connected devices
- Room/environmental sensors
- Multi-step automation
- Wake-word support

Priorities:
1. Correctness
2. Security
3. Privacy
4. Understandability
5. Modularity
6. Reliability
7. Performance
8. Convenience

## Current stack

- Python
- Ollama
- Qwen3 8B
- Git + GitHub
- SQLite planned for persistent memory
- Home Assistant planned for smart-home abstraction
- ESP32 planned for physical devices

The user develops primarily on macOS.

Project directory:
`/Users/brandonchu/Documents/BC_Projects/BchuBot`

## Development timeline

### Phase 1 — Foundation
Status: COMPLETE

- Repository
- Python environment
- Git/GitHub
- Ollama
- Local model
- Project structure

### Phase 2 — Local AI Brain
Status: COMPLETE

- Python → Ollama
- Prompt/response
- Conversation history
- BchuBot system prompt
- Agent class

### Phase 3 — Agent Core
Status: CURRENT / NEAR COMPLETION

- Tool definitions
- Tool registry
- Tool arguments
- Generic tool execution
- Multi-step agent loop
- Error handling
- Tool execution boundaries

Current milestone:
**BchuBot Agent Core v0.1**

### Phase 4 — Tool Ecosystem
NEXT

Build tools incrementally, preferably with Cursor.

Potential order:
1. Safe calculator
2. Date/time
3. Weather
4. Calendar read
5. Calendar write
6. Local alarms/timers
7. Memory read/write
8. Home Assistant read
9. Home Assistant device control
10. ESP32 integration

Each tool should be independently testable.

### Phase 5 — Memory

Use SQLite initially.

Separate:
- Short-term conversation
- Long-term memories
- Stable user profile

Do not dump the entire database into every prompt. Retrieve only relevant context.

### Phase 6 — Permissions and Security

Introduce explicit permission levels such as:
- READ_ONLY
- CONFIRMATION_REQUIRED
- AUTOMATIC
- DISABLED

The user controls which tools can act automatically.

Never claim an action succeeded unless the underlying tool actually succeeded.

### Phase 7 — Digital Integrations

Calendar, reminders, alarms, weather, notes, etc.

Prefer local solutions when practical. Use cloud APIs only when necessary.

### Phase 8 — Smart Home

Preferred architecture:

BchuBot → Home Assistant → ESP32/devices

Avoid giving the LLM direct unrestricted control over arbitrary devices or network services.

### Phase 9 — User Interface

Start with CLI.

Later consider:
- FastAPI
- WebSocket
- HTML/CSS/JavaScript
- React only if justified

### Phase 10 — Voice

Target architecture:

Microphone
→ Speech-to-Text
→ BchuBot Agent
→ Tools/Memory/LLM
→ Text-to-Speech
→ Speaker

Prefer local speech processing when practical.

### Phase 11 — Wake Word

Eventually support a phrase such as:
"Hey BchuBot"

Wake-word detection should be separate from the main agent.

### Phase 12 — Automation

Build deterministic routines that can be triggered through natural language.

Example:
"Good night"

Could eventually invoke:
- Turn off lights
- Turn off selected devices
- Set alarm
- Check tomorrow's calendar
- Report wake-up time

The LLM interprets intent; deterministic workflows should perform critical actions.

## Final architecture target

Conceptually:

User
→ Interface
→ BchuBot Agent
→ LLM + Memory + Tools + Permissions
→ Calendar / Alarms / Home Assistant / ESP32

Do not implement the entire target architecture at once. Build only what is needed for the current milestone.
