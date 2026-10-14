"""Write and read the audit log."""

from typing import Any

from app.store import store
from app.utils import new_id, now_iso

Record = dict[str, Any]

AUDIT_ACTIONS = ("create", "update", "archive", "restore",
                 "assign_role", "assign_team", "complete", "abandon")

# [AUDIT REDACTION HERE]
# How: Listed fields are replaced with "[changed]" in audit entries.
# Why: The audit log must never hold password hashes. It still records that a
#      password changed, which is the part admins need.
REDACTED_FIELDS = frozenset({"password_hash"})

# Bookkeeping fields that change on every edit and add only noise to the log.
IGNORED_FIELDS = frozenset({"updated_at", "token_version", "failed_login_count", "locked_until"})


def _diff(before: Record | None, after: Record | None) -> dict[str, dict[str, Any]]:
    """
    List the fields that differ between two versions of a record.

    Args:
        before: The record before the change (None for creations).
        after: The record after the change.

    Returns:
        {field: {"before": old, "after": new}} for each changed field.
    """
    old = before or {}
    new = after or {}
    changes: dict[str, dict[str, Any]] = {}
    for field in sorted(set(old) | set(new)):
        if field in IGNORED_FIELDS or old.get(field) == new.get(field):
            continue
        if field in REDACTED_FIELDS:
            changes[field] = {"before": "[changed]" if field in old else None,
                              "after": "[changed]"}
        else:
            changes[field] = {"before": old.get(field), "after": new.get(field)}
    return changes


# [AUDIT LOG HERE]
# How: Every service function that changes data calls record_audit() with the
#      acting user, the action, and the record before and after. Only the
#      changed fields are stored, and entries are written to an append-only
#      table that can't be edited or deleted.
# Why: Admins rely on the audit log to see who changed what and when. Putting
#      it in one shared function, used from the very first feature, means no
#      change can be missed, and every entry has the same shape.
def record_audit(actor: Record | None, action: str, entity_type: str, entity_id: str,
                 before: Record | None, after: Record | None) -> Record:
    """
    Write one audit log entry.

    Args:
        actor: The user who made the change (None for system actions).
        action: One of AUDIT_ACTIONS.
        entity_type: e.g. "user", "project", "milestone".
        entity_id: The ID of the changed record.
        before: The record before the change.
        after: The record after the change.

    Returns:
        The stored audit entry.
    """
    if action not in AUDIT_ACTIONS:
        raise ValueError(f"Unknown audit action: {action}")
    entry = {
        "id": new_id(),
        "actor_id": actor["id"] if actor else None,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "changes": _diff(before, after),
        "created_at": now_iso(),
    }
    return store.insert("audit_log", entry)



# Item types that belong to a project. Their entries live in that project's
# own audit log, never in the general one.
PROJECT_ENTITY_TYPES = ("project", "milestone", "hour_assignment")


def _filtered(filters: dict[str, str], allowed: Any) -> dict[str, Any]:
    """
    Filter, sort, and page audit entries.

    Args:
        filters: actor_id, action, entity_type, entity_id, from, to, limit, offset.
        allowed: A function deciding which entries belong in this log at all.

    Returns:
        {"total": count, "limit": n, "offset": n, "entries": [...]}.
    """
    start = filters.get("from")
    end = filters.get("to")

    def matches(entry: Record) -> bool:
        """Decide whether an entry belongs here and passes every filter."""
        if not allowed(entry):
            return False
        for key in ("actor_id", "action", "entity_type", "entity_id"):
            if filters.get(key) and entry[key] != filters[key]:
                return False
        day = entry["created_at"][:10]
        if start and day < start:
            return False
        if end and day > end:
            return False
        return True

    exact = {key: filters[key] for key in ("actor_id", "action", "entity_type", "entity_id")
             if filters.get(key)}
    entries = sorted(store.find("audit_log", matches, where=exact),
                     key=lambda e: e["created_at"], reverse=True)
    limit = _bounded_int(filters.get("limit"), default=100, low=1, high=500)
    offset = _bounded_int(filters.get("offset"), default=0, low=0, high=10**9)
    return {"total": len(entries), "limit": limit, "offset": offset,
            "entries": entries[offset:offset + limit]}


# [GENERAL AUDIT LOG HERE]
# How: The audit log in the sidebar lists every change EXCEPT those about
#      projects, milestones, and booked hours: account creation, profile and
#      password changes, role and manager changes, archiving and restoring
#      people. Filters: person, action, item, date range, with paging.
# Why: Your rule: the general log is for company-wide account activity, and
#      project activity has its own log inside each project, so neither is
#      buried under the other.
def list_audit(filters: dict[str, str]) -> dict[str, Any]:
    """
    List general (non-project) audit entries, newest first.

    Args:
        filters: actor_id, action, entity_type, entity_id, from, to, limit, offset.

    Returns:
        A page of entries with the total count.
    """
    return _filtered(filters, lambda e: e["entity_type"] not in PROJECT_ENTITY_TYPES)


# [PROJECT AUDIT LOG HERE]
# How: Each project's audit log collects entries about the project itself,
#      any of its milestones (archived ones included), and any hours booked
#      on it (removed ones included). Which project an entry belongs to is
#      worked out when the log is read, from the IDs of those items.
# Why: Admins can see the full history of one project in one place. Working
#      it out at read time means old entries never have to be rewritten,
#      which keeps the audit log truly unchangeable.
def list_project_audit(project_id: str, filters: dict[str, str]) -> dict[str, Any]:
    """
    List one project's audit entries (project, milestones, hours), newest first.

    Args:
        project_id: The project's ID.
        filters: actor_id, action, entity_type, from, to, limit, offset.

    Returns:
        A page of entries with the total count.
    """
    ids = {
        "project": {project_id},
        "milestone": {m["id"] for m in store.find("milestones", where={"project_id": project_id})},
        "hour_assignment": {a["id"] for a in store.find("hour_assignments", where={"project_id": project_id})},
    }
    return _filtered(filters, lambda e: e["entity_id"] in ids.get(e["entity_type"], set()))


def _bounded_int(value: str | None, default: int, low: int, high: int) -> int:
    """
    Parse a paging number, falling back to a default and clamping to a range.

    Args:
        value: The raw query value.
        default: Used when the value is missing or not a number.
        low: Smallest allowed value.
        high: Largest allowed value.

    Returns:
        The parsed, clamped number.
    """
    try:
        number = int(value) if value is not None else default
    except ValueError:
        number = default
    return max(low, min(high, number))
