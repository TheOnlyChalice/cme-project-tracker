"""
Automatic housekeeping: archiving projects that have gone quiet.

A project with no activity for INACTIVITY_ARCHIVE_DAYS (default 14) is
archived automatically. Projects get an "inactive" warning flag from
INACTIVITY_WARNING_DAYS (default 10), so managers see it coming.
"""

import logging
import os
import time
from datetime import date
from typing import Any

from app import clock
from app.audit import record_audit
from app.store import store
from app.utils import now_iso

logger = logging.getLogger(__name__)

Record = dict[str, Any]

INACTIVITY_ARCHIVE_DAYS = int(os.getenv("INACTIVITY_ARCHIVE_DAYS", "14"))
INACTIVITY_WARNING_DAYS = int(os.getenv("INACTIVITY_WARNING_DAYS", "10"))
AUTO_RUN_SECONDS = 3600

_last_auto_run = 0.0


# [PROJECT ACTIVITY HERE]
# How: A project's last activity is the most recent change to the project
#      itself, any of its milestones, or any hours booked on it, using the
#      created_at/updated_at timestamps every record already has.
# Why: "No activity" needs one clear definition. Every edit, completed
#      milestone, or booking updates one of those timestamps, so no separate
#      activity tracking is needed and nothing can be missed.
def last_activity(project: Record) -> str:
    """
    Find when anything about a project last changed.

    Args:
        project: The stored project.

    Returns:
        The latest timestamp (ISO string).
    """
    stamps = [project["created_at"], project["updated_at"]]
    for table in ("milestones", "hour_assignments"):
        for row in store.find(table, where={"project_id": project["id"]}):
            stamps.extend([row["created_at"], row["updated_at"]])
    return max(stamps)


def _has_upcoming_hours(project: Record, today: date) -> bool:
    """
    Check whether hours are booked for this week or later.

    Args:
        project: The stored project.
        today: The current company date.

    Returns:
        True if work is planned from the current week onwards.
    """
    this_week = clock.week_start_of(today).isoformat()
    return bool(store.find("hour_assignments", lambda a: a["week_start"] >= this_week,
                           where={"project_id": project["id"], "is_archived": False}))


def days_inactive(project: Record, today: date) -> int | None:
    """
    Count whole days since a project's last activity.

    Args:
        project: The stored project.
        today: The current company date.

    Returns:
        Days of inactivity, or None if work is booked from this week on
        (planned work counts as activity).
    """
    if _has_upcoming_hours(project, today):
        return None
    last_day = date.fromisoformat(last_activity(project)[:10])
    return max((today - last_day).days, 0)


# [AUTO-ARCHIVE HERE]
# How: Every active, unarchived project idle for 14+ days (and with no hours
#      booked from this week on) is archived. Each one gets an "archive" audit
#      entry with no actor, which the audit log shows as "System". Admins can
#      restore them as usual.
# Why: Your requirement: projects with no activity for two weeks archive
#      themselves, so stale work drops off managers' and employees' lists.
#      Booked hours count as activity because that work is still planned.
def archive_inactive_projects(actor: Record | None = None) -> list[Record]:
    """
    Archive every project that has been inactive too long.

    Args:
        actor: The admin who ran it by hand, or None for the automatic run.

    Returns:
        The projects that were archived, as {id, name, days_inactive}.
    """
    today = clock.today()
    archived: list[Record] = []
    for project in store.find("projects", where={"status": "active", "is_archived": False}):
        idle = days_inactive(project, today)
        if idle is None or idle < INACTIVITY_ARCHIVE_DAYS:
            continue
        timestamp = now_iso()
        updated = store.update("projects", project["id"], {
            "is_archived": True, "archived_at": timestamp, "updated_at": timestamp})
        record_audit(actor, "archive", "project", project["id"], project, updated)
        archived.append({"id": project["id"], "name": project["name"], "days_inactive": idle})
    if archived:
        logger.info("Auto-archived %d inactive projects", len(archived))
    return archived


# [AUTO-RUN THROTTLE HERE]
# How: Before handling a request, each Lambda copy runs the archive check if
#      it hasn't in the last hour, inside its own transaction and under a
#      database lock, so two copies never run it at once. Failures are logged
#      and never block the request.
# Why: The workshop's AWS permissions don't allow creating a scheduled job
#      (EventBridge), so ordinary traffic drives the check instead. Once an
#      hour is plenty for a two-week rule, and the cost is a few quick queries.
def maybe_run_maintenance() -> None:
    """Run the inactivity check if this Lambda copy hasn't recently."""
    global _last_auto_run  # pylint: disable=global-statement
    now = time.monotonic()
    if _last_auto_run and now - _last_auto_run < AUTO_RUN_SECONDS:
        return
    _last_auto_run = now
    try:
        with store.transaction():
            store.lock_named("maintenance")
            archive_inactive_projects()
    except Exception:  # pylint: disable=broad-except
        logger.exception("Automatic maintenance failed")


def reset_auto_run() -> None:
    """Forget the last automatic run (used by tests)."""
    global _last_auto_run  # pylint: disable=global-statement
    _last_auto_run = 0.0
