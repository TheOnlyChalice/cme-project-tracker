"""
Milestone business logic: the smaller projects inside a project.

Routes call these functions; nothing here knows about HTTP requests.
"""

from datetime import date, timedelta
from typing import Any

from app.audit import record_audit
from app.permissions import ADMIN, is_admin, require_role
from app.responses import ApiError
from app.services.hour_release import release_future_assignments
from app.services.projects import close_project, get_managed_project, get_visible_project
from app.store import store
from app.utils import new_id, now_iso
from app.validation import Validator, reject_unknown_fields

Record = dict[str, Any]

TABLE = "milestones"
EDITABLE = ("name", "goal", "deliverables", "start_date", "end_date")


def serialize_milestone(milestone: Record) -> Record:
    """
    Prepare a milestone for an API response.

    Args:
        milestone: The stored milestone.

    Returns:
        The milestone plus the employees who have hours on it.
    """
    # [MILESTONE ASSIGNEES HERE]
    # How: assigned_employee_ids is worked out from active hour assignments.
    # Why: Managers put people on a milestone by assigning them hours, so the
    #      hours are the single source of truth for who works on what.
    data = dict(milestone)
    assignments = store.find("hour_assignments",
                             where={"milestone_id": milestone["id"], "is_archived": False})
    data["assigned_employee_ids"] = sorted({a["user_id"] for a in assignments})
    return data


def get_visible_milestone(actor: Record, milestone_id: str) -> tuple[Record, Record]:
    """
    Fetch a milestone the actor may see, along with its project.

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.

    Returns:
        (milestone, project).

    Raises:
        ApiError: 404 if it doesn't exist or the actor can't see it.
    """
    milestone = store.get(TABLE, milestone_id)
    if milestone is None or (milestone.get("is_archived") and not is_admin(actor)):
        raise ApiError(404, "not_found", "Milestone not found.")
    try:
        project = get_visible_project(actor, milestone["project_id"])
    except ApiError as exc:
        raise ApiError(404, "not_found", "Milestone not found.") from exc
    return milestone, project


def get_managed_milestone(actor: Record, milestone_id: str) -> tuple[Record, Record]:
    """
    Fetch a milestone the actor may change, on an open project.

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.

    Returns:
        (milestone, project).

    Raises:
        ApiError: 404/403/409 as for projects, or 409 if the milestone is archived.
    """
    milestone, project = get_visible_milestone(actor, milestone_id)
    get_managed_project(actor, project["id"])
    if milestone.get("is_archived"):
        raise ApiError(409, "milestone_archived", "Restore this milestone first.")
    return milestone, project


# [MILESTONE DATE RULES HERE]
# How: A milestone's end date can't be before its start date, both must sit
#      inside the project's dates, and an edit can't shrink a milestone so
#      that existing hour assignments fall in weeks it no longer covers.
# Why: The data model requires milestone dates inside the project dates, and
#      hours booked for weeks outside the milestone would make no sense.
def _check_dates(project: Record, start: str, end: str, milestone_id: str | None = None) -> None:
    """
    Validate milestone dates against the project and existing hours.

    Args:
        project: The milestone's project.
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).
        milestone_id: The milestone being edited (None when creating).

    Raises:
        ApiError: 400 for dates out of range, 409 if booked hours fall outside.
    """
    errors: dict[str, str] = {}
    if end < start:
        errors["end_date"] = "Can't be before the start date."
    if start < project["start_date"] or start > project["end_date"]:
        errors["start_date"] = (f"Must be within the project dates "
                                f"({project['start_date']} to {project['end_date']}).")
    if end < project["start_date"] or end > project["end_date"]:
        errors["end_date"] = (f"Must be within the project dates "
                              f"({project['start_date']} to {project['end_date']}).")
    if errors:
        raise ApiError(400, "validation_error", "Some fields are invalid.", errors)
    if milestone_id:
        start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
        stranded = store.find("hour_assignments", lambda a: (
            not (date.fromisoformat(a["week_start"]) <= end_day
                     and date.fromisoformat(a["week_start"]) + timedelta(days=6) >= start_day)),
            where={"milestone_id": milestone_id, "is_archived": False})
        if stranded:
            weeks = ", ".join(sorted({a["week_start"] for a in stranded}))
            raise ApiError(409, "hours_outside_dates",
                           f"Hours are booked for weeks outside the new dates: {weeks}. "
                           "Remove those hours first.")


def list_milestones(actor: Record, project_id: str, query: dict[str, str]) -> list[Record]:
    """
    List a project's milestones in sequence order.

    Args:
        actor: The acting user.
        project_id: The project's ID.
        query: Query parameters: status, include_archived (admins only).

    Returns:
        The milestones, serialized.
    """
    get_visible_project(actor, project_id)
    include_archived = query.get("include_archived", "").lower() == "true" and is_admin(actor)
    status = query.get("status")
    milestones = store.find(TABLE, lambda m: (
        (include_archived or not m.get("is_archived"))
        and (not status or m["status"] == status)), where={"project_id": project_id})
    milestones.sort(key=lambda m: m["sequence"])
    return [serialize_milestone(m) for m in milestones]


