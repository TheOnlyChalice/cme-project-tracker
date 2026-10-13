"""
Create and check JSON Web Tokens (JWTs) for login sessions.

An access token proves who the caller is for a short time (default 60
minutes). A refresh token (default 7 days) can only be traded for a new pair
of tokens, so users stay signed in without re-entering their password.
"""

import logging
import os
import secrets
import time
from typing import Any

import jwt

from app.responses import ApiError

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ISSUER = "cme-project-tracker"
ACCESS = "access"
REFRESH = "refresh"


# [JWT SECRET HERE]
# How: Tokens are signed with the JWT_SECRET environment variable. On AWS,
#      Terraform generates a random 64-character secret (infra/jwt.tf) and
#      gives it to Lambda. Locally, put one in backend/v1/.env; if it's
#      missing, a random secret is made for this run only (tokens stop working
#      after a restart). On Lambda a missing secret is an error, never a
#      random fallback.
# Why: Anyone who knows the secret can forge a token for any user, so it must
#      be long, random, and kept out of the code and GitHub. A per-process
#      fallback on Lambda would be a silent bug: each Lambda copy would
#      reject the others' tokens.
def _secret() -> str:
    """
    Return the signing secret.

    Returns:
        The secret string.

    Raises:
        RuntimeError: On Lambda when JWT_SECRET isn't configured.
    """
    global _FALLBACK_SECRET  # pylint: disable=global-statement
    configured = os.getenv("JWT_SECRET", "").strip()
    if configured:
        return configured
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        raise RuntimeError("JWT_SECRET is not configured for this Lambda function.")
    if _FALLBACK_SECRET is None:
        logger.warning("JWT_SECRET not set; using a temporary secret for this run only.")
        _FALLBACK_SECRET = secrets.token_urlsafe(48)
    return _FALLBACK_SECRET


_FALLBACK_SECRET: str | None = None


def access_minutes() -> int:
    """
    How long access tokens last.

    Returns:
        Minutes, from ACCESS_TOKEN_MINUTES (default 60).
    """
    return int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))


def refresh_days() -> int:
    """
    How long refresh tokens last.

    Returns:
        Days, from REFRESH_TOKEN_DAYS (default 7).
    """
    return int(os.getenv("REFRESH_TOKEN_DAYS", "7"))


# [TOKEN CONTENTS HERE]
# How: Each token carries the user's ID (sub), username, role, token version
#      (ver), its type (access or refresh), when it was issued (iat), when it
#      expires (exp), a unique ID (jti), and the issuer (iss). It's signed
#      with HMAC-SHA256.
# Why: The signature means the token can't be edited without the secret, so
#      a user can't change their own role or ID. The role inside is only for
#      the frontend's convenience: the backend always rereads the user's real
#      role from the database, so a role change takes effect immediately.
def issue_token(user: dict[str, Any], kind: str, lifetime_seconds: int | None = None) -> str:
    """
    Create a signed token for a user.

    Args:
        user: The user record.
        kind: ACCESS or REFRESH.
        lifetime_seconds: Override the default lifetime (used by tests).

    Returns:
        The encoded token.
    """
    now = int(time.time())
    if lifetime_seconds is None:
        lifetime_seconds = access_minutes() * 60 if kind == ACCESS else refresh_days() * 86400
    claims = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "ver": user.get("token_version", 0),
        "type": kind,
        "iss": ISSUER,
        "iat": now,
        "exp": now + lifetime_seconds,
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def issue_pair(user: dict[str, Any]) -> dict[str, Any]:
    """
    Create an access token and a refresh token.

    Args:
        user: The user record.

    Returns:
        The tokens plus their type and the access token's lifetime in seconds.
    """
    return {
        "access_token": issue_token(user, ACCESS),
        "refresh_token": issue_token(user, REFRESH),
        "token_type": "Bearer",
        "expires_in": access_minutes() * 60,
    }


# [TOKEN VERIFICATION HERE]
# How: The signature, expiry, issuer, and required claims are all checked,
#      only HS256 is accepted, and the token type must match what the
#      endpoint expects. Expired tokens get their own error code.
# Why: Fixing the algorithm blocks the well-known attack where a forged token
#      claims "alg: none". Checking the type stops a long-lived refresh token
#      being used as an access token. A separate "token_expired" code tells
#      the frontend to refresh, rather than send the user back to login.
def decode_token(token: str, expected_kind: str) -> dict[str, Any]:
    """
    Check a token and return its claims.

    Args:
        token: The encoded token.
        expected_kind: ACCESS or REFRESH.

    Returns:
        The verified claims.

    Raises:
        ApiError: 401 if the token is expired, invalid, or the wrong type.
    """
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM], issuer=ISSUER,
                            options={"require": ["exp", "iat", "sub", "iss", "type"]})
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "invalid_token", "The sign-in token is invalid.") from exc
    if claims.get("type") != expected_kind:
        raise ApiError(401, "invalid_token", "The sign-in token is the wrong type.")
    return claims
