"""
Moving milestone dates as a group.

Used when a milestone's end date changes (later milestones follow it) and
when a project's start date changes (all open milestones follow it).
"""

from datetime import date, timedelta
from typing import Any

from app import clock
from app.audit import record_audit
from app.responses import ApiError
from app.store import store
from app.utils import now_iso

Record = dict[str, Any]


def shift_date(iso_day: str, days: int) -> str:
    """
    Move a YYYY-MM-DD date by a number of days.

    Args:
        iso_day: The date.
        days: Days to add (negative moves earlier).

    Returns:
        The new date as YYYY-MM-DD.
    """
    return (date.fromisoformat(iso_day) + timedelta(days=days)).isoformat()


def days_between(earlier: str, later: str) -> int:
    """
    Count days from one date to another.

    Args:
        earlier: The first date (YYYY-MM-DD).
        later: The second date (YYYY-MM-DD).

    Returns:
        later minus earlier, in days (negative if later is before earlier).
    """
    return (date.fromisoformat(later) - date.fromisoformat(earlier)).days


def open_milestones(project_id: str) -> list[Record]:
    """
    List a project's milestones that can still move, in sequence order.

    Args:
        project_id: The project's ID.

    Returns:
        Active, unarchived milestones.
    """
    rows = store.find("milestones", where={"project_id": project_id, "status": "active", "is_archived": False})
    return sorted(rows, key=lambda m: m["sequence"])


def _stray_hours(milestone_id: str, start: str, end: str) -> tuple[list[Record], list[Record]]:
    """
    Find booked hours in weeks a milestone would no longer cover.

    Args:
        milestone_id: The milestone.
        start: Proposed start date.
        end: Proposed end date.

    Returns:
        (future-week bookings that can be released, current/past-week bookings that can't).
    """
    start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
    this_week = clock.current_week_start().isoformat()
    strays = store.find("hour_assignments", lambda a: not (
        date.fromisoformat(a["week_start"]) <= end_day
        and date.fromisoformat(a["week_start"]) + timedelta(days=6) >= start_day),
        where={"milestone_id": milestone_id, "is_archived": False})
    future = [a for a in strays if a["week_start"] > this_week]
    locked = [a for a in strays if a["week_start"] <= this_week]
    return future, locked


# [DATE SHIFT CHECK HERE]
# How: Before anything is saved, every planned milestone move is checked: it
#      must stay on or after the project start, must end on or before the
#      project end (unless "extend the project" was ticked, in which case the
#      new end date is worked out), and must not strand hours booked in the
#      current or past weeks (those weeks are locked).
# Why: All the checks happen first, so the change is all-or-nothing: either
#      every milestone moves, or nothing moves and the message explains why.
def check_plan(plan: list[tuple[Record, str, str]], project_start: str, project_end: str,
               extend_project: bool) -> str | None:
    """
    Validate a set of milestone moves.

    Args:
        plan: (milestone, new start, new end) for each milestone that changes.
        project_start: The project's start date (after any change).
        project_end: The project's end date (after any change).
        extend_project: Whether the project end may be pushed out to fit.

    Returns:
        A new project end date if one is needed, otherwise None.

    Raises:
        ApiError: If a milestone would start before the project, end after it
                  (without extending), or strand locked hours.
    """
    too_early = [m["name"] for m, start, _ in plan if start < project_start]
    if too_early:
        raise ApiError(409, "milestones_before_project_start",
                       "These milestones would start before the project does: " + ", ".join(too_early) + ".",
                       {"milestones": too_early})
    latest_end = max((end for _, _, end in plan), default=project_end)
    new_project_end = None
    if latest_end > project_end:
        if not extend_project:
            over = days_between(project_end, latest_end)
            names = [m["name"] for m, _, end in plan if end > project_end]
            raise ApiError(409, "milestones_past_project_end",
                           f"These milestones would end {over} days after the project: {', '.join(names)}. "
                           "Tick 'extend the project end date' or choose other dates.",
                           {"milestones": names, "days_over": over})
        new_project_end = latest_end
    for milestone, start, end in plan:
        _, locked = _stray_hours(milestone["id"], start, end)
        if locked:
            weeks = ", ".join(sorted({a["week_start"] for a in locked}))
            raise ApiError(409, "hours_outside_dates",
                           f"'{milestone['name']}' has hours in this week or earlier ({weeks}) that would fall "
                           "outside its new dates. Those weeks can't change.")
    return new_project_end


# [DATE SHIFT APPLY HERE]
# How: Saves each milestone's new dates with its own audit entry, and
#      releases any future-week hours that now fall outside its dates (also
#      audited), returning how many were released.
# Why: Hours booked for a week the milestone no longer covers would make no
#      sense, and releasing them gives those people their time back to be
#      booked elsewhere.
def apply_plan(actor: Record, plan: list[tuple[Record, str, str]]) -> tuple[list[Record], int]:
    """
    Save a validated set of milestone moves.

    Args:
        actor: The acting user.
        plan: (milestone, new start, new end) for each milestone.

    Returns:
        (the updated milestones, number of hour bookings released).
    """
    updated_rows: list[Record] = []
    released = 0
    for milestone, start, end in plan:
        future, _ = _stray_hours(milestone["id"], start, end)
        timestamp = now_iso()
        for booking in future:
            freed = store.update("hour_assignments", booking["id"],
                                 {"is_archived": True, "archived_at": timestamp, "updated_at": timestamp})
            record_audit(actor, "archive", "hour_assignment", booking["id"], booking, freed)
            released += 1
        if (start, end) == (milestone["start_date"], milestone["end_date"]):
            continue
        updated = store.update("milestones", milestone["id"],
                               {"start_date": start, "end_date": end, "updated_at": timestamp})
        record_audit(actor, "update", "milestone", milestone["id"], milestone, updated)
        updated_rows.append(updated)
    return updated_rows, released


def summary(rows: list[Record]) -> list[Record]:
    """
    Describe moved milestones for an API response.

    Args:
        rows: Updated milestones.

    Returns:
        {id, name, start_date, end_date} for each.
    """
    return [{"id": m["id"], "name": m["name"], "start_date": m["start_date"], "end_date": m["end_date"]}
            for m in rows]
