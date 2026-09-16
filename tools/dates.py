import re
from datetime import date, datetime, time, timedelta

CLOCK_RE = re.compile(
    r"^(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?$",
    re.I,
)


def local_now():
    return datetime.now().astimezone()


def resolve_day(value, default="today"):
    if value is None or (isinstance(value, str) and not value.strip()):
        text = default
    elif isinstance(value, str):
        text = value.strip().lower()
    else:
        raise ValueError("Dates must be 'today', 'tomorrow', or YYYY-MM-DD.")

    today = local_now().date()
    if text == "today":
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("Dates must be 'today', 'tomorrow', or YYYY-MM-DD.") from exc


def day_bounds(day):
    start = datetime.combine(day, time.min, tzinfo=local_now().tzinfo)
    return start, start + timedelta(days=1)


def parse_datetime(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A date/time is required.")

    text = value.strip()
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            "Date/time must be ISO format, such as 2026-09-14T09:00."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_now().tzinfo)
    return parsed


def parse_clock_time(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A time is required, such as 18:30 or 6:30 PM.")

    match = CLOCK_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("Time must look like 18:30 or 6:30 PM.")

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    second = int(match.group(3) or 0)
    meridiem = match.group(4)

    if minute > 59 or second > 59:
        raise ValueError("Time must look like 18:30 or 6:30 PM.")

    if meridiem:
        suffix = meridiem.lower().replace(".", "")
        if hour < 1 or hour > 12:
            raise ValueError("Time must look like 18:30 or 6:30 PM.")
        if suffix.startswith("p") and hour != 12:
            hour += 12
        if suffix.startswith("a") and hour == 12:
            hour = 0
    elif hour > 23:
        raise ValueError("Time must look like 18:30 or 6:30 PM.")

    return time(hour, minute, second)
