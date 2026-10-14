"""
Parse Lambda Function URL events into a simple Request object.

The same code runs locally (dev server or the workshop proxy, which strips
the "/api/v1" prefix) and in the cloud (CloudFront, which keeps it), so the
path is normalized here before routing.
"""

import base64
import json
from dataclasses import dataclass, field
from typing import Any

from app.responses import ApiError

SERVICE_PREFIX = "/api/v1"


@dataclass
class Request:
    """A parsed HTTP request."""

    method: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    raw_body: str = ""
    path_params: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        """
        Parse the request body as JSON.

        Returns:
            The parsed body, or an empty dict when the body is empty.

        Raises:
            ApiError: 400 if the body is not valid JSON.
        """
        if not self.raw_body:
            return {}
        try:
            return json.loads(self.raw_body)
        except json.JSONDecodeError as exc:
            raise ApiError(400, "invalid_json", "Request body must be valid JSON.") from exc


# [ACME: PATH NORMALIZATION HERE]
# How: Strip a leading "/api/v1" if present, then remove extra slashes, so
#      "/api/v1/projects/", "/projects", and "projects" all become "/projects".
# Why: CloudFront forwards the full path in the cloud, while the local proxy
#      strips the prefix. Without this, routes would work locally and 404 once
#      deployed (or the reverse).
def normalize_path(raw_path: str) -> str:
    """
    Strip the service prefix and trailing slashes from a request path.

    Args:
        raw_path: The path as received, e.g. "/api/v1/projects/" or "/projects".

    Returns:
        A clean path such as "/projects", or "/" for the root.
    """
    path = raw_path or "/"
    if path == SERVICE_PREFIX or path.startswith(SERVICE_PREFIX + "/"):
        path = path[len(SERVICE_PREFIX):]
    return "/" + path.strip("/")


# [ACME: EVENT PARSING HERE]
# How: Read the method, path, query, headers, and body out of the Lambda
#      Function URL event (payload format 2.0), decoding base64 bodies.
# Why: Lambda has no web framework, so this replaces what Flask or FastAPI
#      would normally do. Header names are lowercased because HTTP headers are
#      case-insensitive and different callers send different casing.
def parse_event(event: dict[str, Any]) -> Request:
    """
    Build a Request from a Lambda Function URL event.

    Args:
        event: The raw Lambda event.

    Returns:
        The parsed Request.
    """
    http = event.get("requestContext", {}).get("http", {})
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()
    raw_path = event.get("rawPath") or http.get("path") or event.get("path") or "/"

    body = event.get("body") or ""
    if body and event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    headers = {key.lower(): value for key, value in (event.get("headers") or {}).items()}

    return Request(
        method=method,
        path=normalize_path(raw_path),
        query=dict(event.get("queryStringParameters") or {}),
        headers=headers,
        raw_body=body,
    )
