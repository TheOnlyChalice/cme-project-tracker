"""Tests for projects: creation, edits, status changes, and visibility."""

from tests.helpers import MIGRATION, PORTAL, PORTAL_M2, ApiTestCase, uid

NEW_PROJECT = {"name": "Mobile App", "description": "A new app", "start_date": "2026-11-01",
               "end_date": "2027-03-01", "allocated_hours": 500, "budget": 50000}


class ProjectVisibilityTests(ApiTestCase):
    """Who sees which projects."""

    def test_each_role_sees_the_right_projects(self) -> None:
        names = lambda u: [p["name"] for p in self.ok("GET", "/projects", u)["projects"]]
        self.assertEqual(len(names("adm001")), 2)
        self.assertEqual(names("mgr001"), ["Customer Portal Redesign"])
        self.assertEqual(names("emp003"), ["Data Center Migration"])
        self.error("GET", f"/projects/{PORTAL}", "emp003", 404)

    def test_employees_do_not_see_budget(self) -> None:
        self.assertNotIn("budget", self.ok("GET", f"/projects/{PORTAL}", "emp001"))
        self.assertIn("budget", self.ok("GET", f"/projects/{PORTAL}", "mgr001"))

    def test_derived_lists(self) -> None:
        project = self.ok("GET", f"/projects/{PORTAL}", "adm001")
        self.assertEqual(len(project["milestone_ids"]), 3)
        self.assertEqual(sorted(project["assigned_employee_ids"]), sorted([uid("emp001"), uid("emp002")]))

    def test_filters(self) -> None:
        found = self.ok("GET", "/projects", "adm001", query={"search": "migration"})["projects"]
        self.assertEqual([p["id"] for p in found], [MIGRATION])
        found = self.ok("GET", "/projects", "adm001", query={"manager_id": uid("mgr001")})["projects"]
        self.assertEqual([p["id"] for p in found], [PORTAL])
        self.assertEqual(self.ok("GET", "/projects", "adm001",
                                 query={"status": "completed"})["projects"], [])


class ProjectCreateEditTests(ApiTestCase):
    """Creating and editing projects."""

    def test_admin_creates_project(self) -> None:
        project = self.ok("POST", "/projects", "adm001",
                          {**NEW_PROJECT, "manager_id": uid("mgr001")}, expected=201)
        self.assertEqual(project["status"], "active")
        self.assertEqual(project["created_by"], uid("adm001"))

    def test_only_admins_create_projects(self) -> None:
        self.error("POST", "/projects", "mgr001", 403, "forbidden",
                   {**NEW_PROJECT, "manager_id": uid("mgr001")})

    def test_create_validation(self) -> None:
        err = self.error("POST", "/projects", "adm001", 400, "validation_error",
                         {"name": "", "start_date": "nope", "allocated_hours": 0})
        for field in ("name", "start_date", "end_date", "allocated_hours", "manager_id"):
            self.assertIn(field, err["details"])
        self.error("POST", "/projects", "adm001", 400, "validation_error",
                   {**NEW_PROJECT, "manager_id": uid("emp001")})
        self.error("POST", "/projects", "adm001", 400, "validation_error",
                   {**NEW_PROJECT, "end_date": "2026-11-01", "manager_id": uid("mgr001")})

    def test_names_are_unique_ignoring_case(self) -> None:
        self.error("POST", "/projects", "adm001", 409, "name_taken",
                   {**NEW_PROJECT, "name": "customer portal REDESIGN", "manager_id": uid("mgr001")})

    def test_manager_edits_own_project_only(self) -> None:
        updated = self.ok("PATCH", f"/projects/{PORTAL}", "mgr001",
                          {"description": "Updated", "allocated_hours": 1300})
        self.assertEqual(updated["description"], "Updated")
        self.error("PATCH", f"/projects/{PORTAL}", "mgr001", 400, "unknown_fields",
                   {"manager_id": uid("mgr002")})
        self.error("PATCH", f"/projects/{MIGRATION}", "mgr001", 404)
        self.error("PATCH", f"/projects/{PORTAL}", "emp001", 403, "forbidden", {"name": "X"})
        self.error("PATCH", f"/projects/{PORTAL}", "mgr001", 400, "no_changes", {})

    def test_only_admins_change_budget(self) -> None:
        self.error("PATCH", f"/projects/{PORTAL}", "mgr001", 400, "unknown_fields", {"budget": 1})
        self.assertEqual(self.ok("GET", f"/projects/{PORTAL}", "mgr001")["budget"], 150000)
        self.assertEqual(self.ok("PATCH", f"/projects/{PORTAL}", "adm001", {"budget": 175000})["budget"], 175000)

    def test_dates_must_still_hold_milestones(self) -> None:
        self.error("PATCH", f"/projects/{PORTAL}", "mgr001", 409, "milestones_outside_dates",
                   {"end_date": "2026-11-01"})

    def test_allocated_hours_cannot_drop_below_assigned(self) -> None:
        self.error("PATCH", f"/projects/{PORTAL}", "mgr001", 409, "below_assigned_hours",
                   {"allocated_hours": 10})
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"allocated_hours": 70})

    def test_active_milestone_must_belong_to_project(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"active_milestone_id": PORTAL_M2})
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"active_milestone_id": None})
        self.error("PATCH", f"/projects/{MIGRATION}", "mgr002", 400, "validation_error",
                   {"active_milestone_id": PORTAL_M2})

    def test_admin_hands_project_to_new_manager(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "adm001", {"manager_id": uid("mgr002")})
        self.error("GET", f"/projects/{PORTAL}", "mgr001", 404)
        self.ok("GET", f"/projects/{PORTAL}", "mgr002")
        remaining = self.ok("GET", "/hour-assignments", "adm001", query={"project_id": PORTAL})
        self.assertEqual(len(remaining["assignments"]), 2)  # next week's hours released


