"""HTTP routes for the audit log (admins only)."""

from typing import Any

from app.audit import list_audit
from app.auth import current_user
from app.permissions import ADMIN, require_role
from app.request import Request
from app.responses import json_response
from app.router import Router


def register(router: Router) -> None:
    """
    Register audit log routes.

    Args:
        router: The router to register routes on.
    """

    # [AUDIT VIEW HERE]
    # How: GET /audit-log returns entries newest first with filters and paging.
    #      Admins only, and there are deliberately no routes to change or
    #      remove entries.
    # Why: The requirements make the audit log admin-only and unchangeable.
    def list_entries(request: Request) -> dict[str, Any]:
        """List audit log entries."""
        actor = current_user(request)
        require_role(actor, ADMIN)
        return json_response(200, list_audit(request.query))

    router.add("GET", "/audit-log", list_entries)
