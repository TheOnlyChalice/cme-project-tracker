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
        seed_data(include_demo=True)

    def test_adding_again_changes_nothing(self) -> None:
        counts = {t: len(store.find(t)) for t in ("users", "projects", "milestones", "hour_assignments")}
        seed_data(include_demo=True)
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
