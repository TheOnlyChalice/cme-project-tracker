"""HTTP routes for users."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import hours, users


def register(router: Router) -> None:
    """
    Register user routes.

    Args:
        router: The router to register routes on.
    """

    # [THIN ROUTES HERE]
    # How: Each route only identifies the caller, reads the request, and calls
    #      a service function. All rules live in app/services/users.py.
    # Why: Keeping HTTP handling separate from business rules means the rules
    #      can be unit-tested directly, and Phase 2 can change how the caller
    #      is identified without touching any rule.
    def me(request: Request) -> dict[str, Any]:
        """Return the calling user's own record."""
        actor = current_user(request)
        return json_response(200, users.serialize_user(actor, actor))

    def list_all(request: Request) -> dict[str, Any]:
        """List users the caller may see, with optional filters."""
        actor = current_user(request)
        return json_response(200, {"users": users.list_users(actor, request.query)})

    def create(request: Request) -> dict[str, Any]:
        """Create a user (admins only)."""
        actor = current_user(request)
        return json_response(201, users.create_user(actor, request.json()))

    def get_one(request: Request) -> dict[str, Any]:
        """Fetch one user."""
        actor = current_user(request)
        user = users.get_visible_user(actor, request.path_params["id"])
        return json_response(200, users.serialize_user(user, actor))

    def update(request: Request) -> dict[str, Any]:
        """Update a user."""
        actor = current_user(request)
        return json_response(200, users.update_user(actor, request.path_params["id"],
                                                    request.json()))

    def team(request: Request) -> dict[str, Any]:
        """List the employees who report to a manager."""
        actor = current_user(request)
        return json_response(200, {"users": users.list_team(actor, request.path_params["id"])})

    def archive(request: Request) -> dict[str, Any]:
        """Archive a user (admins only)."""
        actor = current_user(request)
        return json_response(200, users.archive_user(actor, request.path_params["id"]))

    def restore(request: Request) -> dict[str, Any]:
        """Restore an archived user (admins only)."""
        actor = current_user(request)
        return json_response(200, users.restore_user(actor, request.path_params["id"]))

    def availability(request: Request) -> dict[str, Any]:
        """Show how a user's week is booked (?week=YYYY-MM-DD, default this week)."""
        actor = current_user(request)
        return json_response(200, hours.availability(actor, request.path_params["id"],
                                                     request.query.get("week")))

    router.add("GET", "/me", me)
    router.add("GET", "/users", list_all)
    router.add("POST", "/users", create)
    router.add("GET", "/users/{id}", get_one)
    router.add("PATCH", "/users/{id}", update)
    router.add("GET", "/users/{id}/team", team)
    router.add("GET", "/users/{id}/availability", availability)
    router.add("DELETE", "/users/{id}", archive)
    router.add("POST", "/users/{id}/restore", restore)
