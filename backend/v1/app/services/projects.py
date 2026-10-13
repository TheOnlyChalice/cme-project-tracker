"""
Project business logic: creation, updates, status changes, and visibility.

Routes call these functions; nothing here knows about HTTP requests.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from app.audit import record_audit
from app.permissions import (ADMIN, MANAGER, can_manage_project, can_view_project,
                             has_role, is_admin, require_role, EMPLOYEE)
from app.responses import ApiError
from app.services.hour_release import release_future_assignments
from app.store import store
from app.utils import new_id, now_iso
from app.validation import Validator, reject_unknown_fields

Record = dict[str, Any]

TABLE = "projects"
STATUSES = ("active", "completed", "abandoned")

MANAGER_EDITABLE = ("name", "description", "start_date", "end_date",
                    "allocated_hours", "budget", "active_milestone_id")
ADMIN_EDITABLE = MANAGER_EDITABLE + ("manager_id",)


def _active_assignments(project_id: str) -> list[Record]:
    """
    List the project's hour assignments that still count.

    Args:
        project_id: The project's ID.

    Returns:
        Non-archived hour assignments for the project.
    """
    return store.find("hour_assignments", where={"project_id": project_id, "is_archived": False})


def assigned_hours(project_id: str, exclude_id: str | None = None) -> Decimal:
    """
    Total the hours assigned to a project.

    Args:
        project_id: The project's ID.
        exclude_id: An assignment to leave out (the one being edited).

    Returns:
        The total hours.
    """
    return sum((a["hours"] for a in _active_assignments(project_id) if a["id"] != exclude_id),
               Decimal("0"))


# [PROJECT SERIALIZATION HERE]
# How: Adds the derived lists from the data model (milestone IDs and assigned
#      employee IDs) plus hours assigned so far. Budget is hidden from employees.
# Why: The data model says these lists are worked out by the system rather
#      than stored, so they're always correct. Budget is management
#      information, so employees don't receive it.
def serialize_project(project: Record, viewer: Record) -> Record:
    """
    Prepare a project for an API response.

    Args:
        project: The stored project.
        viewer: The user who will receive the response.

    Returns:
        The project with derived fields, safe for this viewer.
    """
    data = dict(project)
    milestones = store.find("milestones", lambda m: is_admin(viewer) or not m.get("is_archived"),
                            where={"project_id": project["id"]})
    milestones.sort(key=lambda m: m["sequence"])
    assignments = _active_assignments(project["id"])
    data["milestone_ids"] = [m["id"] for m in milestones]
    data["assigned_employee_ids"] = sorted({a["user_id"] for a in assignments})
    data["hours_assigned"] = sum((a["hours"] for a in assignments), Decimal("0"))
    if viewer.get("role") == EMPLOYEE:
        data.pop("budget", None)
    return data


def get_visible_project(actor: Record, project_id: str) -> Record:
    """
    Fetch a project the actor may see.

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The stored project.

    Raises:
        ApiError: 404 if it doesn't exist or the actor can't see it.
    """
    project = store.get(TABLE, project_id)
    if project is None or not can_view_project(actor, project):
        raise ApiError(404, "not_found", "Project not found.")
    return project


# [OPEN PROJECT CHECK HERE]
# How: Changes to a project, its milestones, or its hours require the actor
#      to manage the project and the project to be active and not archived.
# Why: Completed, abandoned, and archived projects are closed records. An
#      admin must restore one before it can change, which keeps history intact
#      and leaves a "restore" entry in the audit log.
def get_managed_project(actor: Record, project_id: str, require_open: bool = True) -> Record:
    """
    Fetch a project the actor may change.

    Args:
        actor: The acting user.
        project_id: The project's ID.
        require_open: Whether the project must be active and not archived.

    Returns:
        The stored project.

    Raises:
        ApiError: 404 if not visible, 403 if not the manager, 409 if closed.
    """
    project = get_visible_project(actor, project_id)
    if not can_manage_project(actor, project):
        raise ApiError(403, "forbidden", "Only this project's manager or an admin can do this.")
    if require_open and (project.get("is_archived") or project["status"] != "active"):
        raise ApiError(409, "project_closed",
                       "This project is completed, abandoned, or archived. Restore it first.")
    return project


def _name_taken(name: str, exclude_id: str | None = None) -> bool:
    """
    Check whether another project already uses a name (ignoring case).

    Args:
        name: The proposed name.
        exclude_id: A project to ignore (the one being edited).

    Returns:
        True if the name is taken.
    """
    lowered = name.lower()
    return bool(store.find(TABLE, lambda p: p["name"].lower() == lowered and p["id"] != exclude_id))


def _check_manager(manager_id: Any, errors: dict[str, str]) -> None:
    """
    Check that a project manager is an active manager or admin.

    Args:
        manager_id: The proposed manager's ID.
        errors: Error map to add a "manager_id" message to.
    """
    manager = store.get("users", manager_id) if isinstance(manager_id, str) else None
    if manager is None or manager.get("is_archived"):
        errors["manager_id"] = "No active user has this ID."
    elif not has_role(manager, MANAGER):
        errors["manager_id"] = "Must be a manager or admin."


# [PROJECT DATE RULES HERE]
# How: The end date must be after the start date, and if the project already
#      has milestones, every milestone must still fit inside the new dates.
# Why: The data model requires end_date after start_date and milestone dates
#      inside the project's dates. Checking on project edits too stops a date
#      change from silently breaking existing milestones.
def _check_dates(project_id: str | None, start: str, end: str) -> None:
    """
    Validate project dates against each other and existing milestones.

    Args:
        project_id: The project being edited (None when creating).
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Raises:
        ApiError: 400 for invalid dates, 409 if milestones fall outside them.
    """
    if date.fromisoformat(end) <= date.fromisoformat(start):
        raise ApiError(400, "validation_error", "Some fields are invalid.",
                       {"end_date": "Must be after the start date."})
    if project_id:
        outside = store.find("milestones", lambda m: (
            m["start_date"] < start or m["end_date"] > end),
            where={"project_id": project_id, "is_archived": False})
        if outside:
            names = ", ".join(m["name"] for m in outside)
            raise ApiError(409, "milestones_outside_dates",
                           f"These milestones fall outside the new dates: {names}.")


# [PROJECT SEARCH AND FILTERS HERE]
# How: Start from the projects the actor may see, then narrow by status,
#      manager_id, or a search term matched against name and description.
#      Admins can add include_archived=true to see archived projects.
# Why: Covers the search and filter requirement while making sure filters can
#      never reveal projects outside the actor's view.
def list_projects(actor: Record, query: dict[str, str]) -> list[Record]:
    """
    List projects the actor may see, with optional filters.

    Args:
        actor: The acting user.
        query: Query parameters: status, manager_id, search, include_archived.

    Returns:
        Matching projects, serialized for the actor, sorted by end date.
    """
    include_archived = query.get("include_archived", "").lower() == "true" and is_admin(actor)
    status = query.get("status")
    manager_id = query.get("manager_id")
    search = (query.get("search") or "").strip().lower()

    def matches(project: Record) -> bool:
        """Decide whether a project passes visibility and every filter."""
        if project.get("is_archived") and not include_archived:
            return False
        if not can_view_project(actor, project):
            return False
        if status and project["status"] != status:
            return False
        if manager_id and project["manager_id"] != manager_id:
            return False
        if search and search not in (project["name"] + " " + (project.get("description") or "")).lower():
            return False
        return True

    projects = store.find(TABLE, matches)
    projects.sort(key=lambda p: (p["end_date"], p["name"].lower()))
    return [serialize_project(p, actor) for p in projects]


def create_project(actor: Record, data: Any) -> Record:
    """
    Create a project (admins only).

    Args:
        actor: The acting user.
        data: The request body.

    Returns:
        The new project, serialized for the actor.

    Raises:
        ApiError: 403 if not an admin, 400 for invalid fields, 409 for a duplicate name.
    """
    require_role(actor, ADMIN)
    check = Validator(data)
    reject_unknown_fields(check.data, ("name", "description", "start_date", "end_date",
                                       "allocated_hours", "budget", "manager_id"))
    check.string("name", required=True, max_length=150)
    check.string("description", max_length=5000, allow_empty=True)
    check.date("start_date", required=True)
    check.date("end_date", required=True)
    check.integer("allocated_hours", required=True, minimum=1)
    check.money("budget")
    if "manager_id" not in check.data:
        check.errors["manager_id"] = "This field is required."
    else:
        _check_manager(check.data["manager_id"], check.errors)
    check.raise_if_errors()

    _check_dates(None, check.cleaned["start_date"], check.cleaned["end_date"])
    if _name_taken(check.cleaned["name"]):
        raise ApiError(409, "name_taken", "Another project already has this name.",
                       {"name": "Already in use."})

    timestamp = now_iso()
    project = {
        "id": new_id(),
        "name": check.cleaned["name"],
        "description": check.cleaned.get("description"),
        "start_date": check.cleaned["start_date"],
        "end_date": check.cleaned["end_date"],
        "allocated_hours": check.cleaned["allocated_hours"],
        "budget": check.cleaned.get("budget"),
        "manager_id": check.data["manager_id"],
        "active_milestone_id": None,
        "status": "active",
        "is_archived": False,
        "archived_at": None,
        "created_by": actor["id"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    store.insert(TABLE, project)
    record_audit(actor, "create", "project", project["id"], None, project)
    return serialize_project(project, actor)


def update_project(actor: Record, project_id: str, data: Any) -> Record:
    """
    Update a project's fields.

    Args:
        actor: The acting user (the project's manager or an admin).
        project_id: The project to update.
        data: The request body with fields to change.

    Returns:
        The updated project, serialized for the actor.

    Raises:
        ApiError: For permission problems, invalid fields, or conflicts.
    """
    project = get_managed_project(actor, project_id)
    check = Validator(data)
    reject_unknown_fields(check.data, ADMIN_EDITABLE if is_admin(actor) else MANAGER_EDITABLE)
    if not check.data:
        raise ApiError(400, "no_changes", "Send at least one field to change.")
    check.string("name", max_length=150)
    check.string("description", max_length=5000, allow_empty=True)
    check.date("start_date")
    check.date("end_date")
    check.integer("allocated_hours", minimum=1)
    check.money("budget")
    if check.has("manager_id"):
        _check_manager(check.data["manager_id"], check.errors)
    check.raise_if_errors()

    changes: Record = dict(check.cleaned)
    if check.has("manager_id"):
        changes["manager_id"] = check.data["manager_id"]

    if "start_date" in changes or "end_date" in changes:
        _check_dates(project["id"], changes.get("start_date", project["start_date"]),
                     changes.get("end_date", project["end_date"]))
    if "name" in changes and _name_taken(changes["name"], project["id"]):
        raise ApiError(409, "name_taken", "Another project already has this name.",
                       {"name": "Already in use."})

    # [PROJECT HOURS CAP HERE]
    # How: allocated_hours can't be lowered below the hours already assigned.
    # Why: allocated_hours is the project's total hour budget, and hour
    #      assignments are checked against it. Lowering it underneath existing
    #      assignments would leave the project over its own limit.
    if "allocated_hours" in changes:
        used = assigned_hours(project["id"])
        if Decimal(changes["allocated_hours"]) < used:
            raise ApiError(409, "below_assigned_hours",
                           f"{used} hours are already assigned; allocated_hours can't be lower.",
                           {"allocated_hours": f"Must be at least {used}."})

    if check.has("active_milestone_id"):
        milestone_id = check.data["active_milestone_id"]
        if milestone_id is not None:
            milestone = store.get("milestones", milestone_id) if isinstance(milestone_id, str) else None
            if (milestone is None or milestone["project_id"] != project["id"]
                    or milestone.get("is_archived") or milestone["status"] != "active"):
                raise ApiError(400, "validation_error", "Some fields are invalid.",
                               {"active_milestone_id": "Must be an active milestone of this project."})
        changes["active_milestone_id"] = milestone_id

    # [MANAGER HANDOVER HERE]
    # How: When an admin moves a project to a different manager, future hours
    #      booked for the old manager's team on this project are released.
    # Why: Hours can only be assigned to the project manager's own team, and
    #      the old team can no longer see the project after the handover.
    if "manager_id" in changes and changes["manager_id"] != project["manager_id"]:
        new_manager = changes["manager_id"]
        release_future_assignments(actor, lambda a: (
            a["project_id"] == project["id"]
            and (store.get("users", a["user_id"]) or {}).get("manager_id") != new_manager))

    changes["updated_at"] = now_iso()
    updated = store.update(TABLE, project["id"], changes)
    record_audit(actor, "update", "project", project["id"], project, updated)
    return serialize_project(updated, actor)


# [PROJECT STATUS CHANGES HERE]
# How: complete (manager or admin) and abandon (admin only) set the status
#      and archive the project in one step; archive (admin, via DELETE) archives
#      without changing status; restore (admin) un-archives and sets the
#      status back to active. Each change writes its own audit action and
#      releases future booked hours.
# Why: The data model says a project is archived automatically when it's
#      completed or abandoned, only admins abandon or delete, and restoring
#      means un-archiving. Restoring to "active" avoids a project that is
#      visible again but still marked finished.
def _close_project(actor: Record, project: Record, status: str | None, action: str) -> Record:
    """
    Archive a project, optionally setting a final status.

    Args:
        actor: The acting user.
        project: The stored project.
        status: "completed" or "abandoned", or None to keep the current status.
        action: The audit action to record.

    Returns:
        The updated project.
    """
    timestamp = now_iso()
    changes: Record = {"is_archived": True, "archived_at": timestamp, "updated_at": timestamp}
    if status:
        changes["status"] = status
    updated = store.update(TABLE, project["id"], changes)
    record_audit(actor, action, "project", project["id"], project, updated)
    release_future_assignments(actor, lambda a: a["project_id"] == project["id"])
    return updated


def complete_project(actor: Record, project_id: str) -> Record:
    """
    Mark a project completed (manager or admin).

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The updated project, serialized for the actor.
    """
    project = get_managed_project(actor, project_id)
    return serialize_project(_close_project(actor, project, "completed", "complete"), actor)


def abandon_project(actor: Record, project_id: str) -> Record:
    """
    Mark a project abandoned (admins only).

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The updated project, serialized for the actor.
    """
    require_role(actor, ADMIN)
    project = get_managed_project(actor, project_id)
    return serialize_project(_close_project(actor, project, "abandoned", "abandon"), actor)


def archive_project(actor: Record, project_id: str) -> Record:
    """
    Archive (soft-delete) a project (admins only).

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The updated project, serialized for the actor.
    """
    require_role(actor, ADMIN)
    project = get_visible_project(actor, project_id)
    if project.get("is_archived"):
        raise ApiError(409, "already_archived", "This project is already archived.")
    return serialize_project(_close_project(actor, project, None, "archive"), actor)


def restore_project(actor: Record, project_id: str) -> Record:
    """
    Restore an archived project and set it back to active (admins only).

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The updated project, serialized for the actor.
    """
    require_role(actor, ADMIN)
    project = get_visible_project(actor, project_id)
    if not project.get("is_archived"):
        raise ApiError(409, "not_archived", "This project isn't archived.")
    manager = store.get("users", project["manager_id"])
    if manager is None or manager.get("is_archived"):
        raise ApiError(409, "manager_archived",
                       "This project's manager is archived. Restore the manager first.")
    updated = store.update(TABLE, project["id"], {
        "is_archived": False, "archived_at": None, "status": "active", "updated_at": now_iso()})
    record_audit(actor, "restore", "project", project["id"], project, updated)
    return serialize_project(updated, actor)
