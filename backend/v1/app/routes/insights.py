"""HTTP routes for dashboards and reports."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import insights


def register(router: Router) -> None:
    """
    Register reporting routes.

    Args:
        router: The router to register routes on.
    """

    # [ACME: INSIGHTS ROUTES HERE]
    # How: Read-only endpoints built on the same visibility rules as the rest
    #      of the API, so each role's dashboard only ever covers what it can see.
    # Why: These answer the business questions directly: project status,
    #      at-risk projects, resource allocation, and cost versus budget.
    def overview(request: Request) -> dict[str, Any]:
        """Health of every visible project (?at_risk=true&include_closed=true)."""
        actor = current_user(request)
        return json_response(200, {"projects": insights.project_overview(actor, request.query)})

    def at_risk(request: Request) -> dict[str, Any]:
        """Only the projects with risk flags."""
        actor = current_user(request)
        query = {**request.query, "at_risk": "true"}
        return json_response(200, {"projects": insights.project_overview(actor, query)})

    def utilization(request: Request) -> dict[str, Any]:
        """How booked each visible employee is (?week=YYYY-MM-DD)."""
        actor = current_user(request)
        return json_response(200, insights.utilization(actor, request.query.get("week")))

    def timeline(request: Request) -> dict[str, Any]:
        """Projects and milestones for the portfolio timeline."""
        actor = current_user(request)
        return json_response(200, {"projects": insights.portfolio_timeline(actor)})

    def capacity(request: Request) -> dict[str, Any]:
        """Booked hours per person across weeks (?start=YYYY-MM-DD&weeks=6)."""
        actor = current_user(request)
        return json_response(200, insights.capacity(actor, request.query.get("start"),
                                                     request.query.get("weeks")))

    router.add("GET", "/insights/timeline", timeline)
    router.add("GET", "/insights/capacity", capacity)
    router.add("GET", "/insights/projects", overview)
    router.add("GET", "/insights/at-risk", at_risk)
    router.add("GET", "/insights/utilization", utilization)
