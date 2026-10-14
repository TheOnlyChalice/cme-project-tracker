"""Tests for quick search."""

from tests.helpers import MIGRATION, PORTAL, PORTAL_M2, ApiTestCase, uid


class QuickSearchTests(ApiTestCase):
    """Searching projects, milestones, and people."""

    def test_finds_all_three_kinds(self) -> None:
        results = self.ok("GET", "/search", "adm001", query={"q": "port"})
        self.assertEqual([p["id"] for p in results["projects"]], [PORTAL])
        results = self.ok("GET", "/search", "adm001", query={"q": "build"})
        self.assertIn(PORTAL_M2, [m["id"] for m in results["milestones"]])
        self.assertEqual(results["milestones"][0]["project_name"], "Customer Portal Redesign")
        people = self.ok("GET", "/search", "adm001", query={"q": "sam"})["people"]
        self.assertEqual(people[0]["id"], uid("emp001"))

    def test_searches_other_fields_and_ranks_names_first(self) -> None:
        by_deliverable = self.ok("GET", "/search", "adm001", query={"q": "wireframes"})["milestones"]
        self.assertEqual(len(by_deliverable), 1)
        by_username = self.ok("GET", "/search", "adm001", query={"q": "emp003"})["people"]
        self.assertEqual(by_username[0]["name"], "Taylor Brooks")
        by_title = self.ok("GET", "/search", "adm001", query={"q": "engineer"})
        self.assertGreaterEqual(by_title["totals"]["people"], 3)

    def test_respects_visibility(self) -> None:
        mine = self.ok("GET", "/search", "emp001", query={"q": "migration"})
        self.assertEqual(mine["projects"], [])
        self.assertEqual(mine["milestones"], [])
        self.assertEqual(self.ok("GET", "/search", "emp001", query={"q": "jordan"})["people"], [])
        self.assertEqual(len(self.ok("GET", "/search", "mgr002", query={"q": "migration"})["projects"]), 1)
        self.ok("POST", f"/projects/{MIGRATION}/complete", "mgr002")
        self.assertEqual(self.ok("GET", "/search", "mgr002", query={"q": "migration"})["projects"], [])
        archived = self.ok("GET", "/search", "adm001", query={"q": "migration"})["projects"]
        self.assertTrue(archived[0]["is_archived"])

    def test_short_or_missing_text_returns_nothing(self) -> None:
        self.assertEqual(self.ok("GET", "/search", "adm001", query={"q": "a"})["totals"]["projects"], 0)
        self.assertEqual(self.ok("GET", "/search", "adm001")["people"], [])
        self.error("GET", "/search", None, 401, "authentication_required")
