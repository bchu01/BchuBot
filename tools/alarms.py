import os
import subprocess
import sys
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from tools.dates import local_now, parse_clock_time, parse_datetime, resolve_day


KINDS = {"timer", "alarm"}
PENDING = "pending"
FIRED = "fired"
CANCELLED = "cancelled"
MISSED = "missed"
MAX_LABEL_LENGTH = 200
MAX_PENDING = 20
MAX_TIMER = timedelta(days=7)
MISSED_AFTER = timedelta(minutes=5)
MAX_WAIT_SECONDS = 30

_lock = threading.Lock()
_stop = threading.Event()
_wake = threading.Event()
_thread = None
_listeners = []


def _db_path():
    override = os.environ.get("BCHUBOT_ALARMS_DB")
    if override:
        return Path(override)
    return Path.home() / ".bchubot" / "alarms.sqlite"


@contextmanager
def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                fires_at TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def set_timer(minutes=0, seconds=0, hours=0, label="Timer"):
    """Set a local countdown timer that fires on this computer."""
    try:
        duration = timedelta(
            hours=_as_nonneg_number(hours),
            minutes=_as_nonneg_number(minutes),
            seconds=_as_nonneg_number(seconds),
        )
    except ValueError:
        return {"ok": False, "error": "Timer length must be a number of hours, minutes, or seconds."}

    if duration.total_seconds() < 1:
        return {"ok": False, "error": "A timer must be at least one second."}
    if duration > MAX_TIMER:
        return {"ok": False, "error": "A timer can be at most 7 days."}

    return _create("timer", local_now() + duration, label, default_label="Timer")


def set_alarm(label="Alarm", when=None, time=None, day=None):
    """Set a local alarm for a clock time. Fires on this computer."""
    try:
        fires_at = _alarm_datetime(when, time, day)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return _create("alarm", fires_at, label, default_label="Alarm")


def list_alarms():
    """List pending local timers and alarms."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, kind, label, fires_at, status, created_at
            FROM alarms
            WHERE status = ?
            ORDER BY fires_at ASC, id ASC
            """,
            (PENDING,),
        ).fetchall()
    return {"ok": True, "alarms": [_format_row(row) for row in rows]}


def cancel_alarm(alarm_id=None, label=None):
    """Cancel a pending local timer or alarm by id or unique label."""
    parsed_id = _parse_id(alarm_id)
    has_label = isinstance(label, str) and bool(label.strip())
    if parsed_id is None and not has_label:
        return {"ok": False, "error": "An alarm_id or label is required."}

    try:
        if parsed_id is None:
            found = list_alarms()
            matches = [
                item
                for item in found["alarms"]
                if label.strip().lower() in item["label"].lower()
            ]
            if not matches:
                return {"ok": False, "error": "Could not find a matching timer or alarm."}
            if len(matches) > 1:
                return {
                    "ok": False,
                    "error": "Multiple timers or alarms matched. Use alarm_id.",
                    "alarms": matches,
                }
            parsed_id = matches[0]["id"]

        with _connect() as connection:
            existing = _get_by_id(connection, parsed_id)
            if existing is None:
                return {"ok": False, "error": f"Could not find timer or alarm {parsed_id}."}
            if existing["status"] != PENDING:
                return {
                    "ok": False,
                    "error": f"That {existing['kind']} is not pending.",
                    "alarm": _format_row(existing),
                }
            connection.execute(
                "UPDATE alarms SET status = ? WHERE id = ?",
                (CANCELLED, parsed_id),
            )
            existing = _get_by_id(connection, parsed_id)
        _wake_scheduler()
        return {"ok": True, "cancelled": _format_row(existing)}
    except Exception:
        return {"ok": False, "error": "Could not cancel that timer or alarm."}


