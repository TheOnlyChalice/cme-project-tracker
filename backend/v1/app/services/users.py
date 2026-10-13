"""
User business logic: creation, updates, visibility, and reporting lines.

Routes call these functions; nothing here knows about HTTP requests, which
keeps the rules testable on their own.
"""

import re
import secrets
import string
from typing import Any

from app.audit import record_audit
from app.passwords import hash_password, password_problem, verify_password
from app.permissions import (ADMIN, EMPLOYEE, MANAGER, ROLES, can_view_user,
                             has_role, is_admin, require_role)
from app.responses import ApiError
from app.services.hour_release import release_future_assignments
from app.store import store
from app.utils import new_id, now_iso
from app.validation import Validator, reject_unknown_fields

Record = dict[str, Any]

TABLE = "users"
USERNAME_LENGTH = 6

# [FIELD PERMISSIONS HERE]
# How: Two allow-lists decide which fields each kind of caller may send.
#      Anyone may edit their own personal details; only admins may set
#      role, salary, job title, and reporting manager.
# Why: The requirements say employees can modify only their own personal data
#      and only admins can change roles or see salary. Rejecting unexpected
#      fields (instead of silently ignoring them) makes mistakes obvious.
SELF_EDITABLE = ("first_name", "last_name", "email", "password", "current_password",
                 "profile_picture_url")
ADMIN_EDITABLE = SELF_EDITABLE + ("role", "job_title", "salary", "manager_id")
CREATE_FIELDS = tuple(f for f in ADMIN_EDITABLE if f != "current_password")

# Sign-in bookkeeping that never leaves the API (or only for admins).
HIDDEN_FIELDS = frozenset({"password_hash", "token_version", "failed_login_count"})


# [USER SERIALIZATION HERE]
# How: Every user leaving the API goes through this function. The password
#      hash is always removed, and salary is removed unless the viewer is an
#      admin. Admins also see who reports to whom.
# Why: Filtering in one place guarantees no endpoint can leak a password hash
#      or salary by accident, now or in later branches.
def serialize_user(user: Record, viewer: Record) -> Record:
    """
    Prepare a user record for an API response.

    Args:
        user: The stored user record.
        viewer: The user who will receive the response.

    Returns:
        A copy safe to return to this viewer.
    """
    data = {key: value for key, value in user.items() if key not in HIDDEN_FIELDS}
    if not is_admin(viewer):
        data.pop("salary", None)
        data.pop("locked_until", None)
    data["current_project_ids"] = current_project_ids(user)
    # [OWN MANAGER NAME HERE]
    # How: When people look at their own record, it includes their manager's
    #      name (just the name, not the manager's full record).
    # Why: The profile page shows "Reports to", but employees can't look up
    #      other users. Adding only the name keeps that rule intact while
    #      telling them who plans their hours.
    if viewer["id"] == user["id"] and user.get("manager_id"):
        manager = store.get(TABLE, user["manager_id"])
        if manager:
            data["manager_name"] = f"{manager['first_name']} {manager['last_name']}"
    return data


# [CURRENT PROJECTS HERE]
# How: Worked out on the fly: a manager's current projects are the active
#      projects they manage; an employee's are the active projects managed by
#      their manager (their team's projects).
# Why: The data model says the system derives this list rather than storing
#      it, so it can never drift out of date.
def current_project_ids(user: Record) -> list[str]:
    """
    List the active projects a user is currently part of.

    Args:
        user: The stored user.

    Returns:
        Project IDs.
    """
    owner = user["id"] if has_role(user, MANAGER) else user.get("manager_id")
    if not owner:
        return []
    projects = store.find("projects", where={"manager_id": owner, "status": "active",
                                             "is_archived": False})
    return [p["id"] for p in projects]


# [USERNAME GENERATION HERE]
# How: First initial + up to 3 letters of the last name, padded with random
#      digits to 6 characters (e.g. Jane Smith -> "jsmi42"). It retries with
#      new digits if taken, then falls back to fully random characters.
# Why: The data model says usernames are 6 characters, system-generated, and
#      unique. Basing them on the name keeps them recognizable. The secrets
#      module is used instead of random because the Bandit security scan
#      flags random for anything security-related.
def generate_username(first_name: str, last_name: str) -> str:
    """
    Create a unique 6-character username from a person's name.

    Args:
        first_name: The person's first name.
        last_name: The person's last name.

    Returns:
        A lowercase username not used by any other user.
    """
    taken = {u["username"] for u in store.find(TABLE)}
    letters = re.sub(r"[^a-z]", "", (first_name[:1] + last_name[:3]).lower())
    for _ in range(50):
        digits = "".join(secrets.choice(string.digits)
                         for _ in range(USERNAME_LENGTH - len(letters)))
        candidate = letters + digits
        if candidate not in taken:
            return candidate
    alphabet = string.ascii_lowercase + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(USERNAME_LENGTH))
        if candidate not in taken:
            return candidate


