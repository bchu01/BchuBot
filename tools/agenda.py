from tools.calendar import read_calendar
from tools.tasks import read_tasks


def read_today():
    """Read today's Google Calendar events and Google Tasks due today."""
    calendar = read_calendar(start="today", end="today")
    if not calendar.get("ok"):
        return calendar

    tasks = read_tasks(due="today")
    if not tasks.get("ok"):
        return tasks

    return {
        "ok": True,
        "date": calendar["start"],
        "events": calendar["events"],
        "tasks": tasks["tasks"],
    }


AGENDA_CAPABILITIES = {
    "read_today": (
        "Reads today's Google Calendar events and Google Tasks due today. "
        "Use this for 'what do I need to do today' or before making a schedule."
    ),
}

AGENDA_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_today",
            "description": (
                "Read today's Google Calendar events and tasks due today. "
                "Use this when the user asks what they need to do today "
                "or wants a daily schedule."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
