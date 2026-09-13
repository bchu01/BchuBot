import ast
import math
import operator
from datetime import datetime


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_MAX_ABS_VALUE = 1e15
_MAX_EXPONENT = 32
_MAX_INT_BITS = 256


def get_time():
    """Get the current local time."""
    current = datetime.now().astimezone()
    return current.strftime("%I:%M %p")


def get_date():
    """Get the current local date."""
    current = datetime.now().astimezone()
    display = (
        f"{current.strftime('%A')}, {current.strftime('%B')} "
        f"{current.day}, {current.year}"
    )
    return f"{display} ({current.strftime('%Y-%m-%d')})"


def calculator(expression):
    """Evaluate a basic arithmetic expression without executing code."""
    if not isinstance(expression, str) or not expression.strip():
        return "Unable to calculate that expression."

    try:
        tree = ast.parse(expression, mode="eval")
        return _format_number(_eval_node(tree))
    except Exception:
        return "Unable to calculate that expression."


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        return _as_number(node.value)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _check_result(_UNARY_OPERATORS[type(node.op)](_eval_node(node.operand)))

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("Exponent too large")

        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ValueError("Division by zero")

        return _check_result(_BINARY_OPERATORS[type(node.op)](left, right))

    raise ValueError("Unsupported expression")


def _as_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Unsupported value")
    return _check_result(value)


def _check_result(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid result")

    if isinstance(value, int) and value.bit_length() > _MAX_INT_BITS:
        raise ValueError("Result too large")

    if isinstance(value, float) and (
        not math.isfinite(value) or abs(value) > _MAX_ABS_VALUE
    ):
        raise ValueError("Result too large")

    return value


def _format_number(value):
    if isinstance(value, float) and value.is_integer() and abs(value) < _MAX_ABS_VALUE:
        return str(int(value))
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)