def create_milestone(actor: Record, project_id: str, data: Any) -> Record:
    """
    Add a milestone to a project (the project's manager or an admin).

    Args:
        actor: The acting user.
        project_id: The project's ID.
        data: The request body.

    Returns:
        The new milestone, serialized.
    """
    project = get_managed_project(actor, project_id)
    check = Validator(data)
    reject_unknown_fields(check.data, EDITABLE)
    check.string("name", required=True, max_length=150)
    check.string("goal", max_length=2000, allow_empty=True)
    check.string_list("deliverables")
    check.date("start_date", required=True)
    check.date("end_date", required=True)
    check.raise_if_errors()
    _check_dates(project, check.cleaned["start_date"], check.cleaned["end_date"])

    # [MILESTONE SEQUENCE HERE]
    # How: Each new milestone gets the next number in its project (1, 2, 3...),
    #      counting archived milestones so numbers are never reused.
    # Why: The data model asks for a sequential ID per milestone, and the
    #      sequence also defines the milestone order used for the dependency chain.
    existing = store.find(TABLE, where={"project_id": project["id"]})
    sequence = max((m["sequence"] for m in existing), default=0) + 1

    timestamp = now_iso()
    milestone = {
        "id": new_id(),
        "project_id": project["id"],
        "sequence": sequence,
        "name": check.cleaned["name"],
        "goal": check.cleaned.get("goal"),
        "deliverables": check.cleaned.get("deliverables", []),
        "start_date": check.cleaned["start_date"],
        "end_date": check.cleaned["end_date"],
        "status": "active",
        "completed_at": None,
        "is_archived": False,
        "archived_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    store.insert(TABLE, milestone)
    record_audit(actor, "create", "milestone", milestone["id"], None, milestone)

    # [FIRST ACTIVE MILESTONE HERE]
    # How: If the project has no active milestone yet, the new one becomes it.
    # Why: Saves managers a step and means the project always shows what is
    #      currently being worked on once any milestone exists.
    if not project.get("active_milestone_id"):
        updated = store.update("projects", project["id"], {
            "active_milestone_id": milestone["id"], "updated_at": now_iso()})
        record_audit(actor, "update", "project", project["id"], project, updated)
    return serialize_milestone(milestone)


def update_milestone(actor: Record, milestone_id: str, data: Any) -> Record:
    """
    Update a milestone's fields.

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.
        data: The request body with fields to change.

    Returns:
        The updated milestone, serialized.
    """
    milestone, project = get_managed_milestone(actor, milestone_id)
    if milestone["status"] == "completed":
        raise ApiError(409, "milestone_completed", "Completed milestones can't be edited.")
    check = Validator(data)
    reject_unknown_fields(check.data, EDITABLE)
    if not check.data:
        raise ApiError(400, "no_changes", "Send at least one field to change.")
    check.string("name", max_length=150)
    check.string("goal", max_length=2000, allow_empty=True)
    check.string_list("deliverables")
    check.date("start_date")
    check.date("end_date")
    check.raise_if_errors()

    changes: Record = dict(check.cleaned)
    if "start_date" in changes or "end_date" in changes:
        _check_dates(project, changes.get("start_date", milestone["start_date"]),
                     changes.get("end_date", milestone["end_date"]), milestone["id"])
    changes["updated_at"] = now_iso()
    updated = store.update(TABLE, milestone["id"], changes)
    record_audit(actor, "update", "milestone", milestone["id"], milestone, updated)
    return serialize_milestone(updated)


# [ACTIVE MILESTONE ADVANCE HERE]
# How: When the project's active milestone is completed or archived, the next
#      active milestone in sequence order becomes the active one (or none).
# Why: Keeps the project's "current milestone" accurate without the manager
#      having to update it by hand after every milestone.
def _advance_active_milestone(actor: Record, project_id: str, finished_id: str) -> None:
    """
    Move a project's active milestone on if the finished one was active.

    Args:
        actor: The acting user.
        project_id: The project's ID.
        finished_id: The milestone that was completed or archived.
    """
    project = store.get("projects", project_id)
    if not project or project.get("active_milestone_id") != finished_id:
        return
    remaining = store.find(TABLE, where={"project_id": project_id, "status": "active",
                                         "is_archived": False})
    remaining.sort(key=lambda m: m["sequence"])
    next_id = remaining[0]["id"] if remaining else None
    updated = store.update("projects", project_id, {
        "active_milestone_id": next_id, "updated_at": now_iso()})
    record_audit(actor, "update", "project", project_id, project, updated)


def complete_milestone(actor: Record, milestone_id: str) -> Record:
    """
    Mark a milestone completed (the project's manager or an admin).

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.

    Returns:
        The updated milestone, serialized.
    """
    milestone, project = get_managed_milestone(actor, milestone_id)
    if milestone["status"] == "completed":
        raise ApiError(409, "already_completed", "This milestone is already completed.")
    timestamp = now_iso()
    updated = store.update(TABLE, milestone["id"], {
        "status": "completed", "completed_at": timestamp, "updated_at": timestamp})
    record_audit(actor, "complete", "milestone", milestone["id"], milestone, updated)
    release_future_assignments(actor, lambda a: a["milestone_id"] == milestone["id"])
    _advance_active_milestone(actor, project["id"], milestone["id"])

    # [AUTO-COMPLETE PROJECT HERE]
    # How: When the last open milestone of a project is completed, the project
    #      itself is completed and archived in the same step, with its own
    #      "complete" audit entry under the same person. The response says
    #      project_completed: true so the frontend can tell the user.
    # Why: Your rule: finishing every milestone finishes the project. Doing it
    #      in the same transaction means the milestone and project can never
    #      disagree, and managers don't have to complete the project by hand.
    #      Archived milestones don't count, since they were removed from the plan.
    still_open = store.find(TABLE, where={"project_id": project["id"], "status": "active",
                                          "is_archived": False})
    project_completed = False
    if not still_open:
        current = store.get("projects", project["id"])
        close_project(actor, current, "completed", "complete")
        project_completed = True
    return {**serialize_milestone(updated), "project_completed": project_completed}


def archive_milestone(actor: Record, milestone_id: str) -> Record:
    """
    Archive (soft-delete) a milestone (admins only).

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.

    Returns:
        The updated milestone, serialized.
    """
    # [ADMIN-ONLY MILESTONE ARCHIVE HERE]
    # How: Only admins may archive a milestone; managers complete them instead.
    # Why: Your rule: archiving (deleting) is an admin action for every kind
    #      of item, so managers can finish work but not remove it.
    require_role(actor, ADMIN)
    milestone, project = get_managed_milestone(actor, milestone_id)
    timestamp = now_iso()
    updated = store.update(TABLE, milestone["id"], {
        "is_archived": True, "archived_at": timestamp, "updated_at": timestamp})
    record_audit(actor, "archive", "milestone", milestone["id"], milestone, updated)
    release_future_assignments(actor, lambda a: a["milestone_id"] == milestone["id"])
    _advance_active_milestone(actor, project["id"], milestone["id"])
    return serialize_milestone(updated)


def restore_milestone(actor: Record, milestone_id: str) -> Record:
    """
    Restore an archived milestone (admins only).

    Args:
        actor: The acting user.
        milestone_id: The milestone's ID.

    Returns:
        The updated milestone, serialized.
    """
    require_role(actor, ADMIN)
    milestone, project = get_visible_milestone(actor, milestone_id)
    if not milestone.get("is_archived"):
        raise ApiError(409, "not_archived", "This milestone isn't archived.")
    get_managed_project(actor, project["id"])
    updated = store.update(TABLE, milestone["id"], {
        "is_archived": False, "archived_at": None, "updated_at": now_iso()})
    record_audit(actor, "restore", "milestone", milestone["id"], milestone, updated)
    return serialize_milestone(updated)


# [MILESTONE CHAIN HERE]
# How: Milestones are listed in sequence order; each depends on the one
#      before it. A milestone is "blocked" if any earlier milestone is still
#      active, and "overdue" if it's active past its end date.
# Why: The business problem asks for the dependency chain between
#      deliverables. The data model has no explicit dependencies, so the
#      milestone sequence is the chain, which matches how work is planned.
def milestone_chain(actor: Record, project_id: str, today: date) -> list[Record]:
    """
    Describe a project's milestones as an ordered dependency chain.

    Args:
        actor: The acting user.
        project_id: The project's ID.
        today: The current company date.

    Returns:
        One entry per milestone with depends_on_id, blocked, and overdue flags.
    """
    milestones = list_milestones(actor, project_id, {})
    chain: list[Record] = []
    earlier_open = False
    previous_id = None
    for milestone in milestones:
        is_active = milestone["status"] == "active"
        chain.append({
            "id": milestone["id"],
            "sequence": milestone["sequence"],
            "name": milestone["name"],
            "status": milestone["status"],
            "start_date": milestone["start_date"],
            "end_date": milestone["end_date"],
            "depends_on_id": previous_id,
            "blocked": is_active and earlier_open,
            "overdue": is_active and milestone["end_date"] < today.isoformat(),
        })
        earlier_open = earlier_open or is_active
        previous_id = milestone["id"]
    return chain
