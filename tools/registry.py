from tools.basic import get_time, get_date, calculator
from tools.weather import get_weather


TOOL_REGISTRY = {
    "get_time": get_time,
    "get_date": get_date,
    "calculator": calculator,
    "get_weather": get_weather,
}


TOOL_CAPABILITIES = {
    "get_time": "Reads the current local time from this computer's clock.",
    "get_date": "Reads the current local date from this computer's clock.",
    "calculator": (
        "Evaluates basic arithmetic locally. It does not execute code "
        "or use an external service."
    ),
    "get_weather": (
        "Looks up current weather from Open-Meteo (open-meteo.com). "
        "Requires a place name."
    ),
}


def describe_capabilities():
    lines = ["You have these tools, and only these tools:"]
    for name, description in TOOL_CAPABILITIES.items():
        lines.append(f"- {name}: {description}")
    lines.append(
        "When asked how you work or where information comes from, "
        "answer from this list. Do not invent other tools or data sources."
    )
    return "\n".join(lines)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current local time.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": (
                "Get the current local date, including the weekday "
                "and ISO date."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a basic arithmetic expression using numbers and "
                "+, -, *, /, //, %, **, and parentheses. Does not execute code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "The arithmetic expression to calculate, "
                            "such as '17 * 24' or '(3 + 5) / 2'."
                        )
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get the current weather for a named city or place "
                "from Open-Meteo. Use a location such as 'Boston' "
                "or 'Paris, France'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or place name to look up."
                    }
                },
                "required": ["location"]
            }
        }
    }
]