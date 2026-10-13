"""Health check and API discovery routes."""

from datetime import datetime, timezone
from typing import Any

from app.request import Request
from app.responses import json_response
from app.router import Router
from app.store import store

API_VERSION = "1.1.0"


def register(router: Router) -> None:
    """
    Register health and discovery routes.

    Args:
        router: The router to register routes on.
    """

    # [HEALTH CHECK HERE]
    # How: GET /health returns status, version, server time, which storage
    #      backend is in use, and whether the database answers (503 if not).
    # Why: Gives a fast way to confirm the API and its database are reachable,
    #      locally and after deployment, without needing any login.
    def health(_request: Request) -> dict[str, Any]:
        """Report that the service and its storage are running."""
        database_ok = store.ping()
        return json_response(200 if database_ok else 503, {
            "status": "ok" if database_ok else "degraded",
            "storage": store.backend_name,
            "database": "reachable" if database_ok else "unreachable",
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
