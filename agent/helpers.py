import functools
from typing import Any, Dict, Optional


def log_method_call(func):
    """
    Decorator for class methods to log their execution using self.logger.debug.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Log the method name
        if hasattr(self, "logger"):
            self.logger.debug(f"Running {func.__name__}")
        return func(self, *args, **kwargs)
    return wrapper


def error(
        message: str,
    code: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Name:
        error

    Purpose:
        Create a standardized error response for all tools.

    Inputs:
        message (str): Human-readable error message.
        code (str): Stable machine-readable error code.
        details (dict | None): Optional structured metadata.

    Output Schema:
        {
            "error": True,
            "message": str,
            "code": str,
            "details": dict
        }

    Error Handling:
        This method never raises exceptions.

    Fallback Behavior:
        Missing details default to an empty dict.
    """
    return {
        "error": True,
        "message": message,
        "code": code,
        "details": details or {}
    }


def is_error(result: Any) -> bool:
    """
    Name:
        _is_error

    Purpose:
        Determine whether a tool result represents a standardized error.

    Inputs:
        result (Any): Tool return value.

    Output Schema:
        bool

    Error Handling:
        Safe type checks only.

    Fallback Behavior:
        Returns False for non-dict or malformed inputs.
    """
    return isinstance(result, dict) and result.get("error") is True


def broken_rule_in_plan(plan):
    return "broken_rule" in plan["plan"][0]["tool"]
