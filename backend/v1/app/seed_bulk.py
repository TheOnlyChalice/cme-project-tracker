"""
A large, realistic set of demo data (about 1,000 records).

Generated from a fixed random seed, so the same people, projects, and
bookings come out every time, and every record follows the app's rules.
"""

import math
import random
from datetime import date, timedelta
from typing import Any

Record = dict[str, Any]

FIRST_NAMES = [
    "Alex", "Blake", "Cameron", "Dana", "Elliot", "Frankie", "Gabriel", "Harper", "Isla", "Jesse",
    "Kai", "Logan", "Marisol", "Nico", "Olivia", "Parker", "Rafael", "Sasha", "Tomas", "Uma",
    "Valentina", "Wes", "Ximena", "Yusuf", "Zara", "Amara", "Bruno", "Chloe", "Dmitri", "Esme",
    "Felix", "Grace", "Hugo", "Ines", "Jonah", "Keira", "Leo", "Maya", "Noah", "Omar",
]
LAST_NAMES = [
    "Anderson", "Bennett", "Castillo", "Dubois", "Edwards", "Fischer", "Garcia", "Hughes", "Ibrahim", "Jensen",
    "Kowalski", "Lopez", "Morales", "Nakamura", "Okafor", "Petrov", "Quinn", "Ramirez", "Silva", "Tanaka",
    "Usman", "Vargas", "Walsh", "Xu", "Yamamoto", "Zimmerman", "Adeyemi", "Byrne", "Chandra", "Delgado",
]

# (department manager title, employee titles, project names)
DEPARTMENTS = [
    ("Product Engineering Manager", ["Backend Developer", "Frontend Developer", "QA Engineer", "Mobile Developer"],
     ["Checkout Rebuild", "Partner API", "Customer Notifications"]),
    ("Cloud Platform Manager", ["Cloud Engineer", "Site Reliability Engineer", "DevOps Engineer"],
     ["Kubernetes Upgrade", "Disaster Recovery Drill", "Cost Optimization Program"]),
    ("Data Manager", ["Data Engineer", "Data Analyst", "Analytics Engineer"],
     ["Sales Data Warehouse", "Churn Prediction Model", "Executive Reporting Suite"]),
    ("Information Security Manager", ["Security Engineer", "Security Analyst", "Identity Engineer"],
     ["Single Sign-On Rollout", "Vendor Risk Review", "Phishing Awareness Program"]),
    ("Marketing Operations Manager", ["Marketing Analyst", "Content Strategist", "Web Developer"],
     ["Website Relaunch", "Spring Campaign", "Brand Refresh"]),
    ("Finance Systems Manager", ["Financial Analyst", "ERP Specialist", "Business Analyst"],
     ["Expense Tool Migration", "Quarter-End Automation", "Budget Planning Portal"]),
    ("IT Operations Manager", ["IT Support Specialist", "Systems Administrator", "Network Engineer"],
     ["Laptop Refresh", "Office Network Upgrade", "Service Desk Revamp"]),
    ("People Operations Manager", ["HR Specialist", "Recruiter", "Learning Designer"],
     ["Recruiting Pipeline Upgrade", "Leadership Training", "Benefits Portal Update"]),
]

MILESTONE_PATTERNS = [
    ("Discovery", "Agree the scope and success measures", ["Scope document", "Stakeholder sign-off"]),
    ("Design", "Design the solution and review it with users", ["Design review", "Prototype"]),
    ("Build", "Build and test the solution", ["Working build", "Test results"]),
    ("Pilot", "Trial with a small group and fix issues", ["Pilot report"]),
    ("Rollout", "Release to everyone and hand over", ["Release notes", "Training session"]),
]

TEAM_SIZE = 8
WEEKS_BACK = 12
WEEKS_AHEAD = 8


