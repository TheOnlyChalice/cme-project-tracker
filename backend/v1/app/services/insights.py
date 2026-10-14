"""
Reporting that answers the business questions: project health, risk,
resource utilization, and cost versus budget.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app import clock
from app.permissions import EMPLOYEE, MANAGER, can_view_project, is_admin
from app.services.hours import CAPACITY, week_param
from app.services.maintenance import INACTIVITY_WARNING_DAYS, days_inactive, last_activity
from app.services.milestones import milestone_chain
from app.store import store

Record = dict[str, Any]

# [RISK THRESHOLDS HERE]
# How: The numbers that decide when a project is flagged live in one place.
# Why: "At risk" isn't defined in the requirements, so these are our working
#      rules. Keeping them together makes them easy to explain, and easy to
#      change if the business defines risk differently.
DEADLINE_WARNING_DAYS = 14
SCHEDULE_GAP_POINTS = 25
BUDGET_WARNING_PERCENT = 90
WORK_HOURS_PER_YEAR = Decimal("2080")


def _percent(part: Decimal, whole: Decimal) -> Decimal | None:
    """
    Calculate a percentage rounded to one decimal place.

    Args:
        part: The portion.
        whole: The total.

    Returns:
        The percentage, or None if the total is zero.
    """
    if not whole:
        return None
    return (part * 100 / whole).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


# [LABOR COST HERE]
# How: Each assignment costs hours x the employee's hourly rate, where the
#      hourly rate is salary / 2,080 (40 hours x 52 weeks). "To date" counts
#      weeks that have started; "committed" counts every assigned week.
# Why: The project budget is a set number, and the requirements suggest it
#      can grow with team salary. Comparing cost to date with the budget
#      answers "consumed vs planned", and committed cost warns early when
#      planned hours will push a project over. Only totals are returned to
#      non-admins, so no one's individual salary is exposed.
def _labor_costs(project_id: str, this_week: str) -> tuple[Decimal, Decimal, int]:
    """
    Total a project's labor cost.

    Args:
        project_id: The project's ID.
        this_week: The current week's Monday (YYYY-MM-DD).

    Returns:
        (cost to date, committed cost, number of assigned people missing a salary).
    """
    to_date = committed = Decimal("0")
    missing_salary: set[str] = set()
    for a in store.find("hour_assignments", where={"project_id": project_id, "is_archived": False}):
        salary = (store.get("users", a["user_id"]) or {}).get("salary")
        if salary is None:
            missing_salary.add(a["user_id"])
            continue
        cost = a["hours"] * Decimal(salary) / WORK_HOURS_PER_YEAR
        committed += cost
        if a["week_start"] <= this_week:
            to_date += cost
    cents = Decimal("0.01")
    return to_date.quantize(cents), committed.quantize(cents), len(missing_salary)


# [AT-RISK RULES HERE]
# How: A project gets a flag (with a plain-English reason) for each of these:
#      past its end date; an active milestone past its end date; ending within
#      14 days with milestones still open; time elapsed more than 25 points
#      ahead of milestones completed; no milestones after it has started;
#      committed labor cost over budget; or 90%+ of allocated hours used.
#      Any flag means the project is at risk.
# Why: Each flag points at something a manager can act on, and returning the
#      reasons (not just a yes/no) tells them what to fix first.
def project_health(project: Record, viewer: Record, today: date) -> Record:
    """
    Summarize a project's progress, hours, cost, and risk.

    Args:
        project: The stored project.
        viewer: The user who will receive the summary.
        today: The current company date.

    Returns:
        A health summary, with cost fields only for managers and admins.
    """
    this_week = clock.week_start_of(today).isoformat()
    milestones = store.find("milestones", where={"project_id": project["id"], "is_archived": False})
    total = len(milestones)
    completed = sum(1 for m in milestones if m["status"] == "completed")
    overdue = [m for m in milestones
               if m["status"] == "active" and m["end_date"] < today.isoformat()]

    start, end = date.fromisoformat(project["start_date"]), date.fromisoformat(project["end_date"])
    span = (end - start).days or 1
    elapsed_pct = min(max(Decimal((today - start).days) * 100 / span, Decimal(0)), Decimal(100))
    completion_pct = _percent(Decimal(completed), Decimal(total)) or Decimal(0)
    days_left = (end - today).days

    hours = sum((a["hours"] for a in store.find(
        "hour_assignments", where={"project_id": project["id"], "is_archived": False})), Decimal("0"))
    hours_pct = _percent(hours, Decimal(project["allocated_hours"]))
    cost_to_date, cost_committed, missing_salary = _labor_costs(project["id"], this_week)
    budget = project.get("budget")

    flags: list[Record] = []
    is_open = project["status"] == "active" and not project.get("is_archived")
    if is_open:
        if days_left < 0:
            flags.append({"code": "past_end_date", "params": {"days": -days_left},
                          "message": f"The project ended {-days_left} days ago but is still active."})
        if overdue:
            names = ", ".join(m["name"] for m in overdue)
            flags.append({"code": "overdue_milestone", "params": {"names": names},
                          "message": f"Overdue milestones: {names}."})
        if 0 <= days_left <= DEADLINE_WARNING_DAYS and completed < total:
            flags.append({"code": "deadline_near", "params": {"days": days_left, "open": total - completed},
                          "message": f"{days_left} days left with {total - completed} milestones open."})
        if total and elapsed_pct - completion_pct > SCHEDULE_GAP_POINTS:
            flags.append({"code": "behind_schedule",
                          "params": {"elapsed": round(elapsed_pct), "complete": round(completion_pct)},
                          "message": f"{elapsed_pct:.0f}% of the time has passed but only "
                                     f"{completion_pct:.0f}% of milestones are complete."})
        if not total and today > start:
            flags.append({"code": "no_milestones", "params": {},
                          "message": "The project has started but has no milestones."})
        if budget is not None and cost_committed > Decimal(budget):
            # [NO BUDGET LEAK IN FLAGS HERE]
            # How: Employees get the over-budget warning without any amounts.
            # Why: Employees aren't shown budgets or costs anywhere else, so a
            #      risk message must not reveal them either.
            if viewer.get("role") == EMPLOYEE:
                flags.append({"code": "over_budget", "params": {},
                              "message": "Forecast labor cost exceeds the budget."})
            else:
                flags.append({"code": "over_budget",
                              "params": {"cost": float(cost_committed), "budget": float(Decimal(budget))},
                              "message": f"Committed labor cost {cost_committed} exceeds the budget {budget}."})
        if hours_pct is not None and hours_pct >= BUDGET_WARNING_PERCENT:
            flags.append({"code": "hours_nearly_used", "params": {"percent": float(hours_pct)},
                          "message": f"{hours_pct}% of allocated hours are assigned."})

        idle = days_inactive(project, today)
        if idle is not None and idle >= INACTIVITY_WARNING_DAYS:
            flags.append({"code": "inactive", "params": {"days": idle},
                          "message": f"No activity for {idle} days."})

    summary: Record = {
        "project_id": project["id"],
        "name": project["name"],
        "status": project["status"],
        "manager_id": project["manager_id"],
        "start_date": project["start_date"],
        "end_date": project["end_date"],
        "days_left": days_left,
        "active_milestone_id": project.get("active_milestone_id"),
        "milestones_total": total,
        "milestones_completed": completed,
        "percent_complete": completion_pct,
        "percent_time_elapsed": elapsed_pct.quantize(Decimal("0.1")),
        "allocated_hours": project["allocated_hours"],
        "hours_assigned": hours,
        "percent_hours_assigned": hours_pct,
        "last_activity_at": last_activity(project),
        "at_risk": bool(flags),
        "risk_flags": flags,
    }
    if viewer.get("role") != EMPLOYEE:
        summary.update({
            "budget": budget,
            "labor_cost_to_date": cost_to_date,
            "labor_cost_committed": cost_committed,
            "percent_budget_used": _percent(cost_to_date, Decimal(budget)) if budget else None,
            "employees_missing_salary": missing_salary,
        })
    return summary


def project_overview(actor: Record, query: dict[str, str]) -> list[Record]:
    """
    Health summaries for every project the actor can see.

    Args:
        actor: The acting user.
        query: at_risk=true to keep only flagged projects; include_closed=true
               (admins) to include completed, abandoned, and archived projects.

    Returns:
        Summaries, at-risk projects first, then by end date.
    """
    include_closed = query.get("include_closed", "").lower() == "true" and is_admin(actor)
    today = clock.today()
    projects = store.find("projects", lambda p: can_view_project(actor, p) and (
        include_closed or (p["status"] == "active" and not p.get("is_archived"))))
    summaries = [project_health(p, actor, today) for p in projects]
    if query.get("at_risk", "").lower() == "true":
        summaries = [s for s in summaries if s["at_risk"]]
    summaries.sort(key=lambda s: (not s["at_risk"], s["end_date"]))
    return summaries


# [UTILIZATION HERE]
# How: For each employee the actor can see, total their assigned hours for
#      the week and label them fully_booked (40), partly_booked, or unassigned.
# Why: Answers "how are resources allocated" and "who is over-allocated".
#      Because the 40-hour cap is enforced, no one can be over 40, so the
#      useful question becomes who has spare hours to give.
def utilization(actor: Record, week: str | None) -> Record:
    """
    Show how booked each visible employee is for a week.

    Args:
        actor: The acting user.
        week: Any date in the week, or None for the current week.

    Returns:
        The week and one entry per employee, least-booked first.
    """
    week_start = week_param(week)
    if is_admin(actor):
        people = store.find("users", where={"role": EMPLOYEE, "is_archived": False})
    elif actor.get("role") == MANAGER:
        people = store.find("users", where={"manager_id": actor["id"], "role": EMPLOYEE,
                                            "is_archived": False})
    else:
        people = [actor]

    rows = []
    for person in people:
        assignments = store.find("hour_assignments", where={
            "user_id": person["id"], "week_start": week_start, "is_archived": False})
        assigned = sum((a["hours"] for a in assignments), Decimal("0"))
        by_project: dict[str, Decimal] = {}
        for a in assignments:
            by_project[a["project_id"]] = by_project.get(a["project_id"], Decimal("0")) + a["hours"]
        state = ("fully_booked" if assigned >= CAPACITY
                 else "partly_booked" if assigned > 0 else "unassigned")
        rows.append({
            "user_id": person["id"],
            "username": person["username"],
            "name": f"{person['first_name']} {person['last_name']}",
            "manager_id": person.get("manager_id"),
            "capacity": CAPACITY,
            "assigned": assigned,
            "available": CAPACITY - assigned,
            "percent_booked": _percent(assigned, CAPACITY),
            "state": state,
            "projects": [{"project_id": pid,
                          "project_name": (store.get("projects", pid) or {}).get("name"),
                          "hours": hrs} for pid, hrs in by_project.items()],
        })
    rows.sort(key=lambda r: (r["assigned"], r["name"]))
    return {"week_start": week_start, "employees": rows}


def project_chain(actor: Record, project_id: str) -> list[Record]:
    """
    The ordered milestone dependency chain for a project.

    Args:
        actor: The acting user.
        project_id: The project's ID.

    Returns:
        The chain entries.
    """
    return milestone_chain(actor, project_id, clock.today())



# [PORTFOLIO TIMELINE DATA HERE]
# How: One call returns every project the user can see, with its dates,
#      manager's name, risk flags, and milestones (completed ones included),
#      each milestone marked done, in progress, planned, or overdue.
# Why: The dashboard's timeline draws every project as a lane of milestone
#      bars. Sending it in one response avoids a request per project, and
#      only the manager's name is shared, so employees still can't open
#      other people's records.
def portfolio_timeline(actor: Record) -> list[Record]:
    """
    Projects and their milestones for the portfolio timeline.

    Args:
        actor: The acting user.

    Returns:
        One entry per visible active project, sorted by start date.
    """
    today = clock.today()
    iso_today = today.isoformat()
    lanes = []
    for project in store.find("projects", lambda p: can_view_project(actor, p),
                              where={"status": "active", "is_archived": False}):
        manager = store.get("users", project["manager_id"]) or {}
        health = project_health(project, actor, today)
        milestones = sorted(store.find("milestones", where={"project_id": project["id"], "is_archived": False}),
                            key=lambda m: m["sequence"])
        bars = []
        for m in milestones:
            if m["status"] == "completed":
                state = "done"
            elif m["end_date"] < iso_today:
                state = "overdue"
            elif m["start_date"] > iso_today:
                state = "planned"
            else:
                state = "in_progress"
            bars.append({"id": m["id"], "sequence": m["sequence"], "name": m["name"],
                         "start_date": m["start_date"], "end_date": m["end_date"], "state": state})
        lanes.append({
            "project_id": project["id"], "name": project["name"],
            "start_date": project["start_date"], "end_date": project["end_date"],
            "manager_name": f"{manager.get('first_name', '')} {manager.get('last_name', '')}".strip(),
            "at_risk": health["at_risk"], "risk_flags": health["risk_flags"], "milestones": bars,
        })
    lanes.sort(key=lambda lane: (lane["start_date"], lane["name"]))
    return lanes


# [CAPACITY HEAT MAP DATA HERE]
# How: Runs the weekly utilization for several weeks in a row (default 6,
#      at most 12) and turns it into one row per person with their booked
#      hours for each week.
# Why: The hours heat map shows at a glance who is full, who is free, and
#      when, across upcoming weeks. It reuses utilization(), so the same
#      visibility rules apply: managers see their team, admins everyone,
#      employees only themselves.
def capacity(actor: Record, start: str | None, weeks: str | None) -> Record:
    """
    Booked hours per person for a run of weeks.

    Args:
        actor: The acting user.
        start: Any date in the first week (default: the current week).
        weeks: How many weeks (1-12, default 6).

    Returns:
        {"weeks": [...Mondays], "people": [{user_id, name, username, weeks: [{week_start, hours}]}]}.
    """
    try:
        count = max(1, min(12, int(weeks or 6)))
    except ValueError:
        count = 6
    first = date.fromisoformat(week_param(start))
    mondays = [(first + timedelta(weeks=i)).isoformat() for i in range(count)]
    people: dict[str, Record] = {}
    for monday in mondays:
        for row in utilization(actor, monday)["employees"]:
            person = people.setdefault(row["user_id"], {
                "user_id": row["user_id"], "name": row["name"], "username": row["username"], "weeks": []})
            person["weeks"].append({"week_start": monday, "hours": row["assigned"]})
    ordered = sorted(people.values(), key=lambda p: p["name"])
    return {"weeks": mondays, "capacity": CAPACITY, "people": ordered}
