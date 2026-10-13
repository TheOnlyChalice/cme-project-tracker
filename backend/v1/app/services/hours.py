"""
Hour assignment business logic: managers booking employees' weekly hours.

Each employee has 40 hours per week, starting fresh at 12:00 AM Monday
(company time). Managers assign those hours to milestones on their projects.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app import clock
from app.audit import record_audit
from app.permissions import EMPLOYEE, MANAGER, can_view_user, is_admin
from app.responses import ApiError
from app.services.milestones import get_visible_milestone
from app.services.projects import assigned_hours, get_managed_project
from app.store import store
from app.utils import new_id, now_iso
from app.validation import Validator, parse_date, reject_unknown_fields

Record = dict[str, Any]

TABLE = "hour_assignments"
CAPACITY = Decimal(clock.WEEKLY_CAPACITY_HOURS)


def user_week_total(user_id: str, week_start: str, exclude_id: str | None = None) -> Decimal:
    """
    Total an employee's assigned hours for one week.

    Args:
        user_id: The employee's ID.
        week_start: The week's Monday (YYYY-MM-DD).
        exclude_id: An assignment to leave out (the one being edited).

    Returns:
        The total hours.
    """
    rows = store.find(TABLE, lambda a: (
        a["user_id"] == user_id and a["week_start"] == week_start
        and not a.get("is_archived") and a["id"] != exclude_id))
    return sum((a["hours"] for a in rows), Decimal("0"))


# [HOUR ASSIGNMENT VISIBILITY HERE]
# How: Admins see all assignments. Managers see assignments on projects they
#      manage and assignments for people on their team. Employees see only
#      their own.
# Why: Employees need to know where their week is going; managers need the
#      full picture for their projects and people; nobody else's schedule leaks.
def can_view_assignment(viewer: Record, assignment: Record) -> bool:
    """
    Decide whether a user may see an hour assignment.

    Args:
        viewer: The acting user.
        assignment: The hour assignment.

    Returns:
        True if the viewer may see it.
    """
    if is_admin(viewer):
        return True
    if assignment.get("is_archived"):
        return False
    if viewer["id"] == assignment["user_id"]:
        return True
    if viewer.get("role") != MANAGER:
        return False
    project = store.get("projects", assignment["project_id"]) or {}
    employee = store.get("users", assignment["user_id"]) or {}
    return project.get("manager_id") == viewer["id"] or employee.get("manager_id") == viewer["id"]


def week_param(value: str | None) -> str:
    """
    Turn an optional date into the Monday of its week.

    Args:
        value: Any date in the week (YYYY-MM-DD), or None for the current week.

    Returns:
        The week's Monday as YYYY-MM-DD.

    Raises:
        ApiError: 400 if the date is invalid.
    """
    if not value:
        return clock.current_week_start().isoformat()
    parsed = parse_date(value)
    if parsed is None:
        raise ApiError(400, "validation_error", "Some fields are invalid.",
                       {"week": "Must be a date in YYYY-MM-DD format."})
    return clock.week_start_of(parsed).isoformat()


def _require_not_past(week_start: str) -> None:
    """
    Stop changes to weeks that have already ended.

    Args:
        week_start: The week's Monday (YYYY-MM-DD).

    Raises:
        ApiError: 409 if the week is before the current week.
    """
    # [PAST WEEKS LOCKED HERE]
    # How: Assignments in weeks before the current one can't be added, changed,
    #      or removed.
    # Why: Past weeks are a record of what was planned and feed the cost
    #      figures. Since hours reset every Monday, only this week and future
    #      weeks are still open for planning.
    if week_start < clock.current_week_start().isoformat():
        raise ApiError(409, "week_closed", "That week has ended and can't be changed.")


# [WEEKLY 40-HOUR CAP HERE]
# How: Before saving, add up the employee's hours for that week across every
#      milestone and project; the new total can't go over 40. The error says
#      how many hours are still free.
# Why: The requirements say every employee has 40 hours a week and managers
#      can't go over it. Checking across all projects is what makes
#      over-allocation impossible rather than just reported.
def _check_capacity(user_id: str, week_start: str, hours: Decimal,
                    exclude_id: str | None = None) -> None:
    """
    Make sure an assignment fits in the employee's 40 weekly hours.

    Args:
        user_id: The employee's ID.
        week_start: The week's Monday (YYYY-MM-DD).
        hours: The hours to add (or the new amount when editing).
        exclude_id: The assignment being edited, if any.

    Raises:
        ApiError: 409 with the remaining hours if the cap would be exceeded.
    """
    booked = user_week_total(user_id, week_start, exclude_id)
    if booked + hours > CAPACITY:
        remaining = CAPACITY - booked
        raise ApiError(409, "weekly_capacity_exceeded",
                       f"This employee has {remaining} of {CAPACITY} hours left in the week "
                       f"of {week_start}.",
                       {"hours": f"At most {remaining} hours can be assigned.",
                        "hours_remaining": remaining})


def _check_project_budget(project: Record, hours: Decimal, exclude_id: str | None = None) -> None:
    """
    Make sure an assignment fits in the project's allocated hours.

    Args:
        project: The project.
        hours: The hours to add (or the new amount when editing).
        exclude_id: The assignment being edited, if any.

    Raises:
        ApiError: 409 with the remaining hours if the project cap would be exceeded.
    """
    # [PROJECT ALLOCATED HOURS CHECK HERE]
    # How: All of a project's assigned hours together can't exceed its
    #      allocated_hours.
    # Why: allocated_hours is the project's total hour budget; enforcing it at
    #      assignment time means a project can never quietly overrun it.
    used = assigned_hours(project["id"], exclude_id)
    if used + hours > Decimal(project["allocated_hours"]):
        remaining = Decimal(project["allocated_hours"]) - used
        raise ApiError(409, "project_hours_exceeded",
                       f"The project has {remaining} of {project['allocated_hours']} "
                       "allocated hours left.",
                       {"hours": f"At most {remaining} hours can be assigned to this project.",
                        "hours_remaining": remaining})


def list_assignments(actor: Record, query: dict[str, str]) -> list[Record]:
    """
    List hour assignments the actor may see, with optional filters.

    Args:
        actor: The acting user.
        query: user_id, project_id, milestone_id, week (any date in the week),
               include_archived (admins only).

    Returns:
        Matching assignments, sorted by week then user.
    """
    include_archived = query.get("include_archived", "").lower() == "true" and is_admin(actor)
    week = week_param(query["week"]) if query.get("week") else None

    def matches(a: Record) -> bool:
        """Decide whether an assignment passes visibility and every filter."""
        if a.get("is_archived") and not include_archived:
            return False
        for key in ("user_id", "project_id", "milestone_id"):
            if query.get(key) and a[key] != query[key]:
                return False
        if week and a["week_start"] != week:
            return False
        return can_view_assignment(actor, a)

    rows = store.find(TABLE, matches)
    rows.sort(key=lambda a: (a["week_start"], a["user_id"]))
    return rows


def create_assignment(actor: Record, data: Any) -> Record:
    """
    Assign some of an employee's weekly hours to a milestone.

    Args:
        actor: The acting user (the project's manager or an admin).
        data: user_id, milestone_id, hours, and optional week_start (any date
              in the week; defaults to the current week).

    Returns:
        The new assignment.
    """
    check = Validator(data)
    reject_unknown_fields(check.data, ("user_id", "milestone_id", "hours", "week_start"))
    check.hours("hours", required=True)
    for field in ("user_id", "milestone_id"):
        if not isinstance(check.data.get(field), str):
            check.errors[field] = "This field is required."
    if check.has("week_start") and parse_date(check.data["week_start"]) is None:
        check.errors["week_start"] = "Must be a date in YYYY-MM-DD format."
    check.raise_if_errors()

    milestone, project = get_visible_milestone(actor, check.data["milestone_id"])
    get_managed_project(actor, project["id"])
    if milestone.get("is_archived") or milestone["status"] != "active":
        raise ApiError(409, "milestone_closed", "Hours can only go to active milestones.")

    # [TEAM-ONLY ASSIGNMENT HERE]
    # How: The employee must be an active employee who reports to the
    #      project's manager.
    # Why: A manager assigns their own team's hours, and employees can only
    #      see their own manager's projects; assigning anyone else would put
    #      them on a project they can't see.
    employee = store.get("users", check.data["user_id"])
    if (employee is None or employee.get("is_archived") or employee["role"] != EMPLOYEE
            or employee.get("manager_id") != project["manager_id"]):
        raise ApiError(400, "validation_error", "Some fields are invalid.",
                       {"user_id": "Must be an active employee on this project manager's team."})

    week_start = week_param(check.data.get("week_start"))
    _require_not_past(week_start)

    # [WEEK INSIDE MILESTONE HERE]
    # How: The week (Monday to Sunday) must overlap the milestone's dates.
    # Why: Booking hours for a week when the milestone isn't running would
    #      be meaningless and would distort the milestone's cost.
    monday = date.fromisoformat(week_start)
    if not (week_start <= milestone["end_date"]
            and (monday + timedelta(days=6)).isoformat() >= milestone["start_date"]):
        raise ApiError(400, "validation_error", "Some fields are invalid.",
                       {"week_start": f"The milestone runs {milestone['start_date']} to "
                                      f"{milestone['end_date']}; pick a week in that range."})

    duplicate = store.find(TABLE, lambda a: (
        a["user_id"] == employee["id"] and a["milestone_id"] == milestone["id"]
        and a["week_start"] == week_start and not a.get("is_archived")))
    if duplicate:
        raise ApiError(409, "already_assigned",
                       "This employee already has hours on this milestone that week. "
                       "Edit that assignment instead.", {"assignment_id": duplicate[0]["id"]})

    hours = check.cleaned["hours"]
    _check_capacity(employee["id"], week_start, hours)
    _check_project_budget(project, hours)

    timestamp = now_iso()
    assignment = {
        "id": new_id(),
        "user_id": employee["id"],
        "milestone_id": milestone["id"],
        "project_id": project["id"],
        "week_start": week_start,
        "hours": hours,
        "assigned_by": actor["id"],
        "is_archived": False,
        "archived_at": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    store.insert(TABLE, assignment)
    record_audit(actor, "create", "hour_assignment", assignment["id"], None, assignment)
    return assignment


def _get_managed_assignment(actor: Record, assignment_id: str) -> tuple[Record, Record]:
    """
    Fetch an open assignment the actor may change.

    Args:
        actor: The acting user.
        assignment_id: The assignment's ID.

    Returns:
        (assignment, project).
    """
    assignment = store.get(TABLE, assignment_id)
    if assignment is None or not can_view_assignment(actor, assignment):
        raise ApiError(404, "not_found", "Hour assignment not found.")
    if assignment.get("is_archived"):
        raise ApiError(409, "assignment_archived", "This hour assignment was removed.")
    project = get_managed_project(actor, assignment["project_id"])
    _require_not_past(assignment["week_start"])
    return assignment, project


def update_assignment(actor: Record, assignment_id: str, data: Any) -> Record:
    """
    Change the hours on an assignment.

    Args:
        actor: The acting user.
        assignment_id: The assignment's ID.
        data: {"hours": number}.

    Returns:
        The updated assignment.
    """
    assignment, project = _get_managed_assignment(actor, assignment_id)
    check = Validator(data)
    reject_unknown_fields(check.data, ("hours",))
    check.hours("hours", required=True)
    check.raise_if_errors()
    hours = check.cleaned["hours"]
    _check_capacity(assignment["user_id"], assignment["week_start"], hours, assignment["id"])
    _check_project_budget(project, hours, assignment["id"])
    updated = store.update(TABLE, assignment["id"], {"hours": hours, "updated_at": now_iso()})
    record_audit(actor, "update", "hour_assignment", assignment["id"], assignment, updated)
    return updated


def remove_assignment(actor: Record, assignment_id: str) -> Record:
    """
    Remove (archive) an assignment, freeing the hours.

    Args:
        actor: The acting user.
        assignment_id: The assignment's ID.

    Returns:
        The archived assignment.
    """
    assignment, _ = _get_managed_assignment(actor, assignment_id)
    timestamp = now_iso()
    updated = store.update(TABLE, assignment["id"], {
        "is_archived": True, "archived_at": timestamp, "updated_at": timestamp})
    record_audit(actor, "archive", "hour_assignment", assignment["id"], assignment, updated)
    return updated


# [AVAILABILITY HERE]
# How: For one employee and week, returns the 40-hour capacity, hours
#      assigned, hours still free, and a breakdown by project and milestone.
# Why: Managers need to see how much of someone's week is left before
#      assigning more, and employees can see where their week is going.
def availability(actor: Record, user_id: str, week: str | None) -> Record:
    """
    Show how an employee's week is booked.

    Args:
        actor: The acting user.
        user_id: The employee's ID.
        week: Any date in the week, or None for the current week.

    Returns:
        Capacity, assigned, available, and a per-milestone breakdown.
    """
    user = store.get("users", user_id)
    if user is None or not can_view_user(actor, user):
        raise ApiError(404, "not_found", "User not found.")
    week_start = week_param(week)
    rows = store.find(TABLE, lambda a: (
        a["user_id"] == user_id and a["week_start"] == week_start and not a.get("is_archived")))
    assigned = sum((a["hours"] for a in rows), Decimal("0"))
    breakdown = []
    for a in rows:
        project = store.get("projects", a["project_id"]) or {}
        milestone = store.get("milestones", a["milestone_id"]) or {}
        breakdown.append({"assignment_id": a["id"], "hours": a["hours"],
                          "project_id": a["project_id"], "project_name": project.get("name"),
                          "milestone_id": a["milestone_id"], "milestone_name": milestone.get("name")})
    return {"user_id": user_id, "week_start": week_start, "capacity": CAPACITY,
            "assigned": assigned, "available": CAPACITY - assigned, "assignments": breakdown}
