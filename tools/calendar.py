from datetime import timedelta

from tools.dates import day_bounds, parse_datetime, resolve_day
from tools.google_auth import GoogleAuthError, calendar_service


def read_calendar(start=None, end=None):
    """Read events from the user's primary Google Calendar."""
    try:
        start_day = resolve_day(start or "today")
        end_day = resolve_day(end or start or "today")
        if end_day < start_day:
            return {"ok": False, "error": "End date is before start date."}

        time_min, _ = day_bounds(start_day)
        _, time_max = day_bounds(end_day)
        result = (
            calendar_service()
            .events()
            .list(
                calendarId="primary",
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
        return {
            "ok": True,
            "start": start_day.isoformat(),
            "end": end_day.isoformat(),
            "events": [_format_event(item) for item in result.get("items", [])],
        }
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not read the calendar."}


def create_calendar_event(title, start, end=None, reminder_minutes=30):
    """Create an event on the user's primary Google Calendar."""
    if not isinstance(title, str) or not title.strip():
        return {"ok": False, "error": "An event title is required."}

    try:
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end) if end else start_dt + timedelta(hours=1)
        if end_dt <= start_dt:
            return {"ok": False, "error": "End time must be after start time."}

        body = {
            "summary": title.strip(),
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
            "reminders": _reminders(reminder_minutes),
        }
        created = (
            calendar_service()
            .events()
            .insert(calendarId="primary", body=body)
            .execute()
        )
        return {"ok": True, "event": _format_event(created)}
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not create the calendar event."}


def create_reminder(title, when, reminder_minutes=0):
    """Create a short timed reminder on the user's Google Calendar."""
    if not isinstance(title, str) or not title.strip():
        return {"ok": False, "error": "A reminder title is required."}

    try:
        start_dt = parse_datetime(when)
        end_dt = start_dt + timedelta(minutes=15)
        body = {
            "summary": title.strip(),
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
            "reminders": _reminders(reminder_minutes),
        }
        created = (
            calendar_service()
            .events()
            .insert(calendarId="primary", body=body)
            .execute()
        )
        return {"ok": True, "event": _format_event(created)}
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not create the reminder."}


def delete_calendar_event(event_id=None, title=None, day=None):
    """Cancel and delete an event from the user's primary Google Calendar."""
    has_event_id = isinstance(event_id, str) and bool(event_id.strip())
    has_title = isinstance(title, str) and bool(title.strip())
    if not has_event_id and not has_title:
        return {
            "ok": False,
            "error": "An event_id or title is required to delete an event.",
        }

    try:
        service = calendar_service()
        if has_event_id:
            return _delete_event_by_id(service, event_id.strip())

        matches = _find_events_by_title(service, title.strip(), day or "today")
        if not matches:
            return {"ok": False, "error": f"Could not find an event titled '{title}'."}
        if len(matches) > 1:
            return {
                "ok": False,
                "error": "Multiple events matched that title. Use event_id.",
                "events": [_format_event(item) for item in matches],
            }

        return _delete_event_by_id(service, matches[0]["id"])
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not delete the calendar event."}


def _delete_event_by_id(service, event_id):
    existing = (
        service.events()
        .get(calendarId="primary", eventId=event_id)
        .execute()
    )
    service.events().delete(
        calendarId="primary",
        eventId=event_id,
        sendUpdates="all",
    ).execute()
    return {"ok": True, "deleted": _format_event(existing)}


def _find_events_by_title(service, title, day):
    wanted = title.strip().lower()
    start_day = resolve_day(day)
    time_min, time_max = day_bounds(start_day)
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        )
        .execute()
    )
    return [
        item
        for item in result.get("items", [])
        if (item.get("summary") or "").strip().lower() == wanted
    ]


def _reminders(reminder_minutes):
    if reminder_minutes in (None, ""):
        return {"useDefault": True}
    minutes = int(reminder_minutes)
    if minutes < 0:
        raise ValueError("Reminder minutes cannot be negative.")
    return {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": minutes}],
    }


def _format_event(event):
    start = event.get("start") or {}
    end = event.get("end") or {}
    return {
        "id": event.get("id"),
        "title": event.get("summary") or "(No title)",
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": event.get("location"),
    }


CALENDAR_CAPABILITIES = {
    "read_calendar": (
        "Reads events from the user's primary Google Calendar. "
        "Dates can be today, tomorrow, or YYYY-MM-DD."
    ),
    "create_calendar_event": (
        "Creates an event on the user's primary Google Calendar. "
        "This changes the user's real calendar and requires confirmation."
    ),
    "create_reminder": (
        "Creates a short timed reminder on the user's Google Calendar. "
        "This changes the user's real calendar and requires confirmation."
    ),
    "delete_calendar_event": (
        "Cancels and deletes an event from the user's primary Google Calendar "
        "by event_id or by title and day. This changes the user's real "
        "calendar and requires confirmation."
    ),
}

CALENDAR_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_calendar",
            "description": (
                "Read events from the user's primary Google Calendar "
                "for a date range. Use today, tomorrow, or YYYY-MM-DD."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date. Defaults to today.",
                    },
                    "end": {
                        "type": "string",
                        "description": "End date. Defaults to the start date.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": (
                "Create an event on the user's primary Google Calendar. "
                "start and end should be ISO date/times such as "
                "2026-09-14T09:00."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title.",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date/time in ISO format.",
                    },
                    "end": {
                        "type": "string",
                        "description": (
                            "End date/time in ISO format. "
                            "Defaults to one hour after start."
                        ),
                    },
                    "reminder_minutes": {
                        "type": "integer",
                        "description": (
                            "Popup reminder minutes before the event. "
                            "Defaults to 30."
                        ),
                    },
                },
                "required": ["title", "start"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": (
                "Create a short timed reminder on the user's Google Calendar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Reminder title.",
                    },
                    "when": {
                        "type": "string",
                        "description": "When the reminder should occur, ISO format.",
                    },
                    "reminder_minutes": {
                        "type": "integer",
                        "description": (
                            "Popup minutes before the time. Defaults to 0."
                        ),
                    },
                },
                "required": ["title", "when"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": (
                "Cancel and delete an event from the user's primary Google "
                "Calendar. Prefer event_id from read_calendar or read_today. "
                "If the id is unknown, use title and day."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Google Calendar event id.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title, used if event_id is unknown.",
                    },
                    "day": {
                        "type": "string",
                        "description": (
                            "Day to search when using title. "
                            "today, tomorrow, or YYYY-MM-DD. Defaults to today."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]