# [ACME: BULK DEMO DATA HERE]
# How: Builds 8 more managers (one per department), 64 employees, 24 projects
#      (two active and one completed per manager), 3-5 milestones each, and
#      several hundred weekly bookings across the last 12 and next 8 weeks.
#      A fixed seed makes the output identical every run. While booking, it
#      tracks each person's weekly total so no one goes over 40 hours, only
#      books people onto their own manager's projects, keeps every booking
#      inside its milestone's dates, and sets each project's allocated hours
#      and budget from what was booked. The mix deliberately includes
#      overdue milestones, projects nearly out of hours, over-budget work,
#      quiet projects, and projects with no budget.
# Why: Your request to simulate a real-world environment: about 1,000
#      records gives the dashboards, timeline, heat map, filters, and paging
#      something realistic to show, while every record still passes the same
#      rules a real user's changes must pass.
def bulk_specs(today: date) -> tuple[list[Record], list[Record]]:
    """
    Generate the bulk demo users and projects.

    Args:
        today: The current company date (dates are relative to it).

    Returns:
        (users, projects) in the same shapes the seed module uses.
    """
    rng = random.Random(20261014)  # nosec B311 - repeatable demo data, not security
    this_monday = today - timedelta(days=today.weekday())
    users: list[Record] = []
    projects: list[Record] = []
    booked: dict[tuple[str, int], int] = {}
    names_used: set[str] = set()
    salaries: dict[str, int] = {}

    def unique_name(index: int) -> tuple[str, str]:
        """Pick a first and last name not used yet."""
        step = 0
        while True:
            first = FIRST_NAMES[(index * 7 + step) % len(FIRST_NAMES)]
            last = LAST_NAMES[(index * 11 + step * 3) % len(LAST_NAMES)]
            if f"{first} {last}" not in names_used:
                names_used.add(f"{first} {last}")
                return first, last
            step += 1

    managers: list[str] = []
    for d, (title, _, _) in enumerate(DEPARTMENTS):
        username = f"mgr{d + 4:03d}"
        first, last = unique_name(100 + d)
        salaries[username] = rng.randrange(115, 151) * 1000
        users.append({"username": username, "first_name": first, "last_name": last, "role": "manager",
                      "job_title": title, "salary": str(salaries[username]), "manager": None})
        managers.append(username)

    teams: dict[str, list[str]] = {}
    number = 9
    for d, (_, titles, _) in enumerate(DEPARTMENTS):
        team = []
        for _ in range(TEAM_SIZE):
            username = f"emp{number:03d}"
            first, last = unique_name(number)
            salaries[username] = rng.randrange(68, 121) * 1000
            users.append({"username": username, "first_name": first, "last_name": last, "role": "employee",
                          "job_title": rng.choice(titles), "salary": str(salaries[username]),
                          "manager": managers[d]})
            team.append(username)
            number += 1
        teams[managers[d]] = team

    def split(start: date, end: date, count: int) -> list[tuple[date, date]]:
        """Divide a date range into back-to-back pieces of random length."""
        weights = [rng.uniform(0.7, 1.4) for _ in range(count)]
        total_days = (end - start).days + 1
        pieces, cursor = [], start
        for i, weight in enumerate(weights):
            length = max(5, round(total_days * weight / sum(weights)))
            piece_end = end if i == count - 1 else min(cursor + timedelta(days=length - 1), end - timedelta(days=count - i - 1))
            pieces.append((cursor, piece_end))
            cursor = piece_end + timedelta(days=1)
        return pieces

    for d, (_, _, names) in enumerate(DEPARTMENTS):
        manager = managers[d]
        for p, name in enumerate(names):
            kind = "completed" if p == 2 else "active"
            if kind == "completed":
                start = today - timedelta(days=rng.randint(150, 220))
                end = today - timedelta(days=rng.randint(14, 45))
            elif p == 0:
                start = today - timedelta(days=rng.randint(25, 75))
                end = today + timedelta(days=rng.randint(30, 110))
            else:
                start = today - timedelta(days=rng.randint(-14, 30))
                end = start + timedelta(days=rng.randint(70, 150))
            idle = kind == "active" and (d, p) in {(2, 1), (6, 0)}
            count = rng.randint(3, 5)
            patterns = MILESTONE_PATTERNS if count == 5 else rng.sample(MILESTONE_PATTERNS, count)
            if count < 5:
                patterns = [m for m in MILESTONE_PATTERNS if m in patterns]
            milestones = []
            for (title, goal, deliverables), (m_start, m_end) in zip(patterns, split(start, end, count)):
                if kind == "completed" or (m_end < today and rng.random() < 0.82):
                    status = "completed"
                else:
                    status = "active"
                milestones.append((title, goal, deliverables, m_start.isoformat(), m_end.isoformat(), status))

            hours: list[tuple[str, int, int, str]] = []
            team = teams[manager]
            for week in range(-WEEKS_BACK, WEEKS_AHEAD + 1):
                if idle and week >= 0:
                    continue
                monday = this_monday + timedelta(weeks=week)
                for m_index, (_, _, _, m_start, m_end, _) in enumerate(milestones, 1):
                    if not (monday <= date.fromisoformat(m_end) and monday + timedelta(days=6) >= date.fromisoformat(m_start)):
                        continue
                    for person in rng.sample(team, rng.randint(2, 4)):
                        want = rng.choice([4, 6, 8, 10, 12, 16, 20])
                        free = 40 - booked.get((person, week), 0)
                        amount = min(want, free)
                        if amount < 2:
                            continue
                        booked[(person, week)] = booked.get((person, week), 0) + amount
                        hours.append((person, m_index, week, str(amount)))
                    break

            total_hours = sum(int(h[3]) for h in hours)
            factor = rng.choice([1.04, 1.3, 1.5, 1.8, 2.2])
            allocated = max(40, math.ceil(total_hours * factor / 10) * 10)
            labor = sum(int(h[3]) * salaries[h[0]] / 2080 for h in hours)
            budget_factor = rng.choice([0.85, 1.15, 1.4, 1.7, None])
            budget = None if budget_factor is None or not labor else str(round(labor * budget_factor / 1000) * 1000)
            projects.append({
                "key": f"bulk-{d}-{p}", "name": name, "manager": manager,
                "description": f"{name} for the {DEPARTMENTS[d][0].replace(' Manager', '')} team.",
                "start": start.isoformat(), "end": end.isoformat(),
                "allocated_hours": allocated, "budget": budget,
                "status": "completed" if kind == "completed" else "active",
                "archived": kind == "completed",
                "idle_days": 12 if idle else None,
                "milestones": milestones, "hours": hours,
            })
    return users, projects

