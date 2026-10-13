"""Health check and API discovery routes."""

from datetime import datetime, timezone
from typing import Any

from app.request import Request
from app.responses import json_response
from app.router import Router

API_VERSION = "1.0.0"


def register(router: Router) -> None:
    """
    Register health and discovery routes.

    Args:
        router: The router to register routes on.
    """

    # [HEALTH CHECK HERE]
    # How: GET /health returns status, service name, version, and server time.
    # Why: Gives a fast way to confirm the API is reachable, locally and after
    #      deployment, without depending on any data or login.
    def health(_request: Request) -> dict[str, Any]:
        """Report that the service is running."""
        return json_response(200, {
            "status": "ok",
            "service": "cme-project-tracker",
            "version": API_VERSION,
            "time": datetime.now(timezone.utc).isoformat(),
        })

    # [ROUTE DISCOVERY HERE]
    # How: GET / lists every registered route.
    # Why: Lets you see the whole API at a glance while developing and testing.
    def index(_request: Request) -> dict[str, Any]:
        """List every available route."""
        return json_response(200, {"service": "cme-project-tracker",
                                   "version": API_VERSION,
                                   "routes": router.routes()})

    router.add("GET", "/", index)
    router.add("GET", "/health", health)
