"""HTTP routes for signing in and out."""

from typing import Any

from app.auth import current_user
from app.request import Request
from app.responses import json_response
from app.router import Router
from app.services import auth


def register(router: Router) -> None:
    """
    Register sign-in routes.

    Args:
        router: The router to register routes on.
    """

    def login(request: Request) -> dict[str, Any]:
        """Sign in with username (or email) and password."""
        status, body = auth.login(request.json())
        return json_response(status, body)

    def refresh(request: Request) -> dict[str, Any]:
        """Trade a refresh token for new tokens."""
        return json_response(200, auth.refresh(request.json()))

    def logout(request: Request) -> dict[str, Any]:
        """Sign out on every device."""
        return json_response(200, auth.logout(current_user(request)))

    router.add("POST", "/auth/login", login)
    router.add("POST", "/auth/refresh", refresh)
    router.add("POST", "/auth/logout", logout)
