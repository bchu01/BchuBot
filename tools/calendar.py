from datetime import datetime, time, timedelta, timezone

from tools.dates import day_bounds, parse_datetime, resolve_day
from tools.google_auth import GoogleAuthError, calendar_service


FREQUENCIES = {
    "daily": "DAILY",
    "weekly": "WEEKLY",
    "monthly": "MONTHLY",
    "yearly": "YEARLY",
}

WEEKDAYS = {
    "mo": "MO",
    "tu": "TU",
    "we": "WE",
    "th": "TH",
    "fr": "FR",
    "sa": "SA",
    "su": "SU",
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}

MAX_RECURRENCE_COUNT = 104
MAX_RECURRENCE_INTERVAL = 52


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


def create_calendar_event(
    title,
    start,
    end=None,
    reminder_minutes=30,
    recurrence=None,
    recurrence_interval=1,
    recurrence_count=None,
    recurrence_until=None,
    recurrence_days=None,
):
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
            "start": _event_when(start_dt),
            "end": _event_when(end_dt),
            "reminders": _reminders(reminder_minutes),
        }
        rule = _recurrence_rule(
            recurrence,
            interval=recurrence_interval,
            count=recurrence_count,
            until=recurrence_until,
            days=recurrence_days,
        )
        if rule:
            body["recurrence"] = rule
            tz = _iana_timezone(start_dt)
            body["start"]["timeZone"] = tz
            body["end"]["timeZone"] = tz

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


def delete_calendar_event(
    event_id=None,
    title=None,
    day=None,
    scope="this",
    event_ids=None,
):
    """Cancel and delete one event, several events, or a recurring series."""
    ids = _parse_event_ids(event_id, event_ids)
    has_title = isinstance(title, str) and bool(title.strip())
    if not ids and not has_title:
        return {
            "ok": False,
            "error": "An event_id, event_ids, or title is required to delete.",
        }

    try:
        scope_name = _normalize_scope(scope)
        service = calendar_service()
        if ids:
            deleted = [
                _delete_event_by_id(service, item_id, scope_name) for item_id in ids
            ]
            payload = {
                "ok": True,
                "scope": scope_name,
                "deleted": deleted[0] if len(deleted) == 1 else deleted,
            }
            return payload

        matches = _find_events_by_title(service, title.strip(), day or "today")
        if not matches:
            return {"ok": False, "error": f"Could not find an event titled '{title}'."}
        if len(matches) > 1 and not _same_series(matches, scope_name):
            return {
                "ok": False,
                "error": "Multiple events matched that title. Use event_id.",
                "events": [_format_event(item) for item in matches],
            }

        deleted = _delete_event_by_id(service, matches[0]["id"], scope_name)
        return {"ok": True, "scope": scope_name, "deleted": deleted}
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not delete the calendar event."}


def _delete_event_by_id(service, event_id, scope="this"):
    existing = (
        service.events()
        .get(calendarId="primary", eventId=event_id)
        .execute()
    )
    target_id = _delete_target_id(existing, scope)
    service.events().delete(
        calendarId="primary",
        eventId=target_id,
        sendUpdates="all",
    ).execute()
    deleted = _format_event(existing)
    deleted["deleted_id"] = target_id
    deleted["scope"] = _normalize_scope(scope)
    return deleted


def _delete_target_id(event, scope):
    scope_name = _normalize_scope(scope)
    if scope_name == "all":
        return event.get("recurringEventId") or event.get("id")
    return event.get("id")


def _normalize_scope(scope):
    if scope in (None, ""):
        return "this"
    if not isinstance(scope, str):
        raise ValueError("Scope must be 'this' or 'all'.")
    scope_name = scope.strip().lower()
    if scope_name not in {"this", "all"}:
        raise ValueError("Scope must be 'this' or 'all'.")
    return scope_name


def _parse_event_ids(event_id, event_ids):
    ids = []
    if isinstance(event_id, str) and event_id.strip():
        ids.append(event_id.strip())
    if isinstance(event_ids, str):
        ids.extend(part.strip() for part in event_ids.split(",") if part.strip())
    elif isinstance(event_ids, (list, tuple)):
        ids.extend(str(part).strip() for part in event_ids if str(part).strip())
    elif event_ids not in (None, ""):
        raise ValueError("event_ids must be a list or comma-separated ids.")

    unique = []
    for item in ids:
        if item not in unique:
            unique.append(item)
    if len(unique) > 20:
        raise ValueError("You can delete at most 20 events at once.")
    return unique


def _same_series(matches, scope):
    if scope != "all" or not matches:
        return False
    series_ids = {
        item.get("recurringEventId") or item.get("id") for item in matches
    }
    return len(series_ids) == 1


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


