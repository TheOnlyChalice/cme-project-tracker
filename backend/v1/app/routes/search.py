"""HTTP route for quick search."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services.search import quick_search


def register(router: Router) -> None:
    """
    Register the quick search route.

    Args:
        router: The router to register routes on.
    """

    def search(request: Request) -> dict[str, Any]:
        """Search projects, milestones, and people (?q=)."""
        actor = current_user(request)
        return json_response(200, quick_search(actor, request.query.get("q")))

    router.add("GET", "/search", search)
