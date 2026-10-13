"""Free up future hours when the work they were booked for goes away."""

from typing import Any, Callable

from app import clock
from app.audit import record_audit
from app.store import store
from app.utils import now_iso

Record = dict[str, Any]


# [FUTURE HOURS RELEASE HERE]
# How: When a project or milestone is completed, abandoned, or archived, or an
#      employee moves to a different manager, every hour assignment it affects
#      in a FUTURE week is archived (with an audit entry). The current and past
#      weeks are left alone.
# Why: Without this, finished or cancelled work would keep using up employees'
#      40 weekly hours, so managers couldn't book them elsewhere. Hours already
#      in the current or past weeks stay, because they reflect work that was
#      planned and is used for cost reporting.
def release_future_assignments(actor: Record | None,
                               predicate: Callable[[Record], bool]) -> int:
    """
    Archive matching hour assignments in weeks after the current one.

    Args:
        actor: The user whose action caused the release.
        predicate: Selects which assignments are affected.

    Returns:
        How many assignments were released.
    """
    this_week = clock.current_week_start().isoformat()
    affected = store.find("hour_assignments", lambda a: (
        a["week_start"] > this_week and predicate(a)), where={"is_archived": False})
    timestamp = now_iso()
    for assignment in affected:
        updated = store.update("hour_assignments", assignment["id"],
                               {"is_archived": True, "archived_at": timestamp,
                                "updated_at": timestamp})
        record_audit(actor, "archive", "hour_assignment", assignment["id"], assignment, updated)
    return len(affected)