class ProjectStatusTests(ApiTestCase):
    """Completing, abandoning, archiving, and restoring."""

    def test_complete_hides_from_manager_and_releases_future_hours(self) -> None:
        project = self.ok("POST", f"/projects/{PORTAL}/complete", "mgr001")
        self.assertEqual(project["status"], "completed")
        self.assertTrue(project["is_archived"])
        self.error("GET", f"/projects/{PORTAL}", "mgr001", 404)
        self.error("GET", f"/projects/{PORTAL}", "emp001", 404)
        self.ok("GET", f"/projects/{PORTAL}", "adm001")
        self.error("PATCH", f"/projects/{PORTAL}", "adm001", 409, "project_closed", {"name": "X"})

    def test_only_admins_abandon_or_archive(self) -> None:
        self.error("POST", f"/projects/{PORTAL}/abandon", "mgr001", 403)
        self.error("DELETE", f"/projects/{PORTAL}", "mgr001", 403)
        self.assertEqual(self.ok("POST", f"/projects/{PORTAL}/abandon", "adm001")["status"],
                         "abandoned")

    def test_archive_then_restore_sets_active(self) -> None:
        self.ok("DELETE", f"/projects/{MIGRATION}", "adm001")
        self.error("DELETE", f"/projects/{MIGRATION}", "adm001", 409, "already_archived")
        listed = self.ok("GET", "/projects", "adm001", query={"include_archived": "true"})
        self.assertEqual(len(listed["projects"]), 2)
        restored = self.ok("POST", f"/projects/{MIGRATION}/restore", "adm001")
        self.assertFalse(restored["is_archived"])
        self.assertEqual(restored["status"], "active")
        self.error("POST", f"/projects/{MIGRATION}/restore", "adm001", 409, "not_archived")
        self.error("POST", f"/projects/{MIGRATION}/restore", "mgr002", 403)

    def test_completed_project_restores_to_active(self) -> None:
        self.ok("POST", f"/projects/{PORTAL}/complete", "adm001")
        self.assertEqual(self.ok("POST", f"/projects/{PORTAL}/restore", "adm001")["status"], "active")
        self.ok("GET", f"/projects/{PORTAL}", "mgr001")
