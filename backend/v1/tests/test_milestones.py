"""Tests for milestones and the milestone chain."""

from tests.helpers import (MIGRATION, MIGRATION_M1, MIGRATION_M2, PORTAL, PORTAL_M2, PORTAL_M3,
                           ApiTestCase, day)

NEW_MILESTONE = {"name": "Beta test", "goal": "Test with 50 users",
                 "deliverables": ["Test plan", " ", "Feedback report"]}


class MilestoneTests(ApiTestCase):
    """Creating, editing, completing, and archiving milestones."""

    def test_create_gets_next_sequence(self) -> None:
        m = self.ok("POST", f"/projects/{PORTAL}/milestones", "mgr001",
                    {**NEW_MILESTONE, "start_date": day(50), "end_date": day(60)}, expected=201)
        self.assertEqual(m["sequence"], 4)
        self.assertEqual(m["deliverables"], ["Test plan", "Feedback report"])

    def test_first_milestone_becomes_active(self) -> None:
        project = self.ok("POST", "/projects", "adm001",
                          {"name": "New", "start_date": day(0), "end_date": day(30),
                           "allocated_hours": 100, "manager_id": self.ok(
                               "GET", "/me", "mgr001")["id"]}, expected=201)
        m = self.ok("POST", f"/projects/{project['id']}/milestones", "mgr001",
                    {"name": "First", "start_date": day(0), "end_date": day(5)}, expected=201)
        self.assertEqual(self.ok("GET", f"/projects/{project['id']}", "mgr001")["active_milestone_id"],
                         m["id"])

    def test_dates_must_be_inside_project(self) -> None:
        err = self.error("POST", f"/projects/{PORTAL}/milestones", "mgr001", 400,
                         "validation_error", {**NEW_MILESTONE, "start_date": day(-100),
                                              "end_date": day(500)})
        self.assertIn("start_date", err["details"])
        self.assertIn("end_date", err["details"])
        self.error("POST", f"/projects/{PORTAL}/milestones", "mgr001", 400, "validation_error",
                   {**NEW_MILESTONE, "start_date": day(10), "end_date": day(5)})

    def test_permissions(self) -> None:
        body = {**NEW_MILESTONE, "start_date": day(50), "end_date": day(60)}
        self.error("POST", f"/projects/{PORTAL}/milestones", "emp001", 403, body=body)
        self.error("POST", f"/projects/{PORTAL}/milestones", "mgr002", 404, body=body)
        self.ok("GET", f"/milestones/{PORTAL_M2}", "emp001")
        self.error("GET", f"/milestones/{PORTAL_M2}", "emp003", 404)

    def test_edit_and_shrinking_around_booked_hours(self) -> None:
        self.ok("PATCH", f"/milestones/{PORTAL_M2}", "mgr001", {"goal": "Ship it"})
        self.error("PATCH", f"/milestones/{PORTAL_M2}", "mgr001", 409, "hours_outside_dates",
                   {"start_date": day(20)})
        self.error("PATCH", f"/milestones/{PORTAL_M2}", "mgr001", 400, "no_changes", {})

    def test_complete_advances_active_milestone_and_releases_hours(self) -> None:
        done = self.ok("POST", f"/milestones/{PORTAL_M2}/complete", "mgr001")
        self.assertEqual(done["status"], "completed")
        self.assertEqual(self.ok("GET", f"/projects/{PORTAL}", "mgr001")["active_milestone_id"],
                         PORTAL_M3)
        self.assertEqual(len(self.ok("GET", "/hour-assignments", "mgr001",
                                     query={"milestone_id": PORTAL_M2})["assignments"]), 2)
        self.error("POST", f"/milestones/{PORTAL_M2}/complete", "mgr001", 409, "already_completed")
        self.error("PATCH", f"/milestones/{PORTAL_M2}", "mgr001", 409, "milestone_completed",
                   {"name": "X"})

    def test_archive_and_restore(self) -> None:
        self.error("DELETE", f"/milestones/{MIGRATION_M1}", "mgr002", 403, "forbidden")
        self.ok("DELETE", f"/milestones/{MIGRATION_M1}", "adm001")
        self.assertEqual(self.ok("GET", f"/projects/{MIGRATION}", "mgr002")["active_milestone_id"],
                         MIGRATION_M2)
        self.error("GET", f"/milestones/{MIGRATION_M1}", "mgr002", 404)
        listed = self.ok("GET", f"/projects/{MIGRATION}/milestones", "adm001",
                         query={"include_archived": "true"})["milestones"]
        self.assertEqual(len(listed), 2)
        self.error("POST", f"/milestones/{MIGRATION_M1}/restore", "mgr002", 403)
        self.ok("POST", f"/milestones/{MIGRATION_M1}/restore", "adm001")
        self.error("POST", f"/milestones/{MIGRATION_M1}/restore", "adm001", 409, "not_archived")
        self.ok("DELETE", f"/milestones/{MIGRATION_M1}", "adm001")
        self.error("PATCH", f"/milestones/{MIGRATION_M1}", "adm001", 409, "milestone_archived",
                   {"name": "X"})

    def test_list_filters_by_status(self) -> None:
        active = self.ok("GET", f"/projects/{PORTAL}/milestones", "emp001",
                         query={"status": "active"})["milestones"]
        self.assertEqual([m["sequence"] for m in active], [2, 3])

    def test_chain_marks_blocked_and_overdue(self) -> None:
        chain = self.ok("GET", f"/projects/{MIGRATION}/milestone-chain", "emp003")["milestones"]
        self.assertIsNone(chain[0]["depends_on_id"])
        self.assertTrue(chain[0]["overdue"])
        self.assertEqual(chain[1]["depends_on_id"], MIGRATION_M1)
        self.assertTrue(chain[1]["blocked"])
        portal = self.ok("GET", f"/projects/{PORTAL}/milestone-chain", "mgr001")["milestones"]
        self.assertFalse(portal[1]["blocked"])  # milestone 1 is completed