def process_due(now=None):
    """Fire or mark missed any pending items that are due. Used by tests and the scheduler."""
    moment = now or local_now()
    fired = []
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, kind, label, fires_at, status, created_at
            FROM alarms
            WHERE status = ?
            ORDER BY fires_at ASC, id ASC
            """,
            (PENDING,),
        ).fetchall()
        for row in rows:
            due_at = datetime.fromisoformat(row["fires_at"])
            if due_at > moment:
                continue
            status = MISSED if moment - due_at > MISSED_AFTER else FIRED
            connection.execute(
                "UPDATE alarms SET status = ? WHERE id = ?",
                (status, row["id"]),
            )
            item = _format_row(_get_by_id(connection, row["id"]))
            fired.append(item)

    for item in fired:
        _emit(item)
    return fired


def fired_message(item):
    label = item.get("label") or item.get("kind", "alarm")
    kind = item.get("kind", "alarm")
    if item.get("status") == MISSED:
        return f'Missed {kind} "{label}" (was due {_display_time(item.get("fires_at"))}).'
    if kind == "timer":
        return f'Timer "{label}" is done.'
    return f'Alarm "{label}" is going off.'


def add_alarm_listener(callback):
    if callback not in _listeners:
        _listeners.append(callback)


def remove_alarm_listener(callback):
    if callback in _listeners:
        _listeners.remove(callback)


def start_scheduler():
    global _thread
    if os.environ.get("BCHUBOT_ALARMS_SCHEDULER") == "0":
        return
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop.clear()
        _wake.clear()
        _thread = threading.Thread(
            target=_loop,
            name="bchubot-alarms",
            daemon=True,
        )
        _thread.start()


def stop_scheduler():
    global _thread
    _stop.set()
    _wake.set()
    thread = _thread
    if thread is not None and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=1.5)
    _thread = None


def _create(kind, fires_at, label, default_label="Alarm"):
    if isinstance(label, str) and len(label.strip()) > MAX_LABEL_LENGTH:
        return {"ok": False, "error": "That label is too long."}
    cleaned = _normalize_label(label, default_label)
    if cleaned is None:
        return {"ok": False, "error": "A label is required."}
    if fires_at <= local_now():
        return {"ok": False, "error": "That alarm time is already past."}

    try:
        with _connect() as connection:
            pending = connection.execute(
                "SELECT COUNT(*) FROM alarms WHERE status = ?",
                (PENDING,),
            ).fetchone()[0]
            if pending >= MAX_PENDING:
                return {
                    "ok": False,
                    "error": f"There are already {MAX_PENDING} pending timers or alarms.",
                }
            created_at = local_now().isoformat()
            cursor = connection.execute(
                """
                INSERT INTO alarms (kind, label, fires_at, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (kind, cleaned, fires_at.isoformat(), PENDING, created_at),
            )
            row = _get_by_id(connection, cursor.lastrowid)
        _ensure_scheduler()
        _wake_scheduler()
        return {"ok": True, "alarm": _format_row(row)}
    except Exception:
        return {"ok": False, "error": f"Could not set that {kind}."}


def _alarm_datetime(when, time_value, day):
    has_when = isinstance(when, str) and bool(when.strip())
    has_time = isinstance(time_value, str) and bool(time_value.strip())
    if has_when:
        return parse_datetime(when)
    if not has_time:
        raise ValueError("An alarm needs a time, such as 18:30 or 6:30 PM.")

    clock = parse_clock_time(time_value)
    day_was_set = isinstance(day, str) and bool(day.strip())
    target_day = resolve_day(day if day_was_set else "today")
    fires_at = datetime.combine(target_day, clock, tzinfo=local_now().tzinfo)
    if fires_at <= local_now() and not day_was_set:
        fires_at += timedelta(days=1)
    return fires_at


def _loop():
    while not _stop.is_set():
        try:
            process_due()
        except Exception:
            pass
        wait_s = _seconds_until_next()
        if wait_s is None:
            timeout = MAX_WAIT_SECONDS
        else:
            timeout = max(0.05, min(wait_s, MAX_WAIT_SECONDS))
        _wake.wait(timeout=timeout)
        _wake.clear()


