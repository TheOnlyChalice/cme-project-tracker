"""
Lambda entry point for the CME project tracking API (v1).

Terraform deploys this folder as one Lambda function, and the dev server calls
the same handler locally. Every request is passed to the router, which sends
it to the matching route handler.
"""

import logging
from typing import Any

from app.router import router
from app.routes import register_all_routes
from app.seed import seed_data

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# [ROUTE REGISTRATION HERE]
# How: Every domain module registers its routes once, when Lambda loads this file.
# Why: Lambda reuses the loaded module across requests in a warm container, so
#      routes are built once instead of on every request.
register_all_routes(router)
seed_data()


def handler(event: dict[str, Any] | None = None, context: Any = None) -> dict[str, Any]:
    """
    Handle an incoming Lambda Function URL request.

    Args:
        event: The Lambda Function URL event (payload format 2.0).
        context: The Lambda runtime context (unused).

    Returns:
        A Lambda proxy response with statusCode, headers, and a JSON body.
    """
    return router.dispatch(event or {})


if __name__ == "__main__":
    print(handler({"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}))
