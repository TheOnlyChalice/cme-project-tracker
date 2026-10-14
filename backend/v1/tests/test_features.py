"""Tests for auto-archiving, translated-friendly errors, and the role review fixes."""

from unittest import mock

from app import clock
from app.store import store
from tests.helpers import FROZEN_TODAY, MIGRATION, PORTAL, ApiTestCase, day, uid


def age_project(project_id: str, days_ago: int) -> None:
    """Make a project, its milestones, and its hours look untouched for a while."""
    stamp = f"{day(-days_ago)}T09:00:00+00:00"
    store.update("projects", project_id, {"created_at": stamp, "updated_at": stamp})
    for table in ("milestones", "hour_assignments"):
        for row in store.find(table, where={"project_id": project_id}):
            store.update(table, row["id"], {"created_at": stamp, "updated_at": stamp})


def remove_upcoming_hours(project_id: str) -> None:
    """Archive hours booked from this week on, so only inactivity matters."""
    for row in store.find("hour_assignments", where={"project_id": project_id}):
        if row["week_start"] >= clock.week_start_of(FROZEN_TODAY).isoformat():
            store.update("hour_assignments", row["id"], {"is_archived": True})


class AutoArchiveTests(ApiTestCase):
    """Inactive projects are flagged, and admins can archive them on demand."""

    def new_project(self, name: str = "Quiet project") -> str:
        """Create a project with no milestones or hours."""
        return self.ok("POST", "/projects", "adm001",
                       {"name": name, "start_date": day(-60), "end_date": day(60),
                        "allocated_hours": 10, "manager_id": uid("mgr001")}, expected=201)["id"]

    def test_warning_flag_before_archiving(self) -> None:
        project = self.new_project()
        age_project(project, 11)
        flags = {f["code"]: f for f in self.ok("GET", f"/projects/{project}/health", "mgr001")["risk_flags"]}
        self.assertEqual(flags["inactive"]["params"], {"days": 11})

    def test_admin_run_archives_quiet_projects_only(self) -> None:
        quiet = self.new_project()
        age_project(quiet, 15)
        fresh = self.new_project("Busy project")
        result = self.ok("POST", "/admin/maintenance", "adm001")
        self.assertEqual([p["id"] for p in result["archived"]], [quiet])
        self.error("GET", f"/projects/{quiet}", "mgr001", 404)
        self.ok("GET", f"/projects/{fresh}", "mgr001")
        entry = self.ok("GET", f"/projects/{quiet}/audit-log", "adm001", query={"entity_id": quiet})["entries"][0]
        self.assertEqual((entry["action"], entry["actor_id"]), ("archive", uid("adm001")))

    def test_upcoming_hours_count_as_activity(self) -> None:
        age_project(PORTAL, 30)
        self.assertEqual(self.ok("POST", "/admin/maintenance", "adm001")["archived"], [])
        remove_upcoming_hours(PORTAL)
        archived = self.ok("POST", "/admin/maintenance", "adm001")["archived"]
        self.assertIn(PORTAL, [p["id"] for p in archived])

    def test_only_admins_can_run_it(self) -> None:
        self.error("POST", "/admin/maintenance", "mgr001", 403, "forbidden")

    def test_nothing_is_archived_automatically(self) -> None:
        quiet = self.new_project()
        age_project(quiet, 30)
        self.ok("GET", "/me", "emp001")
        self.ok("GET", "/insights/projects", "adm001")
        self.ok("GET", f"/projects/{quiet}", "mgr001")

    def test_far_future_archives_everything_idle(self) -> None:
        with mock.patch.object(clock, "today", return_value=FROZEN_TODAY.replace(year=2027)):
            names = {p["name"] for p in self.ok("POST", "/admin/maintenance", "adm001")["archived"]}
        self.assertEqual(names, {"Customer Portal Redesign", "Data Center Migration"})


class ReviewFixTests(ApiTestCase):
    """Fixes found in the role-overlap review."""

    def test_manager_with_projects_cannot_become_employee(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001", {"manager_id": uid("mgr002")})
        self.ok("PATCH", f"/users/{uid('emp002')}", "adm001", {"manager_id": uid("mgr002")})
        self.error("PATCH", f"/users/{uid('mgr001')}", "adm001", 409, "manages_projects",
                   {"role": "employee", "manager_id": uid("mgr002")})

    def test_profile_picture_must_be_web_link(self) -> None:
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 400, "validation_error",
                   {"profile_picture_url": "javascript:alert(1)"})
        self.ok("PATCH", f"/users/{uid('emp001')}", "emp001",
                {"profile_picture_url": "https://example.com/me.png"})

    def test_employees_do_not_see_budget_in_flags(self) -> None:
        employee = next(f for f in self.ok("GET", f"/projects/{MIGRATION}/health", "emp003")["risk_flags"]
                        if f["code"] == "over_budget")
        self.assertEqual(employee["params"], {})
        self.assertNotIn("12000", employee["message"])
        manager = next(f for f in self.ok("GET", f"/projects/{MIGRATION}/health", "mgr002")["risk_flags"]
                       if f["code"] == "over_budget")
        self.assertEqual(manager["params"]["budget"], 12000.0)

    def test_every_flag_has_params(self) -> None:
        for flag in self.ok("GET", f"/projects/{MIGRATION}/health", "adm001")["risk_flags"]:
            self.assertIn("params", flag)

    def test_lockout_reports_minutes(self) -> None:
        for _ in range(5):
            status, body = self.call("POST", "/auth/login", body={"username": "emp001", "password": "Wrong1234"})
        self.assertEqual(status, 429)
        self.assertEqual(body["error"]["details"]["minutes"], 15)
