"""
A small router that maps HTTP methods and paths to handler functions.

Routes are registered with patterns such as "/projects/{id}". Placeholders in
braces are captured into request.path_params.
"""

import logging
from typing import Any, Callable

from app.request import Request, parse_event
from app.responses import ApiError, error_response, json_response
from app.store import store

logger = logging.getLogger(__name__)

Handler = Callable[[Request], dict[str, Any]]


# [ROUTER HERE]
# How: Routes are stored as (method, path segments, handler). Each request's
#      path is split into segments and compared against every route; segments
#      in braces like {id} match anything and are captured as path parameters.
# Why: All entities live in one Lambda (so in-memory data can be shared), which
#      means one function has to serve many URLs. A small hand-written router
#      avoids pulling in a web framework that Lambda doesn't need.
class Router:
    """Collects routes and dispatches Lambda events to them."""

    def __init__(self) -> None:
        """Create an empty router."""
        self._routes: list[tuple[str, list[str], Handler]] = []

    def add(self, method: str, pattern: str, handler: Handler) -> None:
        """
        Register a handler for a method and path pattern.

        Args:
            method: HTTP method, e.g. "GET".
            pattern: Path pattern, e.g. "/projects/{id}".
            handler: Function that takes a Request and returns a response.
        """
        segments = [part for part in pattern.strip("/").split("/") if part]
        self._routes.append((method.upper(), segments, handler))

    def routes(self) -> list[str]:
        """
        List registered routes for discovery and debugging.

        Returns:
            Strings like "GET /projects/{id}".
        """
        return [f"{method} /{'/'.join(segments)}" for method, segments, _ in self._routes]

    @staticmethod
    def _match(pattern: list[str], parts: list[str]) -> dict[str, str] | None:
        """
        Check whether path parts match a pattern.

        Args:
            pattern: Pattern segments, e.g. ["projects", "{id}"].
            parts: Path segments, e.g. ["projects", "12"].

        Returns:
            Captured path parameters, or None if there is no match.
        """
        if len(pattern) != len(parts):
            return None
        params: dict[str, str] = {}
        for expected, actual in zip(pattern, parts):
            if expected.startswith("{") and expected.endswith("}"):
                params[expected[1:-1]] = actual
            elif expected != actual:
                return None
        return params

    def dispatch(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Route a Lambda event to its handler and return the response.

        Args:
            event: The raw Lambda event.

        Returns:
            A Lambda proxy response. Unknown paths return 404, known paths
            with the wrong method return 405, and unexpected errors return 500.
        """
        try:
            request = parse_event(event)
            logger.info("%s %s", request.method, request.path)
            parts = [part for part in request.path.strip("/").split("/") if part]

            path_exists = False
            for method, pattern, handler in self._routes:
                params = self._match(pattern, parts)
                if params is None:
                    continue
                path_exists = True
                if method == request.method:
                    request.path_params = params
                    # [REQUEST TRANSACTION HERE]
                    # How: The whole route runs inside one storage transaction.
                    # Why: If any step raises an error (including an ApiError
                    #      after some rows were written), every change from
                    #      this request is undone, in memory and in PostgreSQL.
                    with store.transaction():
                        return handler(request)

            # [404 VS 405 HERE]
            # How: If the path matched some route but not with this method,
            #      return 405; if nothing matched the path at all, return 404.
            # Why: The difference tells the frontend developer whether the URL
            #      is wrong or just the HTTP method, which speeds up debugging.
            if path_exists:
                raise ApiError(405, "method_not_allowed",
                               f"Method {request.method} is not allowed on {request.path}.")
            raise ApiError(404, "not_found", f"No route matches {request.path}.")
        except ApiError as err:
            return error_response(err)
        # [CATCH-ALL ERROR HERE]
        # How: Any unexpected exception is logged with its full traceback and
        #      returned as a generic 500.
        # Why: The traceback goes to CloudWatch for debugging, but internal
        #      details never leak to the client, which is a security concern.
        except Exception:  # pylint: disable=broad-except
            logger.exception("Unhandled error")
            return json_response(500, {"error": {"status": 500, "code": "internal_error",
                                                 "message": "An unexpected error occurred."}})


router = Router()
