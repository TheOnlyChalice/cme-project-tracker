"""Roles and the rules for who can see and change what."""

from typing import Any

from app.responses import ApiError

Record = dict[str, Any]

ADMIN = "admin"
MANAGER = "manager"
EMPLOYEE = "employee"
ROLES = (ADMIN, MANAGER, EMPLOYEE)

# [ACME: ROLE HIERARCHY HERE]
# How: Each role gets a rank, and a check passes if the user's rank is at
#      least the required one.
# Why: The requirements say Admin inherits Manager, which inherits Employee.
#      Ranking means "managers and up" is one comparison, so admins
#      automatically get every manager permission without repeating rules.
ROLE_RANK = {EMPLOYEE: 1, MANAGER: 2, ADMIN: 3}


def has_role(user: Record, minimum: str) -> bool:
    """
    Check whether a user's role is at least the given role.

    Args:
        user: The acting user.
        minimum: The lowest role allowed.

    Returns:
        True if the user meets or exceeds the role.
    """
    return ROLE_RANK.get(user.get("role", ""), 0) >= ROLE_RANK[minimum]


def require_role(user: Record, minimum: str) -> None:
    """
    Stop the request unless the user has at least the given role.

    Args:
        user: The acting user.
        minimum: The lowest role allowed.

    Raises:
        ApiError: 403 if the user's role is too low.
    """
    if not has_role(user, minimum):
        raise ApiError(403, "forbidden", "You don't have permission to do this.")


def is_admin(user: Record) -> bool:
    """
    Check whether a user is an admin.

    Args:
        user: The acting user.

    Returns:
        True for admins.
    """
    return user.get("role") == ADMIN


# [ACME: USER VISIBILITY HERE]
# How: Admins see everyone, including archived users. Managers see themselves
#      and the employees who report to them. Employees see only themselves.
# Why: Matches the role rules: a manager's "team" is the people reporting to
#      them, and employees can only access their own personal data. Archived
#      users are admin-only because only admins see archived items.
def can_view_user(viewer: Record, target: Record) -> bool:
    """
    Decide whether one user may see another user's record.

    Args:
        viewer: The acting user.
        target: The user being looked at.

    Returns:
        True if the viewer may see the target.
    """
    if is_admin(viewer):
        return True
    if target.get("is_archived"):
        return False
    if viewer["id"] == target["id"]:
        return True
    return viewer.get("role") == MANAGER and target.get("manager_id") == viewer["id"]


# [ACME: PROJECT VISIBILITY HERE]
# How: Admins see every project, including completed, abandoned, and archived
#      ones. Managers see the active projects they manage. Employees see the
#      active projects managed by their own manager (their team's projects).
# Why: Directly follows the role rules: only admins see archived, completed,
#      or abandoned work, and a "team" is the employees under a manager.
def can_view_project(viewer: Record, project: Record) -> bool:
    """
    Decide whether a user may see a project.

    Args:
        viewer: The acting user.
        project: The project.

    Returns:
        True if the viewer may see it.
    """
    if is_admin(viewer):
        return True
    if project.get("is_archived") or project.get("status") != "active":
        return False
    if viewer.get("role") == MANAGER:
        return project.get("manager_id") == viewer["id"]
    return bool(viewer.get("manager_id")) and project.get("manager_id") == viewer.get("manager_id")


# [ACME: PROJECT MANAGEMENT RIGHTS HERE]
# How: The project's own manager or any admin may change it.
# Why: "Each project has one manager", and admins can do every manager action.
def can_manage_project(viewer: Record, project: Record) -> bool:
    """
    Decide whether a user may change a project and its milestones and hours.

    Args:
        viewer: The acting user.
        project: The project.

    Returns:
        True for admins and the project's manager.
    """
    return is_admin(viewer) or (viewer.get("role") == MANAGER
                                and project.get("manager_id") == viewer["id"])