def _seconds_until_next():
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT fires_at FROM alarms
            WHERE status = ?
            ORDER BY fires_at ASC, id ASC
            LIMIT 1
            """,
            (PENDING,),
        ).fetchone()
    if row is None:
        return None
    due_at = datetime.fromisoformat(row["fires_at"])
    return (due_at - local_now()).total_seconds()


def _ensure_scheduler():
    if os.environ.get("BCHUBOT_ALARMS_SCHEDULER") == "0":
        return
    start_scheduler()


def _wake_scheduler():
    _wake.set()


def _emit(item):
    for callback in list(_listeners):
        try:
            callback(item)
        except Exception:
            pass
    _notify_os(item)


def _notify_os(item):
    if os.environ.get("BCHUBOT_ALARMS_NOTIFY") == "0":
        return
    if sys.platform != "darwin":
        return
    body = fired_message(item)
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                "on run argv",
                "-e",
                "display notification (item 1 of argv) with title (item 2 of argv)",
                "-e",
                "end run",
                body,
                "BchuBot",
            ],
            check=False,
            timeout=3,
            capture_output=True,
        )
        sound = Path("/System/Library/Sounds/Glass.aiff")
        if sound.exists():
            subprocess.run(
                ["afplay", str(sound)],
                check=False,
                timeout=5,
                capture_output=True,
            )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _get_by_id(connection, alarm_id):
    return connection.execute(
        """
        SELECT id, kind, label, fires_at, status, created_at
        FROM alarms
        WHERE id = ?
        """,
        (alarm_id,),
    ).fetchone()


def _format_row(row):
    return {
        "id": row["id"],
        "kind": row["kind"],
        "label": row["label"],
        "fires_at": row["fires_at"],
        "status": row["status"],
    }


def _display_time(value):
    if not value:
        return "the scheduled time"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%I:%M %p").lstrip("0")


def _normalize_label(label, default="Alarm"):
    if label in (None, ""):
        return default
    if not isinstance(label, str):
        return None
    cleaned = label.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_LABEL_LENGTH:
        return None
    return cleaned


def _as_nonneg_number(value):
    if value in (None, ""):
        return 0.0
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("not a number")
    if isinstance(value, str):
        value = float(value.strip())
    else:
        value = float(value)
    if value < 0 or value != value:
        raise ValueError("not a number")
    return value


def _parse_id(alarm_id):
    if isinstance(alarm_id, bool) or alarm_id in (None, ""):
        return None
    if isinstance(alarm_id, int) and alarm_id > 0:
        return alarm_id
    if isinstance(alarm_id, str) and alarm_id.strip().isdigit():
        parsed = int(alarm_id.strip())
        return parsed if parsed > 0 else None
    return None


ALARM_CAPABILITIES = {
    "set_timer": (
        "Sets a local countdown timer on this computer. "
        "It only fires while BchuBot is running (CLI or web server)."
    ),
    "set_alarm": (
        "Sets a local alarm for a clock time on this computer. "
        "It only fires while BchuBot is running (CLI or web server)."
    ),
    "list_alarms": "Lists pending local timers and alarms.",
    "cancel_alarm": (
        "Cancels a pending local timer or alarm by alarm_id or unique label."
    ),
}

ALARM_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": (
                "Set a local countdown timer that pings this computer. "
                "Use for 'in 10 minutes'. Does not use Google Calendar. "
                "Only fires while BchuBot is running."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Hours to wait. Optional.",
                    },
                    "minutes": {
                        "type": "number",
                        "description": "Minutes to wait. Optional.",
                    },
                    "seconds": {
                        "type": "number",
                        "description": "Seconds to wait. Optional.",
                    },
                    "label": {
                        "type": "string",
                        "description": "What the timer is for, such as 'tea'.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_alarm",
            "description": (
                "Set a local alarm that pings this computer at a clock time. "
                "Use 18:30 or 6:30 PM. If that time already passed today, "
                "it uses tomorrow unless day is set. Does not use Google Calendar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "What the alarm is for, such as 'dinner'.",
                    },
                    "time": {
                        "type": "string",
                        "description": "Clock time such as 18:30 or 6:30 PM.",
                    },
                    "day": {
                        "type": "string",
                        "description": "today, tomorrow, or YYYY-MM-DD.",
                    },
                    "when": {
                        "type": "string",
                        "description": "Optional ISO datetime, such as 2026-09-16T18:30.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_alarms",
            "description": "List pending local timers and alarms.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_alarm",
            "description": (
                "Cancel a pending local timer or alarm. "
                "Prefer alarm_id from list_alarms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "alarm_id": {
                        "type": "integer",
                        "description": "Id from list_alarms or set_timer.",
                    },
                    "label": {
                        "type": "string",
                        "description": "Label to cancel if the id is unknown.",
                    },
                },
                "required": [],
            },
        },
    },
]
