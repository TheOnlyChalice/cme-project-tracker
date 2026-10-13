"""Starter data so the API is usable as soon as it starts."""

import os
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from app import clock
from app.passwords import hash_password
from app.store import store
from app.utils import now_iso

# [SEED DATA HERE]
# How: On startup, a few users are added with fixed IDs and usernames: one
#      admin, two managers, and three employees split between them. Two
#      projects follow, with milestones and booked hours dated relative to
#      today: one healthy, and one deliberately at risk (overdue milestone,
#      close deadline, over budget) so the dashboards have something to show.
#      The password comes from the DEV_SEED_PASSWORD environment variable,
#      with a dev-only default.
# Why: In-memory data disappears whenever Lambda or the dev server restarts,
#      and only an admin can create users, so there has to be an admin who
#      already exists. Fixed IDs (uuid5) stay the same across restarts, so
#      the usernames and IDs below always work in the X-User-Id header.
SEED_NAMESPACE = uuid.UUID("6f1c2a52-8d1e-4c43-9a57-4f3d2b9e7a10")
DEFAULT_SEED_PASSWORD = "ChangeMe123"  # nosec B105 - dev-only default, override with env var

SEED_USERS: list[dict[str, Any]] = [
    {"username": "adm001", "first_name": "Ada", "last_name": "Admin", "role": "admin",
     "job_title": "Platform Administrator", "salary": "150000", "manager": None},
    {"username": "mgr001", "first_name": "Morgan", "last_name": "Reyes", "role": "manager",
     "job_title": "Engineering Manager", "salary": "130000", "manager": "adm001"},
    {"username": "mgr002", "first_name": "Priya", "last_name": "Shah", "role": "manager",
     "job_title": "Infrastructure Manager", "salary": "128000", "manager": "adm001"},
    {"username": "emp001", "first_name": "Sam", "last_name": "Lee", "role": "employee",
     "job_title": "Software Engineer", "salary": "95000", "manager": "mgr001"},
    {"username": "emp002", "first_name": "Jordan", "last_name": "Kim", "role": "employee",
     "job_title": "QA Engineer", "salary": "88000", "manager": "mgr001"},
    {"username": "emp003", "first_name": "Taylor", "last_name": "Brooks", "role": "employee",
     "job_title": "Systems Engineer", "salary": "92000", "manager": "mgr002"},
]


def seed_id(username: str) -> str:
    """
    Return the fixed ID for a seed user.

    Args:
        username: The seed user's username.

    Returns:
        A UUID string that is the same on every restart.
    """
    return str(uuid.uuid5(SEED_NAMESPACE, username))


def seed_data() -> None:
    """Add the seed users if the store has no users yet."""
    if store.find("users"):
        return
    password_hash = hash_password(os.getenv("DEV_SEED_PASSWORD", DEFAULT_SEED_PASSWORD))
    timestamp = now_iso()
    for seed in SEED_USERS:
        store.insert("users", {
            "id": seed_id(seed["username"]),
            "username": seed["username"],
            "first_name": seed["first_name"],
            "last_name": seed["last_name"],
            "email": f"{seed['username']}@cme.example.com",
            "password_hash": password_hash,
            "role": seed["role"],
            "job_title": seed["job_title"],
            "salary": Decimal(seed["salary"]),
            "profile_picture_url": None,
            "manager_id": seed_id(seed["manager"]) if seed["manager"] else None,
            "is_archived": False,
            "archived_at": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        })
    _seed_projects()


def _seed_projects() -> None:
    """Add two demo projects with milestones and hour assignments."""
    today = clock.today()
    week = clock.current_week_start()
    timestamp = now_iso()

    def day(offset: int) -> str:
        """Date relative to today, as YYYY-MM-DD."""
        return (today + timedelta(days=offset)).isoformat()

    def monday(weeks: int) -> str:
        """Monday relative to the current week, as YYYY-MM-DD."""
        return (week + timedelta(weeks=weeks)).isoformat()

    projects = [
        {"key": "portal", "name": "Customer Portal Redesign", "manager": "mgr001",
         "description": "Rebuild the customer portal with a responsive design.",
         "start": day(-30), "end": day(90), "allocated_hours": 1200, "budget": "150000",
         "milestones": [
             ("Discovery and requirements", "Agree scope with stakeholders",
              ["Requirements document", "Wireframes"], day(-30), day(-10), "completed"),
             ("Build the new UI", "Ship all redesigned pages",
              ["Responsive layouts", "Accessibility review"], day(-9), day(40), "active"),
             ("Launch", "Move all customers to the new portal",
              ["Release plan", "Customer announcement"], day(41), day(90), "active"),
         ],
         "hours": [("emp001", 2, 0, "30"), ("emp002", 2, 0, "20"), ("emp001", 2, 1, "20")]},
        {"key": "migration", "name": "Data Center Migration", "manager": "mgr002",
         "description": "Move workloads to the cloud and close the old data center.",
         "start": day(-60), "end": day(10), "allocated_hours": 600, "budget": "12000",
         "milestones": [
             ("Inventory servers", "Catalogue every server and its owner",
              ["Server inventory"], day(-60), day(-20), "active"),
             ("Decommission 200 servers", "Decommission 200 servers",
              ["Decommission checklist", "Sign-off from owners"], day(-19), day(10), "active"),
         ],
         "hours": [("emp003", 1, w, "40") for w in range(-8, -2)]
                  + [("emp003", 2, 0, "40"), ("emp003", 2, 1, "40")]},
    ]

    for spec in projects:
        project_id = seed_id("project:" + spec["key"])
        milestone_ids = []
        for number, (name, goal, deliverables, start, end, status) in enumerate(spec["milestones"], 1):
            milestone_id = seed_id(f"milestone:{spec['key']}:{number}")
            milestone_ids.append((milestone_id, status))
            store.insert("milestones", {
                "id": milestone_id, "project_id": project_id, "sequence": number,
                "name": name, "goal": goal, "deliverables": deliverables,
                "start_date": start, "end_date": end, "status": status,
                "completed_at": timestamp if status == "completed" else None,
                "is_archived": False, "archived_at": None,
                "created_at": timestamp, "updated_at": timestamp,
            })
        active = next((mid for mid, status in milestone_ids if status == "active"), None)
        store.insert("projects", {
            "id": project_id, "name": spec["name"], "description": spec["description"],
            "start_date": spec["start"], "end_date": spec["end"],
            "allocated_hours": spec["allocated_hours"], "budget": Decimal(spec["budget"]),
            "manager_id": seed_id(spec["manager"]), "active_milestone_id": active,
            "status": "active", "is_archived": False, "archived_at": None,
            "created_by": seed_id("adm001"), "created_at": timestamp, "updated_at": timestamp,
        })
        for username, milestone_number, week_offset, hours in spec["hours"]:
            store.insert("hour_assignments", {
                "id": seed_id(f"hours:{spec['key']}:{username}:{milestone_number}:{week_offset}"),
                "user_id": seed_id(username),
                "milestone_id": milestone_ids[milestone_number - 1][0],
                "project_id": project_id, "week_start": monday(week_offset),
                "hours": Decimal(hours), "assigned_by": seed_id(spec["manager"]),
                "is_archived": False, "archived_at": None,
                "created_at": timestamp, "updated_at": timestamp,
            })
