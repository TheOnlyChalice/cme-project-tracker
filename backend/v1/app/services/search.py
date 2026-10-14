"""Quick search across projects, milestones, and people."""

from typing import Any

from app.permissions import can_view_project, can_view_user, is_admin
from app.store import store

Record = dict[str, Any]

MIN_LENGTH = 2
PER_GROUP = 6


def _rank(query: str, name: str, others: list[str]) -> int | None:
    """
    Score how well a record matches (lower is better), or None for no match.

    Args:
        query: The lowercased search text.
        name: The record's main name.
        others: Other text fields to search.

    Returns:
        0 name starts with it, 1 a word in the name starts with it,
        2 the name contains it, 3 another field contains it, else None.
    """
    lowered = name.lower()
    if lowered.startswith(query):
        return 0
    if any(word.startswith(query) for word in lowered.split()):
        return 1
    if query in lowered:
        return 2
    if any(query in (text or "").lower() for text in others):
        return 3
    return None


def _top(rows: list[tuple[int, str, Record]]) -> tuple[list[Record], int]:
    """
    Sort scored matches and keep the best few.

    Args:
        rows: (score, name, result) for every match.

    Returns:
        (the best PER_GROUP results, the total number of matches).
    """
    rows.sort(key=lambda row: (row[0], row[1].lower()))
    return [row[2] for row in rows[:PER_GROUP]], len(rows)


# [ACME: QUICK SEARCH HERE]
# How: One query searches three things at once and returns the best few of
#      each: projects (name, description), milestones (name, goal,
#      deliverables), and people (name, username, email, job title). Matches
#      are ranked: names that start with the text first, then names with a
#      word starting with it, then names containing it, then other fields.
#      Each group goes through the usual visibility rules first, so a search
#      can never reveal something the user couldn't open anyway.
# Why: People remember things by different handles ("Sam", "pen testing",
#      "migration"); one box that finds any of them is the fastest way around
#      the app. Showing only the top few per group keeps the dropdown short.
def quick_search(actor: Record, text: str | None) -> Record:
    """
    Search projects, milestones, and people the actor may see.

    Args:
        actor: The acting user.
        text: What was typed (at least 2 characters to search).

    Returns:
        {"query", "projects", "milestones", "people", "totals"}.
    """
    query = (text or "").strip().lower()
    empty = {"query": query, "projects": [], "milestones": [], "people": [],
             "totals": {"projects": 0, "milestones": 0, "people": 0}}
    if len(query) < MIN_LENGTH:
        return empty

    admin = is_admin(actor)
    visible = {p["id"]: p for p in store.find("projects", lambda p: can_view_project(actor, p))}

    project_rows = []
    for project in visible.values():
        score = _rank(query, project["name"], [project.get("description")])
        if score is not None:
            project_rows.append((score, project["name"], {
                "id": project["id"], "name": project["name"], "status": project["status"],
                "is_archived": project["is_archived"], "end_date": project["end_date"]}))

    milestone_rows = []
    for milestone in store.find("milestones", lambda m: m["project_id"] in visible and (admin or not m["is_archived"])):
        score = _rank(query, milestone["name"], [milestone.get("goal")] + list(milestone.get("deliverables") or []))
        if score is not None:
            project = visible[milestone["project_id"]]
            milestone_rows.append((score, milestone["name"], {
                "id": milestone["id"], "name": milestone["name"], "status": milestone["status"],
                "sequence": milestone["sequence"], "end_date": milestone["end_date"],
                "project_id": project["id"], "project_name": project["name"]}))

    people_rows = []
    for person in store.find("users", lambda u: can_view_user(actor, u) and (admin or not u["is_archived"])):
        name = f"{person['first_name']} {person['last_name']}"
        score = _rank(query, name, [person["username"], person["email"], person.get("job_title")])
        if score is not None:
            people_rows.append((score, name, {
                "id": person["id"], "name": name, "username": person["username"], "role": person["role"],
                "job_title": person.get("job_title"), "is_archived": person["is_archived"]}))

    projects, project_total = _top(project_rows)
    milestones, milestone_total = _top(milestone_rows)
    people, people_total = _top(people_rows)
    return {"query": query, "projects": projects, "milestones": milestones, "people": people,
            "totals": {"projects": project_total, "milestones": milestone_total, "people": people_total}}
