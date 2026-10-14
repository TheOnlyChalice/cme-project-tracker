"""The demo data loads cleanly, follows every rule, and can be topped up safely."""

from collections import defaultdict
from decimal import Decimal

from app.seed import seed_data, seed_id
from app.store import store
from tests.helpers import THIS_MONDAY, ApiTestCase, uid


class DemoDataTests(ApiTestCase):
    """The full demo set."""

    def setUp(self) -> None:
        """Load the full demo set on top of the core data."""
        super().setUp()
        seed_data(include_demo=True, include_bulk=False)

    def test_adding_again_changes_nothing(self) -> None:
        counts = {t: len(store.find(t)) for t in ("users", "projects", "milestones", "hour_assignments")}
        seed_data(include_demo=True, include_bulk=False)
        self.assertEqual(counts, {t: len(store.find(t)) for t in counts})
        self.assertEqual(counts["users"], 12)

    def test_hours_follow_the_rules(self) -> None:
        weekly: dict = defaultdict(Decimal)
        for booking in store.find("hour_assignments", where={"is_archived": False}):
            weekly[(booking["user_id"], booking["week_start"])] += booking["hours"]
            employee = store.get("users", booking["user_id"])
            project = store.get("projects", booking["project_id"])
            self.assertEqual(employee["manager_id"], project["manager_id"])
        self.assertLessEqual(max(weekly.values()), 40)

    def test_someone_works_on_two_projects(self) -> None:
        week = self.ok("GET", f"/users/{uid('emp001')}/availability", "emp001", query={"week": THIS_MONDAY})
        self.assertEqual({a["project_name"] for a in week["assignments"]},
                         {"Customer Portal Redesign", "Mobile App Launch"})
        self.assertEqual(week["available"], 0)

    def test_showcase_states(self) -> None:
        health = self.ok("GET", f"/projects/{seed_id('project:analytics')}/health", "mgr003")
        self.assertIn("inactive", {f["code"] for f in health["risk_flags"]})
        onboarding = self.ok("GET", f"/projects/{seed_id('project:onboarding')}/health", "mgr002")
        self.assertIn("no_milestones", {f["code"] for f in onboarding["risk_flags"]})
        self.error("GET", f"/projects/{seed_id('project:legacy')}", "mgr002", 404)
        closed = self.ok("GET", "/projects", "adm001", query={"include_archived": "true"})["projects"]
        statuses = {p["name"]: p["status"] for p in closed}
        self.assertEqual(statuses["Legacy CRM Retirement"], "completed")
        self.assertEqual(statuses["Office Kiosk Pilot"], "abandoned")

    def test_managers_have_no_manager(self) -> None:
        for user in store.find("users"):
            if user["role"] != "employee":
                self.assertIsNone(user["manager_id"], user["username"])


class BulkDataTests(ApiTestCase):
    """The ~1,000-record bulk set follows every rule."""

    def setUp(self) -> None:
        """Load core, demo, and bulk data."""
        super().setUp()
        seed_data(include_demo=True, include_bulk=True)

    def test_about_a_thousand_records(self) -> None:
        total = sum(len(store.find(t)) for t in ("users", "projects", "milestones", "hour_assignments"))
        self.assertGreaterEqual(total, 1000)

    def test_every_booking_follows_the_rules(self) -> None:
        weekly: dict = defaultdict(Decimal)
        per_project: dict = defaultdict(Decimal)
        milestones = {m["id"]: m for m in store.find("milestones")}
        for booking in store.find("hour_assignments", where={"is_archived": False}):
            weekly[(booking["user_id"], booking["week_start"])] += booking["hours"]
            per_project[booking["project_id"]] += booking["hours"]
            employee = store.get("users", booking["user_id"])
            project = store.get("projects", booking["project_id"])
            self.assertEqual(employee["manager_id"], project["manager_id"])
            milestone = milestones[booking["milestone_id"]]
            self.assertLessEqual(booking["week_start"], milestone["end_date"])
        self.assertLessEqual(max(weekly.values()), 40)
        for project_id, used in per_project.items():
            self.assertLessEqual(used, store.get("projects", project_id)["allocated_hours"])

    def test_milestones_fit_their_projects(self) -> None:
        for milestone in store.find("milestones"):
            project = store.get("projects", milestone["project_id"])
            self.assertGreaterEqual(milestone["start_date"], project["start_date"])
            self.assertLessEqual(milestone["end_date"], project["end_date"])
            self.assertLessEqual(milestone["start_date"], milestone["end_date"])

    def test_loading_again_adds_nothing_and_reports_work(self) -> None:
        before = len(store.find("hour_assignments"))
        seed_data(include_demo=True, include_bulk=True)
        self.assertEqual(before, len(store.find("hour_assignments")))
        self.assertGreater(len(self.ok("GET", "/insights/timeline", "adm001")["projects"]), 20)
        grid = self.ok("GET", "/insights/capacity", "adm001")
        self.assertGreater(len(grid["people"]), 60)


class CacheTests(ApiTestCase):
    """The per-request read cache never serves stale data."""

    def test_writes_and_locks_refresh_the_cache(self) -> None:
        with store.transaction():
            first = store.get("users", uid("emp001"))
            store.update("users", uid("emp001"), {"job_title": "Changed"})
            self.assertEqual(store.get("users", uid("emp001"))["job_title"], "Changed")
            store.find("hour_assignments")
            store.lock_row("users", uid("emp001"))
            self.assertEqual(store.find("users", where={"username": "emp001"})[0]["job_title"], "Changed")
        self.assertNotEqual(first["job_title"], "Changed")
        self.assertEqual(store.get("users", uid("emp001"))["job_title"], "Changed")
