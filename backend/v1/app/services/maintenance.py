"""
Inactivity tracking and the admin's on-demand clean-up.

Projects with no activity for INACTIVITY_WARNING_DAYS (default 10) get an
"inactive" warning flag. Nothing is archived automatically: an admin can run
the clean-up on demand, which archives projects idle for
INACTIVITY_ARCHIVE_DAYS (default 14).
"""

import logging
import os
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


# [ACME: PROJECT ACTIVITY HERE]
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


# [ACME: INACTIVE CLEAN-UP HERE]
# How: Only when an admin runs it (POST /admin/maintenance), every active,
#      unarchived project idle for 14+ days (and with no hours booked from
#      this week on) is archived, each with an "archive" audit entry under
#      that admin's name. Admins can restore them as usual.
# Why: Automatic archiving was removed as too risky: nothing disappears
#      without a person deciding to. The warning flag still tells managers
#      a project has gone quiet.
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
