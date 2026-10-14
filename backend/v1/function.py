"""
Lambda entry point for the CME project tracking API (v1).

Terraform deploys this folder as one Lambda function, and the dev server calls
the same handler locally. Every request is passed to the router, which sends
it to the matching route handler.
"""

import logging
from typing import Any

from app.responses import json_response
from app.router import router
from app.routes import register_all_routes
from app.seed import seed_data
from app.store import store

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# [ACME: ROUTE REGISTRATION HERE]
# How: Every domain module registers its routes once, when Lambda loads this file.
# Why: Lambda reuses the loaded module across requests in a warm container, so
#      routes are built once instead of on every request.
register_all_routes(router)

_ready = False


# [ACME: STARTUP BOOTSTRAP HERE]
# How: The first request a Lambda copy handles creates any missing tables and
#      adds the starter data if the database is empty. If the database can't be
#      reached, the request gets a 503 and the next request tries again.
# Why: Doing this lazily (instead of when the file is imported) means a
#      database hiccup during a cold start returns a clear error rather than
#      crashing the whole Lambda copy, and it recovers on its own.
def _bootstrap() -> dict[str, Any] | None:
    """
    Prepare storage once per Lambda copy.

    Returns:
        None when ready, or a 503 response if storage isn't reachable.
    """
    global _ready  # pylint: disable=global-statement
    if _ready:
        return None
    try:
        store.ensure_schema()
        seed_data()
        _ready = True
        return None
    except Exception:  # pylint: disable=broad-except
        logger.exception("Storage bootstrap failed")
        return json_response(503, {"error": {"status": 503, "code": "storage_unavailable",
                                             "message": "The database is unavailable. Try again shortly."}})


def handler(event: dict[str, Any] | None = None, context: Any = None) -> dict[str, Any]:
    """
    Handle an incoming Lambda Function URL request.

    Args:
        event: The Lambda Function URL event (payload format 2.0).
        context: The Lambda runtime context (unused).

    Returns:
        A Lambda proxy response with statusCode, headers, and a JSON body.
    """
    not_ready = _bootstrap()
    if not_ready:
        return not_ready
    return router.dispatch(event or {})


if __name__ == "__main__":
    print(handler({"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}))
