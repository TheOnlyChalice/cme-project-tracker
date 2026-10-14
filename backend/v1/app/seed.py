"""Starter data so the API is usable as soon as it starts."""

import os
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from app import clock
from app.passwords import hash_password
from app.seed_bulk import bulk_specs
from app.store import store
from app.utils import now_iso

# [SEED DATA HERE]
# How: On startup, starter and demo records are added with fixed IDs, dated
#      relative to today. Each record is only added if its ID isn't already
#      there, so new demo data can be added to an existing database without
#      touching anything people have changed. The unit tests load only the
#      small "core" set so their expected numbers stay stable.
#      The password comes from the DEV_SEED_PASSWORD environment variable,
#      with a dev-only default.
# Why: Only an admin can create users, so the very first admin has to exist
#      already. Seeding runs only when the users table is empty: in memory
#      that's every restart; in PostgreSQL it's just the first start, after
#      which the data persists. Fixed IDs (uuid5) keep the demo data identical
#      everywhere. All starter users sign in with DEV_SEED_PASSWORD (default
#      ChangeMe123); change these passwords before real use.
SEED_NAMESPACE = uuid.UUID("6f1c2a52-8d1e-4c43-9a57-4f3d2b9e7a10")
DEFAULT_SEED_PASSWORD = "ChangeMe123"  # nosec B105 - dev-only default, override with env var

CORE_USERS: list[dict[str, Any]] = [
    {"username": "adm001", "first_name": "Ada", "last_name": "Admin", "role": "admin",
     "job_title": "Platform Administrator", "salary": "150000", "manager": None},
    {"username": "mgr001", "first_name": "Morgan", "last_name": "Reyes", "role": "manager",
     "job_title": "Engineering Manager", "salary": "130000", "manager": None},
    {"username": "mgr002", "first_name": "Priya", "last_name": "Shah", "role": "manager",
     "job_title": "Infrastructure Manager", "salary": "128000", "manager": None},
    {"username": "emp001", "first_name": "Sam", "last_name": "Lee", "role": "employee",
     "job_title": "Software Engineer", "salary": "95000", "manager": "mgr001"},
    {"username": "emp002", "first_name": "Jordan", "last_name": "Kim", "role": "employee",
     "job_title": "QA Engineer", "salary": "88000", "manager": "mgr001"},
    {"username": "emp003", "first_name": "Taylor", "last_name": "Brooks", "role": "employee",
     "job_title": "Systems Engineer", "salary": "92000", "manager": "mgr002"},
]

# [DEMO DATA HERE]
# How: Extra people and projects that show off more of the app: a third
#      manager and team, an employee split across two projects, someone fully
#      free, a project going quiet (inactive warning, auto-archives in a few
#      days), a project with no milestones, and finished work (one completed,
#      one abandoned) that only admins can see.
# Why: A demo is much more convincing when every feature has something real
#      to show, without needing to set it all up by hand first.
DEMO_USERS: list[dict[str, Any]] = [
    {"username": "mgr003", "first_name": "Diego", "last_name": "Alvarez", "role": "manager",
     "job_title": "Security Manager", "salary": "125000", "manager": None},
    {"username": "emp004", "first_name": "Riley", "last_name": "Chen", "role": "employee",
     "job_title": "Frontend Developer", "salary": "90000", "manager": "mgr001"},
    {"username": "emp005", "first_name": "Avery", "last_name": "Patel", "role": "employee",
     "job_title": "Network Engineer", "salary": "91000", "manager": "mgr002"},
    {"username": "emp006", "first_name": "Casey", "last_name": "Nguyen", "role": "employee",
     "job_title": "Security Analyst", "salary": "89000", "manager": "mgr003"},
    {"username": "emp007", "first_name": "Jamie", "last_name": "Ortiz", "role": "employee",
     "job_title": "Data Analyst", "salary": "86000", "manager": "mgr003"},
    {"username": "emp008", "first_name": "Quinn", "last_name": "Foster", "role": "employee",
     "job_title": "DevOps Engineer", "salary": "97000", "manager": "mgr003"},
]

# Kept for anything that imported the old name.
SEED_USERS = CORE_USERS


def seed_id(username: str) -> str:
    """
    Return the fixed ID for a seed record.

    Args:
        username: The seed record's key, e.g. "adm001" or "project:portal".

    Returns:
        A UUID string that is the same on every restart.
    """
    return str(uuid.uuid5(SEED_NAMESPACE, username))


