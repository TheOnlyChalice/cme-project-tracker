"""HTTP routes for milestones."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import milestones


def register(router: Router) -> None:
    """
    Register milestone routes.

    Args:
        router: The router to register routes on.
    """

    def list_for_project(request: Request) -> dict[str, Any]:
        """List a project's milestones (?status=&include_archived=)."""
        actor = current_user(request)
        return json_response(200, {"milestones": milestones.list_milestones(
            actor, request.path_params["id"], request.query)})

    def create(request: Request) -> dict[str, Any]:
        """Add a milestone to a project."""
        actor = current_user(request)
        return json_response(201, milestones.create_milestone(
            actor, request.path_params["id"], request.json()))

    def get_one(request: Request) -> dict[str, Any]:
        """Fetch one milestone."""
        actor = current_user(request)
        milestone, _ = milestones.get_visible_milestone(actor, request.path_params["id"])
        return json_response(200, milestones.serialize_milestone(milestone))

    def update(request: Request) -> dict[str, Any]:
        """Update a milestone."""
        actor = current_user(request)
        return json_response(200, milestones.update_milestone(
            actor, request.path_params["id"], request.json()))

    def complete(request: Request) -> dict[str, Any]:
        """Mark a milestone completed."""
        actor = current_user(request)
        return json_response(200, milestones.complete_milestone(actor, request.path_params["id"]))

    def archive(request: Request) -> dict[str, Any]:
        """Archive (soft-delete) a milestone."""
        actor = current_user(request)
        return json_response(200, milestones.archive_milestone(actor, request.path_params["id"]))

    def restore(request: Request) -> dict[str, Any]:
        """Restore an archived milestone (admins only)."""
        actor = current_user(request)
        return json_response(200, milestones.restore_milestone(actor, request.path_params["id"]))

    router.add("GET", "/projects/{id}/milestones", list_for_project)
    router.add("POST", "/projects/{id}/milestones", create)
    router.add("GET", "/milestones/{id}", get_one)
    router.add("PATCH", "/milestones/{id}", update)
    router.add("DELETE", "/milestones/{id}", archive)
    router.add("POST", "/milestones/{id}/complete", complete)
    router.add("POST", "/milestones/{id}/restore", restore)
