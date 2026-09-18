import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tools.dates import local_now


CONFIG_PATH = Path.home() / ".bchubot" / "canvas.json"
REQUEST_TIMEOUT_SECONDS = 10
MAX_TOKEN_LENGTH = 512
MAX_DAYS = 60
DEFAULT_DAYS = 14
OVERDUE_LOOKBACK_DAYS = 30
MAX_PAGES = 5
PER_PAGE = 50
MAX_ASSIGNMENTS = 50
HOMEWORK_TYPES = {"assignment", "quiz", "discussion_topic"}


class CanvasConfigError(Exception):
    pass


class CanvasAuthError(Exception):
    pass


def read_canvas_homework(days=DEFAULT_DAYS, course=None):
    """Read upcoming and overdue Canvas homework for the signed-in student."""
    try:
        window_days = _parse_days(days)
        course_filter = _optional_text(course)
        config = load_config()
        now = local_now()
        start_day = now.date()
        end_day = start_day + timedelta(days=window_days)
        lookback = start_day - timedelta(days=OVERDUE_LOOKBACK_DAYS)

        items = _planner_items(
            config,
            start=lookback.isoformat(),
            end=(end_day + timedelta(days=1)).isoformat(),
        )
        assignments = []
        for item in items:
            homework = _format_homework(item, now)
            if homework is None:
                continue
            if course_filter and course_filter not in homework["course"].lower():
                continue
            due_at = homework.get("due_at")
            if homework["overdue"]:
                assignments.append(homework)
            elif due_at and start_day.isoformat() <= due_at[:10] <= end_day.isoformat():
                assignments.append(homework)

        assignments.sort(key=_sort_key)
        return {
            "ok": True,
            "start": start_day.isoformat(),
            "end": end_day.isoformat(),
            "count": len(assignments),
            "assignments": assignments[:MAX_ASSIGNMENTS],
        }
    except CanvasConfigError as exc:
        return {"ok": False, "error": str(exc)}
    except CanvasAuthError:
        return {
            "ok": False,
            "error": (
                "Canvas rejected the access token. Create a new token in "
                "Canvas Account Settings and update ~/.bchubot/canvas.json."
            ),
        }
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not read Canvas homework."}


def load_config(path=None):
    config_path = Path(path) if path else CONFIG_PATH
    if not config_path.exists():
        raise CanvasConfigError(
            "Canvas is not set up. Save your Canvas site URL and access token "
            f"to {CONFIG_PATH}."
        )

    try:
        raw = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        raise CanvasConfigError(
            f"{config_path} is not valid JSON."
        ) from exc

    if not isinstance(raw, dict):
        raise CanvasConfigError(f"{config_path} must contain a JSON object.")

    base_url = _normalize_base_url(raw.get("base_url"))
    token = raw.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise CanvasConfigError("canvas.json must include an access_token.")
    token = token.strip()
    if len(token) > MAX_TOKEN_LENGTH:
        raise CanvasConfigError("The Canvas access token is too long.")

    return {"base_url": base_url, "access_token": token}


def _normalize_base_url(value):
    if not isinstance(value, str) or not value.strip():
        raise CanvasConfigError("canvas.json must include a base_url.")

    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme != "https":
        raise CanvasConfigError("Canvas base_url must use https.")
    if not parsed.hostname:
        raise CanvasConfigError("Canvas base_url must include a hostname.")
    if parsed.username or parsed.password:
        raise CanvasConfigError("Do not put the Canvas token in the URL.")
    if parsed.query or parsed.fragment:
        raise CanvasConfigError("Canvas base_url should not include a query string.")

    path = parsed.path.rstrip("/")
    if path.endswith("/api/v1"):
        path = path[: -len("/api/v1")]
    netloc = parsed.hostname.lower()
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return f"https://{netloc}{path}"


def _parse_days(value):
    if value in (None, ""):
        return DEFAULT_DAYS
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("days must be a whole number.") from exc
    if days < 1 or days > MAX_DAYS:
        raise ValueError(f"days must be between 1 and {MAX_DAYS}.")
    return days