def _email_in_use(email: str, exclude_id: str | None = None) -> bool:
    """
    Check whether another user already has this email.

    Args:
        email: Lowercased email address.
        exclude_id: A user ID to ignore (the user being edited).

    Returns:
        True if the email is taken.
    """
    return bool(store.find(TABLE, lambda u: u["id"] != exclude_id, where={"email": email}))


# [REPORTING LINE CHECK HERE]
# How: A manager_id must point to an active manager or admin, can't be the
#      user themselves, and can't create a loop (A reports to B who reports
#      to A), which is checked by walking up the chain.
# Why: A "team" is simply the employees under a manager, so every rule about
#      what employees can see depends on this link being valid.
def _validate_manager(manager_id: Any, user_id: str | None, errors: dict[str, str]) -> None:
    """
    Check that a proposed manager is valid, adding to errors if not.

    Args:
        manager_id: The proposed manager's ID.
        user_id: The user being created or edited (None when creating).
        errors: Error map to add a "manager_id" message to.
    """
    if not isinstance(manager_id, str):
        errors["manager_id"] = "Must be a user ID."
        return
    manager = store.get(TABLE, manager_id)
    if manager is None or manager.get("is_archived"):
        errors["manager_id"] = "No active user has this ID."
    elif not has_role(manager, MANAGER):
        errors["manager_id"] = "Must be a manager or admin."
    elif manager_id == user_id:
        errors["manager_id"] = "A user can't report to themselves."
    else:
        seen = set()
        current = manager
        while current and current.get("manager_id") and current["id"] not in seen:
            seen.add(current["id"])
            if current["manager_id"] == user_id:
                errors["manager_id"] = "This would create a reporting loop."
                return
            current = store.get(TABLE, current["manager_id"])


def _active_admin_count() -> int:
    """
    Count admins who aren't archived.

    Returns:
        The number of active admins.
    """
    return len(store.find(TABLE, where={"role": ADMIN, "is_archived": False}))


def _direct_reports(user_id: str) -> list[Record]:
    """
    List active users who report to a user.

    Args:
        user_id: The manager's ID.

    Returns:
        The reporting users.
    """
    return store.find(TABLE, where={"manager_id": user_id, "is_archived": False})


# [SAFE PICTURE LINK HERE]
# How: A profile picture link must start with http:// or https://.
# Why: Found in the role-overlap review: without this, someone could save a
#      "javascript:" or "data:" link that other people's browsers would load
#      when showing their avatar. Only plain web links are allowed.
def _check_picture_url(check: Validator) -> None:
    """
    Reject profile picture links that aren't plain web addresses.

    Args:
        check: The validator holding the cleaned value.
    """
    url = check.cleaned.get("profile_picture_url")
    if url and not url.lower().startswith(("http://", "https://")):
        check.errors["profile_picture_url"] = "Must be a web link starting with http:// or https://."
        del check.cleaned["profile_picture_url"]


