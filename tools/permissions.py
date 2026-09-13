AUTOMATIC = "AUTOMATIC"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
DISABLED = "DISABLED"

TOOL_PERMISSIONS = {
    "get_time": AUTOMATIC,
    "get_date": AUTOMATIC,
    "calculator": AUTOMATIC,
    "get_weather": AUTOMATIC,
    "read_calendar": AUTOMATIC,
    "read_tasks": AUTOMATIC,
    "read_task_lists": AUTOMATIC,
    "read_today": AUTOMATIC,
    "create_calendar_event": CONFIRMATION_REQUIRED,
    "create_reminder": CONFIRMATION_REQUIRED,
    "delete_calendar_event": CONFIRMATION_REQUIRED,
    "create_task": CONFIRMATION_REQUIRED,
    "create_task_list": CONFIRMATION_REQUIRED,
}


def permission_for(tool_name):
    return TOOL_PERMISSIONS.get(tool_name, CONFIRMATION_REQUIRED)


def request_confirmation(tool_name, arguments):
    args = ", ".join(
        f"{key}={value!r}" for key, value in (arguments or {}).items()
    )
    print(f"\nBchuBot wants to run {tool_name}({args})")
    answer = input("Allow this action? [y/N] ").strip().lower()
    return answer in {"y", "yes"}
