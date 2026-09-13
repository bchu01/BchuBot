from datetime import datetime


def get_time():
    """Get the current local time."""
    return datetime.now().strftime("%I:%M %p")


def calculator(expression):
    """Evaluate a basic mathematical expression."""
    try:
        return str(eval(expression))
    except Exception:
        return "Unable to calculate that expression."