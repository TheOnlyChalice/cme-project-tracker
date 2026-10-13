"""
Sign-in logic: login, token refresh, and logout.

Failed logins are counted and an account is locked for a while after too
many in a row, which slows down anyone trying to guess passwords.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app import tokens
from app.auth import user_from_claims
from app.passwords import hash_password, verify_password
from app.responses import ApiError
from app.services.users import revoke_tokens, serialize_user
from app.store import store
from app.utils import now_iso
from app.validation import Validator, reject_unknown_fields

Record = dict[str, Any]

# [LOGIN LOCKOUT HERE]
# How: Five wrong passwords in a row lock the account for 15 minutes. While
#      it's locked, the password isn't even checked. A successful login, or an
#      admin setting a new password, clears the count.
# Why: Without a limit, a script could try thousands of passwords against one
#      account. Locking briefly makes guessing impractical while a real user
#      who mistyped only waits a few minutes.
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

_DUMMY_HASH: str | None = None


def _dummy_hash() -> str:
    """
    A throwaway hash used when the username doesn't exist.

    Returns:
        A valid password hash for a password nobody knows.
    """
    global _DUMMY_HASH  # pylint: disable=global-statement
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-real-password-0")
    return _DUMMY_HASH


def _find_user(identifier: str) -> Record | None:
    """
    Find a user by username or email (ignoring case).

    Args:
        identifier: What the person typed in the username box.

    Returns:
        The user, or None.
    """
    lowered = identifier.strip().lower()
    field = "email" if "@" in lowered else "username"
    matches = store.find("users", where={field: lowered})
    return matches[0] if matches else None


def _failure(code: str, message: str, status: int = 401,
             details: Record | None = None) -> tuple[int, Record]:
    """
    Build a login failure response body.

    Args:
        code: Error code.
        message: Human-readable message.
        status: HTTP status.
        details: Extra values (e.g. minutes left) so the frontend can translate.

    Returns:
        (status, body).
    """
    error: Record = {"code": code, "message": message}
    if details:
        error["details"] = details
    return status, {"error": error}


# [LOGIN HERE]
# How: Look the user up by username or email, check the password against the
#      stored PBKDF2 hash, and on success return an access token, a refresh
#      token, and the user's profile. Wrong username and wrong password give
#      the same message, and a missing user still runs a password check.
#      Failures are returned (not raised) so the failed-attempt count is saved.
# Why: Identical errors and timing stop attackers finding out which usernames
#      exist. Every other request raises errors, which undoes its changes;
#      login must keep its failure count, so it's handled differently on purpose.
def login(data: Any) -> tuple[int, Record]:
    """
    Sign a user in.

    Args:
        data: {"username": username or email, "password": ...}.

    Returns:
        (status, body): 200 with tokens, or an error.
    """
    check = Validator(data)
    reject_unknown_fields(check.data, ("username", "password"))
    check.string("username", required=True, max_length=254)
    if not isinstance(check.data.get("password"), str) or not check.data["password"]:
        check.errors["password"] = "This field is required."
    check.raise_if_errors()

    password = check.data["password"]
    user = _find_user(check.cleaned["username"])
    invalid = ("invalid_credentials", "The username or password is incorrect.")

    if user is None or user.get("is_archived"):
        verify_password(password, _dummy_hash())
        return _failure(*invalid)

    now = datetime.now(timezone.utc)
    locked_until = user.get("locked_until")
    if locked_until and datetime.fromisoformat(locked_until) > now:
        minutes = max(1, int((datetime.fromisoformat(locked_until) - now).total_seconds() // 60) + 1)
        return _failure("account_locked",
                        f"Too many failed attempts. Try again in about {minutes} minutes.", 429,
                        {"minutes": minutes})

    if not verify_password(password, user["password_hash"]):
        failures = (user.get("failed_login_count") or 0) + 1
        changes: Record = {"failed_login_count": failures}
        if failures >= MAX_FAILED_LOGINS:
            changes = {"failed_login_count": 0,
                       "locked_until": (now + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()}
            store.update("users", user["id"], changes)
            return _failure("account_locked",
                            f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.", 429,
                            {"minutes": LOCKOUT_MINUTES})
        store.update("users", user["id"], changes)
        return _failure(*invalid)

    if user.get("failed_login_count") or user.get("locked_until"):
        user = store.update("users", user["id"], {"failed_login_count": 0, "locked_until": None})
    return 200, {**tokens.issue_pair(user), "user": serialize_user(user, user)}


# [TOKEN REFRESH HERE]
# How: A valid, unrevoked refresh token is exchanged for a brand-new access
#      and refresh token pair.
# Why: Access tokens are short-lived to limit the damage if one leaks. Refresh
#      lets the frontend keep someone signed in for up to 7 days without
#      asking for their password every hour.
def refresh(data: Any) -> Record:
    """
    Exchange a refresh token for new tokens.

    Args:
        data: {"refresh_token": ...}.

    Returns:
        New tokens and the user's profile.

    Raises:
        ApiError: 400 if missing, 401 if invalid, expired, or revoked.
    """
    check = Validator(data)
    reject_unknown_fields(check.data, ("refresh_token",))
    token = check.data.get("refresh_token")
    if not isinstance(token, str) or not token:
        raise ApiError(400, "validation_error", "Some fields are invalid.",
                       {"refresh_token": "This field is required."})
    user = user_from_claims(tokens.decode_token(token, tokens.REFRESH))
    return {**tokens.issue_pair(user), "user": serialize_user(user, user)}


# [LOGOUT HERE]
# How: Logging out raises the user's token version, which instantly
#      invalidates every access and refresh token they hold, on every device.
# Why: Simply deleting the token in the browser would leave copies usable
#      until they expire. Revoking server-side makes logout real.
def logout(actor: Record) -> Record:
    """
    Sign a user out everywhere.

    Args:
        actor: The signed-in user.

    Returns:
        A confirmation message.
    """
    revoke_tokens(actor["id"])
    return {"message": "Signed out.", "signed_out_at": now_iso()}
