from tools.dates import resolve_day
from tools.google_auth import GoogleAuthError, tasks_service


DEFAULT_TASK_LIST = "@default"


def read_task_lists():
    """List the user's Google Tasks lists."""
    try:
        result = tasks_service().tasklists().list(maxResults=50).execute()
        lists = [
            {"id": item.get("id"), "title": item.get("title")}
            for item in result.get("items", [])
        ]
        return {"ok": True, "lists": lists}
    except GoogleAuthError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not read task lists."}


def read_tasks(list_name=None, due=None):
    """Read tasks from Google Tasks, optionally filtered by due date."""
    try:
        service = tasks_service()
        list_id = _resolve_task_list_id(service, list_name)
        if list_id is None:
            return {"ok": False, "error": f"Could not find task list: {list_name}"}

        due_day = resolve_day(due) if due not in (None, "") else None
        result = (
            service.tasks()
            .list(tasklist=list_id, showCompleted=False, maxResults=50)
            .execute()
        )
        tasks = [_format_task(item) for item in result.get("items", [])]
        if due_day is not None:
            tasks = [
                task
                for task in tasks
                if task.get("due") and task["due"][:10] == due_day.isoformat()
            ]
        return {
            "ok": True,
            "list": list_name or "default",
            "due": due_day.isoformat() if due_day else None,
            "tasks": tasks,
        }
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not read tasks."}


def create_task(title, due=None, list_name=None, notes=None):
    """Create a task in Google Tasks."""
    if not isinstance(title, str) or not title.strip():
        return {"ok": False, "error": "A task title is required."}

    try:
        service = tasks_service()
        list_id = _resolve_task_list_id(service, list_name)
        if list_id is None:
            return {"ok": False, "error": f"Could not find task list: {list_name}"}

        body = {"title": title.strip()}
        if due not in (None, ""):
            body["due"] = f"{resolve_day(due).isoformat()}T00:00:00.000Z"
        if isinstance(notes, str) and notes.strip():
            body["notes"] = notes.strip()

        created = service.tasks().insert(tasklist=list_id, body=body).execute()
        return {"ok": True, "task": _format_task(created)}
    except (GoogleAuthError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not create the task."}


def create_task_list(title):
    """Create a Google Tasks list."""
    if not isinstance(title, str) or not title.strip():
        return {"ok": False, "error": "A task list title is required."}

    try:
        created = (
            tasks_service()
            .tasklists()
            .insert(body={"title": title.strip()})
            .execute()
        )
        return {
            "ok": True,
            "list": {"id": created.get("id"), "title": created.get("title")},
        }
    except GoogleAuthError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception:
        return {"ok": False, "error": "Could not create the task list."}


def _resolve_task_list_id(service, list_name):
    if not list_name or not str(list_name).strip():
        return DEFAULT_TASK_LIST

    wanted = str(list_name).strip().lower()
    result = service.tasklists().list(maxResults=50).execute()
    for item in result.get("items", []):
        if (item.get("title") or "").lower() == wanted:
            return item.get("id")
    return None


def _format_task(task):
    return {
        "id": task.get("id"),
        "title": task.get("title") or "(No title)",
        "due": task.get("due"),
        "status": task.get("status"),
        "notes": task.get("notes"),
    }


TASKS_CAPABILITIES = {
    "read_task_lists": "Reads the user's Google Tasks lists.",
    "read_tasks": (
        "Reads incomplete Google Tasks. Can filter by list name and due date."
    ),
    "create_task": (
        "Creates a Google Task, optionally with a due date and list. "
        "This changes the user's real tasks and requires confirmation."
    ),
    "create_task_list": (
        "Creates a new Google Tasks list. "
        "This changes the user's real tasks and requires confirmation."
    ),
}

TASKS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_task_lists",
            "description": "List the user's Google Tasks lists.",
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
            "name": "read_tasks",
            "description": (
                "Read incomplete Google Tasks. Optionally filter by list "
                "name and due date (today, tomorrow, or YYYY-MM-DD)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "list_name": {
                        "type": "string",
                        "description": "Task list name. Defaults to the primary list.",
                    },
                    "due": {
                        "type": "string",
                        "description": "Only tasks due on this date.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a Google Task, optionally on a list and due date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title.",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date: today, tomorrow, or YYYY-MM-DD.",
                    },
                    "list_name": {
                        "type": "string",
                        "description": "Task list name. Defaults to the primary list.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional task notes.",
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task_list",
            "description": "Create a new Google Tasks list / todo list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Name of the new list.",
                    }
                },
                "required": ["title"],
            },
        },
    },
]
