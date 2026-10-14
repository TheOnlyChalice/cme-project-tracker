"""Tests for project health, risk flags, utilization, and cost."""

from tests.helpers import MIGRATION, PORTAL, ApiTestCase, day, uid


class InsightTests(ApiTestCase):
    """Dashboards and reports."""

    def test_at_risk_project_has_reasons(self) -> None:
        risky = self.ok("GET", "/insights/at-risk", "adm001")["projects"]
        self.assertEqual([p["project_id"] for p in risky], [MIGRATION])
        codes = {f["code"] for f in risky[0]["risk_flags"]}
        self.assertTrue({"overdue_milestone", "deadline_near", "behind_schedule",
                         "over_budget"} <= codes)

    def test_healthy_project_and_cost_figures(self) -> None:
        health = self.ok("GET", f"/projects/{PORTAL}/health", "mgr001")
        self.assertFalse(health["at_risk"])
        self.assertEqual(health["milestones_completed"], 1)
        self.assertGreater(health["labor_cost_committed"], health["labor_cost_to_date"])
        self.assertIn("percent_budget_used", health)

    def test_employees_see_progress_but_not_cost(self) -> None:
        health = self.ok("GET", f"/projects/{MIGRATION}/health", "emp003")
        self.assertTrue(health["at_risk"])
        self.assertNotIn("budget", health)
        self.assertNotIn("labor_cost_to_date", health)

    def test_overview_respects_visibility_and_closed_filter(self) -> None:
        self.assertEqual(len(self.ok("GET", "/insights/projects", "mgr001")["projects"]), 1)
        self.ok("POST", f"/projects/{PORTAL}/complete", "adm001")
        self.assertEqual(len(self.ok("GET", "/insights/projects", "adm001")["projects"]), 1)
        everything = self.ok("GET", "/insights/projects", "adm001",
                             query={"include_closed": "true"})["projects"]
        self.assertEqual(len(everything), 2)
        closed = next(p for p in everything if p["project_id"] == PORTAL)
        self.assertEqual(closed["risk_flags"], [])

    def test_new_project_without_milestones_is_flagged(self) -> None:
        project = self.ok("POST", "/projects", "adm001",
                          {"name": "Late start", "start_date": day(-40), "end_date": day(-1),
                           "allocated_hours": 10, "manager_id": uid("mgr001")}, expected=201)
        codes = {f["code"] for f in self.ok("GET", f"/projects/{project['id']}/health",
                                            "mgr001")["risk_flags"]}
        self.assertEqual(codes, {"past_end_date", "no_milestones"})

    def test_missing_salary_is_reported(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp002')}", "adm001", {"salary": None})
        health = self.ok("GET", f"/projects/{PORTAL}/health", "adm001")
        self.assertEqual(health["employees_missing_salary"], 1)

    def test_utilization_states(self) -> None:
        rows = {r["username"]: r for r in
                self.ok("GET", "/insights/utilization", "adm001")["employees"]}
        self.assertEqual(rows["emp003"]["state"], "fully_booked")
        self.assertEqual(rows["emp001"]["state"], "partly_booked")
        self.assertEqual(rows["emp001"]["available"], 10)
        mine = self.ok("GET", "/insights/utilization", "mgr001")["employees"]
        self.assertEqual(sorted(r["username"] for r in mine), ["emp001", "emp002"])
        solo = self.ok("GET", "/insights/utilization", "emp002", query={"week": day(14)})
        self.assertEqual(solo["employees"][0]["state"], "unassigned")


class TimelineCapacityTests(ApiTestCase):
    """Data for the portfolio timeline and the hours heat map."""

    def test_timeline_lanes_and_milestone_states(self) -> None:
        lanes = {lane["name"]: lane for lane in self.ok("GET", "/insights/timeline", "adm001")["projects"]}
        portal = lanes["Customer Portal Redesign"]
        self.assertEqual(portal["manager_name"], "Morgan Reyes")
        self.assertEqual([m["state"] for m in portal["milestones"]], ["done", "in_progress", "planned"])
        migration = lanes["Data Center Migration"]
        self.assertEqual(migration["milestones"][0]["state"], "overdue")
        self.assertTrue(migration["at_risk"])

    def test_timeline_respects_visibility(self) -> None:
        names = [lane["name"] for lane in self.ok("GET", "/insights/timeline", "emp003")["projects"]]
        self.assertEqual(names, ["Data Center Migration"])
        self.ok("POST", f"/projects/{PORTAL}/complete", "mgr001")
        self.assertEqual(self.ok("GET", "/insights/timeline", "mgr001")["projects"], [])

    def test_capacity_grid(self) -> None:
        grid = self.ok("GET", "/insights/capacity", "mgr001", query={"weeks": "3"})
        self.assertEqual(grid["weeks"], ["2026-10-12", "2026-10-19", "2026-10-26"])
        sam = next(p for p in grid["people"] if p["username"] == "emp001")
        self.assertEqual([w["hours"] for w in sam["weeks"]], [30, 20, 0])
        self.assertEqual(len(self.ok("GET", "/insights/capacity", "emp001")["people"]), 1)
        self.assertEqual(len(self.ok("GET", "/insights/capacity", "adm001", query={"weeks": "x"})["weeks"]), 6)


class CostSeriesTests(ApiTestCase):
    """Weekly cumulative cost for the budget burn chart."""

    def test_running_totals_and_forecast(self) -> None:
        series = self.ok("GET", f"/projects/{MIGRATION}/cost-series", "mgr002")
        self.assertEqual(len(series["weeks"]), len(series["to_date"]))
        this = series["weeks"].index(series["this_week"])
        self.assertEqual(series["to_date"][this], series["forecast"][this])
        self.assertIsNone(series["to_date"][-1])
        self.assertIsNone(series["forecast"][0])
        self.assertAlmostEqual(series["to_date"][this], 12384.62, places=1)
        self.assertAlmostEqual(series["forecast"][-1], 14153.85, places=1)
        self.assertEqual(series["budget"], 12000)

    def test_employees_and_outsiders_are_refused(self) -> None:
        self.error("GET", f"/projects/{MIGRATION}/cost-series", "emp003", 403, "forbidden")
        self.error("GET", f"/projects/{MIGRATION}/cost-series", "mgr001", 404)