def _optional_text(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("course must be text.")
    text = value.strip().lower()
    return text or None


def _planner_items(config, start, end):
    url = _api_url(config, "/planner/items")
    params = {
        "start_date": start,
        "end_date": end,
        "per_page": str(PER_PAGE),
    }
    items = []
    for _ in range(MAX_PAGES):
        payload, next_url = _request(config, url, params)
        if not isinstance(payload, list):
            raise CanvasConfigError("Canvas returned an unexpected planner response.")
        items.extend(payload)
        if not next_url:
            break
        url = next_url
        params = None
    return items


def _api_url(config, path):
    return config["base_url"].rstrip("/") + "/api/v1" + path


def _request(config, url, params=None):
    _assert_canvas_url(config, url)
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
        _assert_canvas_url(config, url)

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {config['access_token']}",
            "Accept": "application/json",
            "User-Agent": "BchuBot/0.1 (personal assistant)",
        },
    )
    opener = urllib.request.build_opener(_SameHostRedirectHandler(config))
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read().decode()
            next_url = _next_link(response.headers)
            if next_url:
                _assert_canvas_url(config, next_url)
            return json.loads(body), next_url
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise CanvasAuthError("Canvas rejected the access token.") from exc
        raise


def _assert_canvas_url(config, url):
    parsed = urllib.parse.urlparse(url)
    allowed = urllib.parse.urlparse(config["base_url"])
    if parsed.scheme != "https" or parsed.hostname != allowed.hostname:
        raise CanvasConfigError("Refusing to call a non-Canvas URL.")
    if parsed.port != allowed.port:
        raise CanvasConfigError("Refusing to call a non-Canvas URL.")
    api_path = urllib.parse.urlparse(_api_url(config, "")).path
    if not (parsed.path == api_path or parsed.path.startswith(api_path + "/")):
        raise CanvasConfigError("Refusing to call a non-Canvas URL.")


def _next_link(headers):
    link = headers.get("Link") or headers.get("link")
    if not link:
        return None
    for part in link.split(","):
        if 'rel="next"' not in part and "rel=next" not in part:
            continue
        start = part.find("<")
        end = part.find(">")
        if start != -1 and end != -1:
            return part[start + 1 : end].strip()
    return None


def _format_homework(item, now):
    if not isinstance(item, dict):
        return None
    plannable_type = str(item.get("plannable_type") or "").lower()
    if plannable_type not in HOMEWORK_TYPES:
        return None

    submissions = item.get("submissions")
    if isinstance(submissions, dict) and (
        submissions.get("submitted") or submissions.get("excused")
    ):
        return None

    plannable = item.get("plannable")
    if not isinstance(plannable, dict):
        return None
    title = (plannable.get("title") or "").strip()
    if not title:
        return None

    due_raw = plannable.get("due_at") or item.get("plannable_date")
    due_at = _as_datetime(due_raw)
    overdue = bool(due_at and due_at < now)
    course = (item.get("context_name") or "").strip() or "Canvas"
    homework = {
        "title": title,
        "course": course,
        "type": plannable_type,
        "due_at": due_at.isoformat() if due_at else None,
        "points": plannable.get("points_possible"),
        "submitted": False,
        "overdue": overdue,
        "url": item.get("html_url") or plannable.get("html_url"),
    }
    return homework


def _as_datetime(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_now().tzinfo)
    return parsed


def _sort_key(item):
    due_at = item.get("due_at") or "9999-12-31"
    overdue_rank = 0 if item.get("overdue") else 1
    return (overdue_rank, due_at, item.get("course") or "", item.get("title") or "")


class _SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, config):
        super().__init__()
        self._config = config

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            _assert_canvas_url(self._config, newurl)
        except CanvasConfigError:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


CANVAS_CAPABILITIES = {
    "read_canvas_homework": (
        "Reads upcoming and overdue homework from the user's Canvas LMS "
        "account. Requires ~/.bchubot/canvas.json. This is read-only."
    ),
}

CANVAS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_canvas_homework",
            "description": (
                "Read upcoming and overdue homework from Canvas LMS. "
                "Use this when the user asks about homework, assignments, "
                "quizzes, or what is due for school."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": (
                            "How many days ahead to look, from 1 to 60. "
                            "Defaults to 14. Overdue unsubmitted work is "
                            "always included."
                        ),
                    },
                    "course": {
                        "type": "string",
                        "description": (
                            "Optional course name filter, such as 'CS 3200'."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]