def seed_data(include_demo: bool = True, include_bulk: bool | None = None) -> None:
    """
    Add any starter, demo, and bulk records that are missing.

    Args:
        include_demo: Whether to add the hand-written demo people and projects.
        include_bulk: Whether to add the ~1,000-record bulk set; by default
                      on with the demo data unless DEMO_BULK_DATA=false.
    """
    if include_bulk is None:
        include_bulk = include_demo and os.getenv("DEMO_BULK_DATA", "true").lower() != "false"
    with store.transaction():
        # Two Lambda copies starting together must not both seed the database.
        store.lock_named("seed")
        users = CORE_USERS + (DEMO_USERS if include_demo else [])
        projects = _project_specs(include_demo)
        if include_bulk:
            bulk_users, bulk_projects = bulk_specs(clock.today())
            users += bulk_users
            projects += bulk_projects
        _add_missing_users(users)
        _add_missing_projects(projects)


def _add_missing_users(users: list[dict[str, Any]]) -> None:
    """Add seed users whose IDs aren't in the store yet, managers first."""
    existing = {u["id"] for u in store.find("users")}
    missing = [u for u in users if seed_id(u["username"]) not in existing]
    if not missing:
        return
    password_hash = hash_password(os.getenv("DEV_SEED_PASSWORD", DEFAULT_SEED_PASSWORD))
    timestamp = now_iso()
    for seed in missing:
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
            "token_version": 0,
            "failed_login_count": 0,
            "locked_until": None,
            "is_archived": False,
            "archived_at": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        })


