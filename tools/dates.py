from datetime import date, datetime, time, timedelta


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