def _recurrence_rule(frequency, interval=1, count=None, until=None, days=None):
    if frequency in (None, ""):
        return None
    if not isinstance(frequency, str):
        raise ValueError("Recurrence must be daily, weekly, monthly, or yearly.")

    freq = FREQUENCIES.get(frequency.strip().lower())
    if freq is None:
        raise ValueError("Recurrence must be daily, weekly, monthly, or yearly.")

    try:
        interval_value = int(interval or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("Recurrence interval must be a whole number.") from exc
    if interval_value < 1 or interval_value > MAX_RECURRENCE_INTERVAL:
        raise ValueError("Recurrence interval must be between 1 and 52.")

    parts = [f"FREQ={freq}", f"INTERVAL={interval_value}"]

    weekday_codes = _parse_weekdays(days)
    if weekday_codes:
        if freq != "WEEKLY":
            raise ValueError("Days of the week are only used for weekly events.")
        parts.append("BYDAY=" + ",".join(weekday_codes))

    has_count = count not in (None, "")
    has_until = until not in (None, "")
    if has_count and has_until:
        raise ValueError("Use recurrence_count or recurrence_until, not both.")

    if has_count:
        try:
            count_value = int(count)
        except (TypeError, ValueError) as exc:
            raise ValueError("Recurrence count must be a whole number.") from exc
        if count_value < 1 or count_value > MAX_RECURRENCE_COUNT:
            raise ValueError(
                f"Recurrence count must be between 1 and {MAX_RECURRENCE_COUNT}."
            )
        parts.append(f"COUNT={count_value}")
    elif has_until:
        until_day = resolve_day(until)
        until_dt = datetime.combine(until_day, time.max, tzinfo=timezone.utc)
        parts.append("UNTIL=" + until_dt.strftime("%Y%m%dT%H%M%SZ"))

    return ["RRULE:" + ";".join(parts)]


def _parse_weekdays(days):
    if days in (None, ""):
        return []
    if isinstance(days, (list, tuple)):
        tokens = [str(item) for item in days]
    elif isinstance(days, str):
        tokens = [item.strip() for item in days.replace(";", ",").split(",")]
    else:
        raise ValueError("Recurrence days must be text such as 'Monday,Wednesday'.")

    codes = []
    for token in tokens:
        if not token:
            continue
        code = WEEKDAYS.get(token.strip().lower())
        if code is None:
            raise ValueError(f"Unknown weekday: {token}")
        if code not in codes:
            codes.append(code)
    return codes


def _event_when(dt):
    return {"dateTime": dt.isoformat()}


def _iana_timezone(dt):
    key = getattr(dt.tzinfo, "key", None) if dt.tzinfo else None
    return key or "UTC"


def _format_event(event):
    start = event.get("start") or {}
    end = event.get("end") or {}
    formatted = {
        "id": event.get("id"),
        "title": event.get("summary") or "(No title)",
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": event.get("location"),
    }
    if event.get("recurrence"):
        formatted["recurrence"] = event.get("recurrence")
    if event.get("recurringEventId"):
        formatted["recurring_event_id"] = event.get("recurringEventId")
    return formatted


CALENDAR_CAPABILITIES = {
    "read_calendar": (
        "Reads events from the user's primary Google Calendar. "
        "Dates can be today, tomorrow, or YYYY-MM-DD."
    ),
    "create_calendar_event": (
        "Creates an event on the user's primary Google Calendar. "
        "Can repeat daily, weekly, monthly, or yearly. "
        "This changes the user's real calendar and requires confirmation."
    ),
    "create_reminder": (
        "Creates a short timed reminder on the user's Google Calendar. "
        "This changes the user's real calendar and requires confirmation."
    ),
    "delete_calendar_event": (
        "Cancels and deletes Google Calendar events by event_id, event_ids, "
        "or title and day. scope 'this' deletes one occurrence; scope 'all' "
        "deletes a repeating series. Requires confirmation."
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
                "2026-09-14T09:00. For repeating events, set recurrence "
                "to daily, weekly, monthly, or yearly."
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
                    "recurrence": {
                        "type": "string",
                        "description": (
                            "How often the event repeats: daily, weekly, "
                            "monthly, or yearly. Omit for a one-time event."
                        ),
                    },
                    "recurrence_interval": {
                        "type": "integer",
                        "description": (
                            "Repeat every N periods. 2 with weekly means "
                            "every other week. Defaults to 1."
                        ),
                    },
                    "recurrence_count": {
                        "type": "integer",
                        "description": (
                            "Number of occurrences. Do not also set "
                            "recurrence_until."
                        ),
                    },
                    "recurrence_until": {
                        "type": "string",
                        "description": (
                            "Last date to repeat, YYYY-MM-DD. Do not also "
                            "set recurrence_count."
                        ),
                    },
                    "recurrence_days": {
                        "type": "string",
                        "description": (
                            "For weekly events, days such as "
                            "'Monday,Wednesday' or 'MO,WE'."
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
                "Cancel and delete Google Calendar events. Prefer event_id "
                "from read_calendar or read_today. Use scope 'all' to delete "
                "a repeating series, or event_ids to delete several events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Google Calendar event id.",
                    },
                    "event_ids": {
                        "type": "string",
                        "description": (
                            "Comma-separated event ids when deleting "
                            "more than one event."
                        ),
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
                    "scope": {
                        "type": "string",
                        "description": (
                            "'this' deletes one occurrence. 'all' deletes "
                            "the whole repeating series. Defaults to this."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]