def _project_specs(include_demo: bool) -> list[dict[str, Any]]:
    """
    Describe the seed projects, with dates relative to today.

    Args:
        include_demo: Whether to include the extra demo projects.

    Returns:
        Project specs with their milestones and booked hours.
    """
    today = clock.today()

    def day(offset: int) -> str:
        """Date relative to today, as YYYY-MM-DD."""
        return (today + timedelta(days=offset)).isoformat()

    core = [
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
    if not include_demo:
        return core
    demo = [
        {"key": "mobile", "name": "Mobile App Launch", "manager": "mgr001",
         "description": "Launch ACME's first mobile app for iOS and Android.",
         "start": day(-10), "end": day(60), "allocated_hours": 800, "budget": "90000",
         "milestones": [
             ("UX design", "Design every screen and test with users",
              ["Clickable prototype", "Usability report"], day(-10), day(10), "active"),
             ("App build", "Build the app features",
              ["Login and dashboard", "Offline support"], day(11), day(45), "active"),
             ("Store release", "Publish to both app stores",
              ["Store listings", "Release notes"], day(46), day(60), "active"),
         ],
         # emp001 is also on the portal project: 30 + 10 = a full 40-hour week.
         "hours": [("emp001", 1, 0, "10"), ("emp004", 1, 0, "25"), ("emp004", 1, 1, "30"),
                   ("emp002", 1, 1, "10")]},
        {"key": "security", "name": "Security Compliance Audit", "manager": "mgr003",
         "description": "Pass the annual security audit and fix every finding.",
         "start": day(-40), "end": day(25), "allocated_hours": 500, "budget": "60000",
         "milestones": [
             ("Policy review", "Update security policies",
              ["Updated policy handbook"], day(-40), day(-15), "completed"),
             ("Penetration testing", "Test every public system",
              ["Test report", "Findings list"], day(-14), day(10), "active"),
             ("Remediation", "Fix every high and critical finding",
              ["Fixes deployed", "Auditor sign-off"], day(11), day(25), "active"),
         ],
         "hours": [("emp006", 2, -1, "30"), ("emp006", 2, 0, "35"), ("emp007", 2, 0, "20"),
                   ("emp006", 3, 2, "20")]},
        {"key": "analytics", "name": "Analytics Dashboard", "manager": "mgr003",
         "description": "Give leadership a live view of sales and support numbers.",
         "start": day(-50), "end": day(40), "allocated_hours": 400, "budget": "40000",
         "idle_days": 11,
         "milestones": [
             ("Data model", "Agree the metrics and build the data model",
              ["Metric definitions"], day(-50), day(15), "active"),
             ("Dashboards", "Build and share the dashboards",
              ["Sales dashboard", "Support dashboard"], day(16), day(40), "active"),
         ],
         "hours": []},
        {"key": "onboarding", "name": "New Hire Onboarding Revamp", "manager": "mgr002",
         "description": "Redesign the first two weeks for new hires.",
         "start": day(-5), "end": day(70), "allocated_hours": 200, "budget": None,
         "milestones": [], "hours": []},
        {"key": "legacy", "name": "Legacy CRM Retirement", "manager": "mgr002",
         "description": "Move customer records off the old CRM and switch it off.",
         "start": day(-120), "end": day(-20), "allocated_hours": 300, "budget": "30000",
         "status": "completed", "archived": True,
         "milestones": [
             ("Export data", "Copy every record to the new CRM",
              ["Data export"], day(-120), day(-60), "completed"),
             ("Shut down CRM", "Switch off the old system",
              ["Shutdown sign-off"], day(-59), day(-20), "completed"),
         ],
         "hours": []},
        {"key": "kiosk", "name": "Office Kiosk Pilot", "manager": "mgr001",
         "description": "Trial self-service check-in kiosks in the lobby.",
         "start": day(-45), "end": day(30), "allocated_hours": 150, "budget": "15000",
         "status": "abandoned", "archived": True,
         "milestones": [
             ("Hardware trial", "Test two kiosk models",
              ["Trial report"], day(-45), day(0), "active"),
         ],
         "hours": []},
    ]
    return core + demo


def _add_missing_projects(projects: list[dict[str, Any]]) -> None:
    """Add seed projects, milestones, and hours whose IDs aren't present yet."""
    week = clock.current_week_start()
    now = now_iso()
    known = {table: {row["id"] for row in store.find(table)}
             for table in ("projects", "milestones", "hour_assignments")}

    def monday(weeks: int) -> str:
        """Monday relative to the current week, as YYYY-MM-DD."""
        return (week + timedelta(weeks=weeks)).isoformat()

    for spec in projects:
        project_id = seed_id("project:" + spec["key"])
        idle = spec.get("idle_days")
        stamp = (f"{(clock.today() - timedelta(days=idle)).isoformat()}T09:00:00+00:00" if idle else now)
        milestone_ids = [(seed_id(f"milestone:{spec['key']}:{number}"), m[5])
                         for number, m in enumerate(spec["milestones"], 1)]
        if project_id not in known["projects"]:
            archived = spec.get("archived", False)
            active = next((mid for mid, status in milestone_ids if status == "active"), None)
            # The project goes in first because milestones point to it. Its link
            # to the active milestone is checked when the transaction commits.
            store.insert("projects", {
                "id": project_id, "name": spec["name"], "description": spec["description"],
                "start_date": spec["start"], "end_date": spec["end"],
                "allocated_hours": spec["allocated_hours"],
                "budget": Decimal(spec["budget"]) if spec["budget"] else None,
                "manager_id": seed_id(spec["manager"]),
                "active_milestone_id": None if archived else active,
                "status": spec.get("status", "active"), "is_archived": archived,
                "archived_at": now if archived else None,
                "created_by": seed_id("adm001"), "created_at": stamp, "updated_at": stamp,
            })
        for number, (name, goal, deliverables, start, end, status) in enumerate(spec["milestones"], 1):
            if milestone_ids[number - 1][0] in known["milestones"]:
                continue
            store.insert("milestones", {
                "id": milestone_ids[number - 1][0], "project_id": project_id, "sequence": number,
                "name": name, "goal": goal, "deliverables": deliverables,
                "start_date": start, "end_date": end, "status": status,
                "completed_at": stamp if status == "completed" else None,
                "is_archived": False, "archived_at": None,
                "created_at": stamp, "updated_at": stamp,
            })
        for username, milestone_number, week_offset, hours in spec["hours"]:
            hours_id = seed_id(f"hours:{spec['key']}:{username}:{milestone_number}:{week_offset}")
            if hours_id in known["hour_assignments"]:
                continue
            store.insert("hour_assignments", {
                "id": hours_id,
                "user_id": seed_id(username),
                "milestone_id": milestone_ids[milestone_number - 1][0],
                "project_id": project_id, "week_start": monday(week_offset),
                "hours": Decimal(hours), "assigned_by": seed_id(spec["manager"]),
                "is_archived": False, "archived_at": None,
                "created_at": stamp, "updated_at": stamp,
            })
