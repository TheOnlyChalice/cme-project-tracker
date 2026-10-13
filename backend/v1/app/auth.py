"""Identify the user making each request from their sign-in token."""

from typing import Any

from app import tokens
from app.request import Request
from app.responses import ApiError
from app.store import store

Record = dict[str, Any]


def user_from_claims(claims: dict[str, Any]) -> Record:
    """
    Load the user a verified token belongs to, and check it's still valid.

    Args:
        claims: Verified token claims.

    Returns:
        The user's current record.

    Raises:
        ApiError: 401 if the user is gone or archived, or the token was revoked.
    """
    user = store.get("users", str(claims.get("sub", "")))
    if user is None or user.get("is_archived"):
        raise ApiError(401, "invalid_user", "This account no longer exists or is archived.")
    # [TOKEN REVOCATION HERE]
    # How: Every token records the user's token_version when it was issued.
    #      Logging out, changing a password, changing role, or being archived
    #      increases token_version, so all older tokens stop working at once.
    # Why: JWTs can't be "deleted" once issued. A version number stored in the
    #      database gives a simple, reliable way to sign someone out everywhere.
    if claims.get("ver") != user.get("token_version", 0):
        raise ApiError(401, "token_revoked", "You've been signed out. Please sign in again.")
    return user


# [BEARER TOKEN AUTH HERE]
# How: The caller sends "Authorization: Bearer <access token>". The token is
#      verified, then the user is loaded fresh from the database, so their
#      current role, manager, and archived status are always what's used.
# Why: This replaces Phase 1's X-User-Id header, which let anyone claim to be
#      anyone. Every permission rule calls this one function, so swapping the
#      header for JWT changed nothing else in the permission system.
def current_user(request: Request) -> Record:
    """
    Return the signed-in user making the request.

    Args:
        request: The incoming request.

    Returns:
        The acting user's record.

    Raises:
        ApiError: 401 if the token is missing, invalid, expired, or revoked.
    """
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "authentication_required",
                       "Sign in and send your token as 'Authorization: Bearer <token>'.")
    claims = tokens.decode_token(token.strip(), tokens.ACCESS)
    return user_from_claims(claims)
