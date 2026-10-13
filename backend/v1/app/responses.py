"""
Helpers for building consistent JSON responses.

Every response, success or error, goes through these functions so the API
always returns the same structure and headers.
"""

import json
from decimal import Decimal
from typing import Any

JSON_HEADERS = {"Content-Type": "application/json"}


# [API ERROR HERE]
# How: Route code raises ApiError(status, code, message) anywhere it detects a
#      problem; the router catches it and turns it into a JSON error response.
# Why: Handlers stay short because they never build error responses themselves,
#      and every error the frontend receives has the same shape.
class ApiError(Exception):
    """An error that should be returned to the client as a JSON response."""

    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        """
        Create an API error.

        Args:
            status: HTTP status code to return.
            code: Short machine-readable error code, e.g. "not_found".
            message: Human-readable explanation.
            details: Optional extra information, such as per-field errors.
        """
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def json_response(status: int, body: Any = None) -> dict[str, Any]:
    """
    Build a Lambda response with a JSON body.

    Args:
        status: HTTP status code.
        body: Data to serialize. Omitted entirely for 204 responses.

    Returns:
        A Lambda proxy response dictionary.
    """
    response: dict[str, Any] = {"statusCode": status, "headers": dict(JSON_HEADERS)}
    if status != 204:
        response["body"] = json.dumps(body, default=_json_default)
    return response


# [JSON SERIALIZATION HERE]
# How: Decimals (salary, budget) become JSON numbers; anything else json can't
#      handle (dates, UUIDs) becomes a string.
# Why: Money is stored as Decimal to avoid floating-point rounding errors, but
#      the frontend needs plain numbers. Converting here means no route has to.
def _json_default(value: Any) -> Any:
    """
    Convert values the json module can't serialize.

    Args:
        value: The value json.dumps couldn't handle.

    Returns:
        A float for Decimals, otherwise the value's string form.
    """
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


# [ERROR FORMAT HERE]
# How: Every error becomes {"error": {"code": ..., "message": ..., "details": ...}}.
# Why: One predictable shape lets the frontend show errors with a single helper
#      instead of handling each endpoint differently.
def error_response(error: ApiError) -> dict[str, Any]:
    """
    Convert an ApiError into a consistent JSON error response.

    Args:
        error: The error to convert.

    Returns:
        A Lambda proxy response with an "error" object in the body.
    """
    payload: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        payload["details"] = error.details
    return json_response(error.status, {"error": payload})