class AutoCompleteTests(ApiTestCase):
    """Completing every milestone completes the project."""

    def test_last_milestone_completes_and_archives_project(self) -> None:
        first = self.ok("POST", f"/milestones/{MIGRATION_M1}/complete", "mgr002")
        self.assertFalse(first["project_completed"])
        self.ok("GET", f"/projects/{MIGRATION}", "mgr002")
        last = self.ok("POST", f"/milestones/{MIGRATION_M2}/complete", "mgr002")
        self.assertTrue(last["project_completed"])
        self.error("GET", f"/projects/{MIGRATION}", "mgr002", 404)
        project = self.ok("GET", f"/projects/{MIGRATION}", "adm001")
        self.assertEqual((project["status"], project["is_archived"]), ("completed", True))
        log = self.ok("GET", "/audit-log", "adm001", query={"entity_id": MIGRATION, "action": "complete"})
        self.assertEqual(log["entries"][0]["actor_id"], self.ok("GET", "/me", "mgr002")["id"])

    def test_archived_milestones_do_not_block_completion(self) -> None:
        self.ok("DELETE", f"/milestones/{PORTAL_M3}", "adm001")
        done = self.ok("POST", f"/milestones/{PORTAL_M2}/complete", "mgr001")
        self.assertTrue(done["project_completed"])

    def test_completed_project_releases_future_hours(self) -> None:
        self.ok("POST", f"/milestones/{MIGRATION_M1}/complete", "mgr002")
        self.ok("POST", f"/milestones/{MIGRATION_M2}/complete", "mgr002")
        future = [a for a in self.ok("GET", "/hour-assignments", "adm001",
                                     query={"project_id": MIGRATION})["assignments"]
                  if a["week_start"] > "2026-10-12"]
        self.assertEqual(future, [])
