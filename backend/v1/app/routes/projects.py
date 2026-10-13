"""HTTP routes for projects."""

from typing import Any

from app import clock
from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import insights, projects


def register(router: Router) -> None:
    """
    Register project routes.

    Args:
        router: The router to register routes on.
    """

    def list_all(request: Request) -> dict[str, Any]:
        """List projects (?status=&manager_id=&search=&include_archived=)."""
        actor = current_user(request)
        return json_response(200, {"projects": projects.list_projects(actor, request.query)})

    def create(request: Request) -> dict[str, Any]:
        """Create a project (admins only)."""
        actor = current_user(request)
        return json_response(201, projects.create_project(actor, request.json()))

    def get_one(request: Request) -> dict[str, Any]:
        """Fetch one project."""
        actor = current_user(request)
        project = projects.get_visible_project(actor, request.path_params["id"])
        return json_response(200, projects.serialize_project(project, actor))

    def update(request: Request) -> dict[str, Any]:
        """Update a project (its manager or an admin)."""
        actor = current_user(request)
        return json_response(200, projects.update_project(actor, request.path_params["id"],
                                                          request.json()))

    def complete(request: Request) -> dict[str, Any]:
        """Mark a project completed (its manager or an admin)."""
        actor = current_user(request)
        return json_response(200, projects.complete_project(actor, request.path_params["id"]))

    def abandon(request: Request) -> dict[str, Any]:
        """Mark a project abandoned (admins only)."""
        actor = current_user(request)
        return json_response(200, projects.abandon_project(actor, request.path_params["id"]))

    def archive(request: Request) -> dict[str, Any]:
        """Archive (soft-delete) a project (admins only)."""
        actor = current_user(request)
        return json_response(200, projects.archive_project(actor, request.path_params["id"]))

    def restore(request: Request) -> dict[str, Any]:
        """Restore an archived project (admins only)."""
        actor = current_user(request)
        return json_response(200, projects.restore_project(actor, request.path_params["id"]))

    def health(request: Request) -> dict[str, Any]:
        """Progress, hours, cost, and risk for one project."""
        actor = current_user(request)
        project = projects.get_visible_project(actor, request.path_params["id"])
        return json_response(200, insights.project_health(project, actor,
                                                          clock.today()))

    def chain(request: Request) -> dict[str, Any]:
        """The project's milestone dependency chain."""
        actor = current_user(request)
        return json_response(200, {"milestones": insights.project_chain(
            actor, request.path_params["id"])})

    router.add("GET", "/projects", list_all)
    router.add("POST", "/projects", create)
    router.add("GET", "/projects/{id}", get_one)
    router.add("PATCH", "/projects/{id}", update)
    router.add("DELETE", "/projects/{id}", archive)
    router.add("POST", "/projects/{id}/complete", complete)
    router.add("POST", "/projects/{id}/abandon", abandon)
    router.add("POST", "/projects/{id}/restore", restore)
    router.add("GET", "/projects/{id}/health", health)
    router.add("GET", "/projects/{id}/milestone-chain", chain)
