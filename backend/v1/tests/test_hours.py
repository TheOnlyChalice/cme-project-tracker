"""Tests for weekly hour assignments and the 40-hour cap."""

from tests.helpers import (LAST_MONDAY, MIGRATION_M2, NEXT_MONDAY, PORTAL, PORTAL_M2, PORTAL_M3,
                           THIS_MONDAY, ApiTestCase, day, uid)


def assignment(user: str, milestone: str = PORTAL_M2, hours: float = 5, week: str | None = None):
    """Build an hour assignment request body."""
    body = {"user_id": uid(user), "milestone_id": milestone, "hours": hours}
    if week:
        body["week_start"] = week
    return body


class HourAssignmentTests(ApiTestCase):
    """Assigning, editing, and removing hours."""

    def extra_milestone(self) -> str:
        """Add a second Portal milestone that overlaps this week; return its ID."""
        return self.ok("POST", f"/projects/{PORTAL}/milestones", "mgr001",
                       {"name": "Accessibility fixes", "start_date": day(-2),
                        "end_date": day(20)}, expected=201)["id"]

    def test_manager_assigns_hours_to_this_week_by_default(self) -> None:
        created = self.ok("POST", "/hour-assignments", "mgr001",
                          assignment("emp002", hours=10, week=NEXT_MONDAY), expected=201)
        self.assertEqual(created["week_start"], NEXT_MONDAY)
        self.assertEqual(created["project_id"], PORTAL)
        default = self.ok("POST", "/hour-assignments", "mgr001",
                          assignment("emp002", milestone=PORTAL_M3, hours=1), expected=400)
        self.assertIn("week_start", default["error"]["details"])  # M3 starts later

    def test_any_date_maps_to_its_monday(self) -> None:
        created = self.ok("POST", "/hour-assignments", "mgr001",
                          assignment("emp002", hours=4, week="2026-10-22"), expected=201)
        self.assertEqual(created["week_start"], NEXT_MONDAY)

    def test_forty_hour_cap_across_projects(self) -> None:
        extra = self.extra_milestone()
        err = self.error("POST", "/hour-assignments", "mgr001", 409, "weekly_capacity_exceeded",
                         body=assignment("emp001", milestone=extra, hours=10.5))
        self.assertEqual(err["details"]["hours_remaining"], 10)
        self.ok("POST", "/hour-assignments", "mgr001",
                assignment("emp001", milestone=extra, hours=10), expected=201)
        avail = self.ok("GET", f"/users/{uid('emp001')}/availability", "mgr001")
        self.assertEqual(avail["available"], 0)
        self.assertEqual(avail["week_start"], THIS_MONDAY)

    def test_project_allocated_hours_cap(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"allocated_hours": 75})
        self.error("POST", "/hour-assignments", "mgr001", 409, "project_hours_exceeded",
                   body=assignment("emp002", hours=6, week=NEXT_MONDAY))

    def test_only_the_project_managers_team(self) -> None:
        self.error("POST", "/hour-assignments", "mgr001", 400, "validation_error",
                   body=assignment("emp003"))
        self.error("POST", "/hour-assignments", "mgr002", 404, body=assignment("emp003"))
        self.error("POST", "/hour-assignments", "emp001", 403, body=assignment("emp002"))
        self.error("POST", "/hour-assignments", "mgr002", 400, "validation_error",
                   body=assignment("mgr002", milestone=MIGRATION_M2))

    def test_validation_and_rules(self) -> None:
        err = self.error("POST", "/hour-assignments", "mgr001", 400, "validation_error",
                         body={"hours": 0, "week_start": "soon"})
        for field in ("hours", "user_id", "milestone_id", "week_start"):
            self.assertIn(field, err["details"])
        self.error("POST", "/hour-assignments", "mgr001", 409, "week_closed",
                   body=assignment("emp002", week=LAST_MONDAY))
        self.error("POST", "/hour-assignments", "mgr001", 409, "already_assigned",
                   body=assignment("emp002"))

    def test_edit_and_remove(self) -> None:
        created = self.ok("POST", "/hour-assignments", "mgr001",
                          assignment("emp002", hours=10, week=NEXT_MONDAY), expected=201)
        path = f"/hour-assignments/{created['id']}"
        self.assertEqual(self.ok("PATCH", path, "mgr001", {"hours": 12})["hours"], 12)
        self.error("PATCH", path, "mgr001", 400, "validation_error", body={"hours": 41})
        extra = self.ok("POST", "/hour-assignments", "mgr001",
                        assignment("emp002", milestone=self.extra_milestone(), hours=15),
                        expected=201)
        self.error("PATCH", f"/hour-assignments/{extra['id']}", "mgr001", 409,
                   "weekly_capacity_exceeded", body={"hours": 21})
        self.error("PATCH", path, "mgr001", 400, "validation_error", body={"hours": 40.001})
        self.ok("DELETE", path, "mgr001")
        self.error("DELETE", path, "mgr001", 404)  # removed hours are hidden from managers
        self.error("DELETE", path, "adm001", 409, "assignment_archived")
        self.error("PATCH", path, "emp002", 404, body={"hours": 1})

    def test_completed_milestone_rejects_hours(self) -> None:
        self.ok("POST", f"/milestones/{PORTAL_M2}/complete", "mgr001")
        self.error("POST", "/hour-assignments", "mgr001", 409, "milestone_closed",
                   body=assignment("emp002", week=NEXT_MONDAY))


class HourVisibilityTests(ApiTestCase):
    """Who sees which assignments and availability."""

    def test_each_role_sees_the_right_assignments(self) -> None:
        count = lambda u: len(self.ok("GET", "/hour-assignments", u)["assignments"])
        self.assertEqual(count("adm001"), 11)
        self.assertEqual(count("mgr001"), 3)
        self.assertEqual(count("emp001"), 2)
        self.assertEqual(count("emp003"), 8)

    def test_week_filter(self) -> None:
        this_week = self.ok("GET", "/hour-assignments", "mgr001", query={"week": "2026-10-16"})
        self.assertEqual(len(this_week["assignments"]), 2)
        status, _ = self.call("GET", "/hour-assignments", "mgr001", query={"week": "bad"})
        self.assertEqual(status, 400)

    def test_availability_visibility(self) -> None:
        self.ok("GET", f"/users/{uid('emp001')}/availability", "emp001")
        self.error("GET", f"/users/{uid('emp003')}/availability", "mgr001", 404)
        week = self.ok("GET", f"/users/{uid('emp003')}/availability", "mgr002",
                       query={"week": LAST_MONDAY})
        self.assertEqual(week["assigned"], 0)
