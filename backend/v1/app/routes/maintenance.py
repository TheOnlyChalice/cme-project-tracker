"""HTTP route for running maintenance on demand (admins only)."""

from typing import Any

from app.auth import current_user
from app.permissions import ADMIN, require_role
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import maintenance


def register(router: Router) -> None:
    """
    Register maintenance routes.

    Args:
        router: The router to register routes on.
    """

    # [RUN MAINTENANCE NOW HERE]
    # How: POST /admin/maintenance runs the inactivity archive immediately and
    #      lists what it archived. The admin is recorded as the actor.
    # Why: Lets admins (and demos) apply the two-week rule right away instead
    #      of waiting for the hourly automatic run.
    def run(request: Request) -> dict[str, Any]:
        """Archive inactive projects now."""
        actor = current_user(request)
        require_role(actor, ADMIN)
        archived = maintenance.archive_inactive_projects(actor)
        return json_response(200, {"archived": archived,
                                   "archive_after_days": maintenance.INACTIVITY_ARCHIVE_DAYS})

    router.add("POST", "/admin/maintenance", run)
