"""HTTP routes for weekly hour assignments."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import hours


def register(router: Router) -> None:
    """
    Register hour assignment routes.

    Args:
        router: The router to register routes on.
    """

    def list_all(request: Request) -> dict[str, Any]:
        """List assignments (?user_id=&project_id=&milestone_id=&week=&include_archived=)."""
        actor = current_user(request)
        return json_response(200, {"assignments": hours.list_assignments(actor, request.query)})

    def create(request: Request) -> dict[str, Any]:
        """Assign an employee's hours to a milestone."""
        actor = current_user(request)
        return json_response(201, hours.create_assignment(actor, request.json()))

    def update(request: Request) -> dict[str, Any]:
        """Change the hours on an assignment."""
        actor = current_user(request)
        return json_response(200, hours.update_assignment(actor, request.path_params["id"],
                                                          request.json()))

    def remove(request: Request) -> dict[str, Any]:
        """Remove an assignment, freeing the hours."""
        actor = current_user(request)
        return json_response(200, hours.remove_assignment(actor, request.path_params["id"]))

    router.add("GET", "/hour-assignments", list_all)
    router.add("POST", "/hour-assignments", create)
    router.add("PATCH", "/hour-assignments/{id}", update)
    router.add("DELETE", "/hour-assignments/{id}", remove)
