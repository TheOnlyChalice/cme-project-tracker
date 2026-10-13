"""Identify the user making each request."""

from typing import Any

from app.request import Request
from app.responses import ApiError
from app.store import store

Record = dict[str, Any]

DEV_USER_HEADER = "x-user-id"


# [DEV USER HEADER HERE]
# How: The caller names who they are acting as in an "X-User-Id" header,
#      using either the user's ID or their 6-character username.
# Why: Phase 1 has no login, but every visibility and permission rule depends
#      on who is asking. This header lets all of those rules be built and
#      tested now. It is TEMPORARY: Phase 2 (08-jwt-auth) replaces this one
#      function with JWT token checks, and no permission rule has to change.
#      Anyone can claim any identity with this header, so it must be removed
#      before real data is used.
def current_user(request: Request) -> Record:
    """
    Return the user making the request.

    Args:
        request: The incoming request.

    Returns:
        The acting user's record.

    Raises:
        ApiError: 401 if no user is given or the user doesn't exist or is archived.
    """
    claimed = (request.headers.get(DEV_USER_HEADER) or "").strip()
    if not claimed:
        raise ApiError(401, "authentication_required",
                       "Send an X-User-Id header with your user ID or username.")
    user = store.get("users", claimed)
    if user is None:
        matches = store.find("users", lambda u: u["username"] == claimed.lower())
        user = matches[0] if matches else None
    if user is None or user.get("is_archived"):
        raise ApiError(401, "invalid_user", "That user doesn't exist or is archived.")
    return user