def create_user(actor: Record, data: Any) -> Record:
    """
    Create a user (admins only).

    Args:
        actor: The acting user.
        data: The request body.

    Returns:
        The new user, serialized for the actor.

    Raises:
        ApiError: 403 if not an admin, 400 for invalid fields, 409 for a duplicate email.
    """
    require_role(actor, ADMIN)
    check = Validator(data)
    reject_unknown_fields(check.data, CREATE_FIELDS)
    check.string("first_name", required=True, max_length=100)
    check.string("last_name", required=True, max_length=100)
    check.email("email", required=True)
    check.choice("role", ROLES, required=True)
    check.string("job_title", max_length=100, allow_empty=True)
    check.money("salary")
    check.string("profile_picture_url", max_length=500, allow_empty=True)
    _check_picture_url(check)

    problem = password_problem(check.data.get("password"))
    if problem:
        check.errors["password"] = "This field is required." if "password" not in check.data else problem

    # [EMPLOYEE NEEDS MANAGER HERE]
    # How: manager_id is required when the role is employee, optional otherwise.
    # Why: The data model requires employees to belong to a team, and a team
    #      is defined as the people under a manager.
    manager_id = check.data.get("manager_id")
    if manager_id is not None:
        _validate_manager(manager_id, None, check.errors)
    elif check.cleaned.get("role") == EMPLOYEE:
        check.errors["manager_id"] = "Employees must have a manager."
    check.raise_if_errors()

    if _email_in_use(check.cleaned["email"]):
        raise ApiError(409, "email_taken", "Another user already has this email.",
                       {"email": "Already in use."})

    timestamp = now_iso()
    user = {
        "id": new_id(),
        "username": generate_username(check.cleaned["first_name"], check.cleaned["last_name"]),
        "first_name": check.cleaned["first_name"],
        "last_name": check.cleaned["last_name"],
        "email": check.cleaned["email"],
        "password_hash": hash_password(check.data["password"]),
        "role": check.cleaned["role"],
        "job_title": check.cleaned.get("job_title"),
        "salary": check.cleaned.get("salary"),
        "profile_picture_url": check.cleaned.get("profile_picture_url"),
        "manager_id": manager_id,
        "token_version": 0,
        "failed_login_count": 0,
        "locked_until": None,
        "is_archived": False,
        "archived_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    store.insert(TABLE, user)
    record_audit(actor, "create", "user", user["id"], None, user)
    return serialize_user(user, actor)


def get_visible_user(actor: Record, user_id: str) -> Record:
    """
    Fetch a user the actor is allowed to see.

    Args:
        actor: The acting user.
        user_id: The user to fetch.

    Returns:
        The stored user record.

    Raises:
        ApiError: 404 if the user doesn't exist or the actor can't see them.
    """
    # [HIDE WHAT YOU CAN'T SEE HERE]
    # How: A user the actor isn't allowed to see returns 404, the same as one
    #      that doesn't exist.
    # Why: Returning 403 would confirm the user exists, which leaks
    #      information about people outside the actor's team.
    user = store.get(TABLE, user_id)
    if user is None or not can_view_user(actor, user):
        raise ApiError(404, "not_found", "User not found.")
    return user


# [USER SEARCH AND FILTERS HERE]
# How: Start from the users the actor may see, then narrow by role,
#      manager_id, or a search term matched against name, email, and username.
#      Archived users appear only for admins who ask with include_archived=true.
# Why: Covers the search and filter requirement, and applying visibility first
#      means filters can never reveal users outside the actor's view.
def list_users(actor: Record, query: dict[str, str]) -> list[Record]:
    """
    List the users the actor may see, with optional filters.

    Args:
        actor: The acting user.
        query: Query parameters: role, manager_id, search, include_archived.

    Returns:
        Matching users, serialized for the actor, sorted by name.
    """
    include_archived = query.get("include_archived", "").lower() == "true" and is_admin(actor)
    role = query.get("role")
    manager_id = query.get("manager_id")
    search = (query.get("search") or "").strip().lower()

    def matches(user: Record) -> bool:
        """Decide whether a user passes visibility and every filter."""
        if user.get("is_archived") and not include_archived:
            return False
        if not can_view_user(actor, user):
            return False
        if role and user["role"] != role:
            return False
        if manager_id and user.get("manager_id") != manager_id:
            return False
        if search:
            haystack = " ".join([user["first_name"], user["last_name"],
                                 user["email"], user["username"]]).lower()
            if search not in haystack:
                return False
        return True

    users = store.find(TABLE, matches)
    users.sort(key=lambda u: (u["last_name"].lower(), u["first_name"].lower()))
    return [serialize_user(u, actor) for u in users]


def list_team(actor: Record, manager_id: str) -> list[Record]:
    """
    List the employees who report to a manager.

    Args:
        actor: The acting user (the manager themselves, or an admin).
        manager_id: The manager whose team to list.

    Returns:
        The team members, serialized for the actor.

    Raises:
        ApiError: 404 if the actor can't see this manager's team.
    """
    manager = get_visible_user(actor, manager_id)
    if not is_admin(actor) and actor["id"] != manager["id"]:
        raise ApiError(404, "not_found", "User not found.")
    return [serialize_user(u, actor) for u in _direct_reports(manager_id)]


def update_user(actor: Record, user_id: str, data: Any) -> Record:
    """
    Update a user's fields, enforcing who may change what.

    Args:
        actor: The acting user.
        user_id: The user to update.
        data: The request body with fields to change.

    Returns:
        The updated user, serialized for the actor.

    Raises:
        ApiError: 403/404 for permission problems, 400 for invalid fields,
                  409 for conflicts such as a duplicate email or removing the
                  last admin.
    """
    target = get_visible_user(actor, user_id)
    editing_self = actor["id"] == target["id"]
    if not is_admin(actor) and not editing_self:
        raise ApiError(403, "forbidden", "You can only edit your own details.")
    if target.get("is_archived"):
        raise ApiError(409, "archived", "Restore this user before editing them.")

    check = Validator(data)
    reject_unknown_fields(check.data, ADMIN_EDITABLE if is_admin(actor) else SELF_EDITABLE)
    if not check.data:
        raise ApiError(400, "no_changes", "Send at least one field to change.")

    check.string("first_name", max_length=100)
    check.string("last_name", max_length=100)
    check.email("email")
    check.string("profile_picture_url", max_length=500, allow_empty=True)
    _check_picture_url(check)
    check.choice("role", ROLES)
    check.string("job_title", max_length=100, allow_empty=True)
    check.money("salary")
    if check.has("password"):
        problem = password_problem(check.data["password"])
        if problem:
            check.errors["password"] = problem
        # [CURRENT PASSWORD CHECK HERE]
        # How: Changing your own password requires sending your current one too.
        #      Admins resetting someone else's password don't need it.
        # Why: If someone walks up to a signed-in computer, or steals a token,
        #      they still can't lock the real owner out by changing the password.
        elif editing_self and not verify_password(str(check.data.get("current_password", "")),
                                                  target["password_hash"]):
            check.errors["current_password"] = "Enter your current password correctly."
    elif check.has("current_password"):
        check.errors["current_password"] = "Only send this when changing your password."
    if check.has("manager_id") and check.data["manager_id"] is not None:
        _validate_manager(check.data["manager_id"], target["id"], check.errors)
    check.raise_if_errors()

    changes: Record = dict(check.cleaned)
    if check.has("password"):
        changes["password_hash"] = hash_password(check.data["password"])
        changes["failed_login_count"] = 0
        changes["locked_until"] = None
    if check.has("manager_id"):
        changes["manager_id"] = check.data["manager_id"]

    if "email" in changes and _email_in_use(changes["email"], target["id"]):
        raise ApiError(409, "email_taken", "Another user already has this email.",
                       {"email": "Already in use."})

    new_role = changes.get("role", target["role"])
    new_manager = changes.get("manager_id", target.get("manager_id"))

    # [ROLE CHANGE SAFEGUARDS HERE]
    # How: Before saving, check that an employee still has a manager, that a
    #      manager being demoted has no one reporting to them, and that the
    #      last active admin can't be demoted.
    # Why: Each of these would leave the data in a broken state: an employee
    #      with no team, employees reporting to a non-manager, or nobody able
    #      to administer the system.
    if new_role == EMPLOYEE and not new_manager:
        raise ApiError(409, "manager_required", "Employees must have a manager.",
                       {"manager_id": "Required for employees."})
    if target["role"] in (MANAGER, ADMIN) and new_role == EMPLOYEE and _direct_reports(target["id"]):
        raise ApiError(409, "has_reports",
                       "Reassign this user's team to another manager before changing their role.")
    # [DEMOTED MANAGER CHECK HERE]
    # How: Someone who still manages an open project can't be made an employee.
    # Why: Found in the role-overlap review: otherwise a project could end up
    #      "managed" by an employee, who could then edit it and assign hours
    #      even though employees aren't allowed to.
    if target["role"] in (MANAGER, ADMIN) and new_role == EMPLOYEE and store.find(
            "projects", where={"manager_id": target["id"], "status": "active", "is_archived": False}):
        raise ApiError(409, "manages_projects",
                       "Reassign this user's active projects before making them an employee.")
    if target["role"] == ADMIN and new_role != ADMIN and _active_admin_count() <= 1:
        raise ApiError(409, "last_admin", "You can't remove the last admin.")

    # Signing everyone out after a password or role change (see revoke_tokens).
    if "password_hash" in changes or ("role" in changes and changes["role"] != target["role"]):
        changes["token_version"] = (target.get("token_version") or 0) + 1

    changes["updated_at"] = now_iso()
    updated = store.update(TABLE, target["id"], changes)

    # [SPLIT AUDIT ENTRIES HERE]
    # How: A role change and a manager change each get their own audit entry
    #      (assign_role, assign_team); all other edits share one "update" entry.
    # Why: The audit model has specific actions for these, so admins can filter
    #      for "who changed roles" without reading every update.
    role_fields = {"role"}
    team_fields = {"manager_id"}
    def pick(record: Record, fields: set[str]) -> Record:
        """Keep only the given fields of a record."""
        return {k: v for k, v in record.items() if k in fields}

    if "role" in check.cleaned and updated["role"] != target["role"]:
        record_audit(actor, "assign_role", "user", target["id"],
                     pick(target, role_fields), pick(updated, role_fields))
    if check.has("manager_id") and updated.get("manager_id") != target.get("manager_id"):
        record_audit(actor, "assign_team", "user", target["id"],
                     pick(target, team_fields), pick(updated, team_fields))
        # [TEAM MOVE RELEASES HOURS HERE]
        # How: Future hours booked on the old manager's projects are released.
        # Why: The employee can no longer see those projects, and their new
        #      manager needs those hours free to plan with.
        new_manager_id = updated.get("manager_id")
        release_future_assignments(actor, lambda a: (
            a["user_id"] == target["id"]
            and (store.get("projects", a["project_id"]) or {}).get("manager_id") != new_manager_id))
    other_before = {k: v for k, v in target.items() if k not in role_fields | team_fields}
    other_after = {k: v for k, v in updated.items() if k not in role_fields | team_fields}
    if any(other_before.get(k) != other_after.get(k) for k in other_after if k != "updated_at"):
        record_audit(actor, "update", "user", target["id"], other_before, other_after)

    return serialize_user(updated, actor)


# [USER ARCHIVE AND RESTORE HERE]
# How: Archiving (admins only) hides a user and releases their future hours.
#      It's blocked if they still have people reporting to them, still manage
#      an open project, or are the last admin. Restoring brings them back, as
#      long as their manager is active.
# Why: Users are never deleted, so their history and audit trail stay intact.
#      The blocks stop archiving from leaving orphaned teams or projects.
def archive_user(actor: Record, user_id: str) -> Record:
    """
    Archive (soft-delete) a user (admins only).

    Args:
        actor: The acting user.
        user_id: The user to archive.

    Returns:
        The archived user, serialized for the actor.
    """
    require_role(actor, ADMIN)
    target = get_visible_user(actor, user_id)
    if target.get("is_archived"):
        raise ApiError(409, "already_archived", "This user is already archived.")
    if target["id"] == actor["id"]:
        raise ApiError(409, "self_archive", "You can't archive yourself.")
    if _direct_reports(target["id"]):
        raise ApiError(409, "has_reports", "Reassign this user's team before archiving them.")
    if store.find("projects", where={"manager_id": target["id"], "status": "active",
                                     "is_archived": False}):
        raise ApiError(409, "manages_projects",
                       "Reassign this user's active projects before archiving them.")
    if target["role"] == ADMIN and _active_admin_count() <= 1:
        raise ApiError(409, "last_admin", "You can't archive the last admin.")
    timestamp = now_iso()
    updated = store.update(TABLE, target["id"], {
        "is_archived": True, "archived_at": timestamp, "updated_at": timestamp,
        "token_version": (target.get("token_version") or 0) + 1})
    record_audit(actor, "archive", "user", target["id"], target, updated)
    release_future_assignments(actor, lambda a: a["user_id"] == target["id"])
    return serialize_user(updated, actor)


def restore_user(actor: Record, user_id: str) -> Record:
    """
    Restore an archived user (admins only).

    Args:
        actor: The acting user.
        user_id: The user to restore.

    Returns:
        The restored user, serialized for the actor.
    """
    require_role(actor, ADMIN)
    target = get_visible_user(actor, user_id)
    if not target.get("is_archived"):
        raise ApiError(409, "not_archived", "This user isn't archived.")
    if target.get("manager_id"):
        manager = store.get(TABLE, target["manager_id"])
        if manager is None or manager.get("is_archived"):
            raise ApiError(409, "manager_archived",
                           "This user's manager is archived. Restore the manager first.")
    updated = store.update(TABLE, target["id"], {
        "is_archived": False, "archived_at": None, "updated_at": now_iso()})
    record_audit(actor, "restore", "user", target["id"], target, updated)
    return serialize_user(updated, actor)


# [REVOKE TOKENS HERE]
# How: Adds 1 to the user's token_version. Tokens carry the version they were
#      issued with, so every older token is rejected from then on.
# Why: Used for logout, and applied automatically after a password change, a
#      role change, or archiving, so an old token can never outlive the
#      change that should have ended it.
def revoke_tokens(user_id: str) -> None:
    """
    Invalidate every token a user currently holds.

    Args:
        user_id: The user's ID.
    """
    user = store.get(TABLE, user_id)
    if user is not None:
        store.update(TABLE, user_id, {"token_version": (user.get("token_version") or 0) + 1})
