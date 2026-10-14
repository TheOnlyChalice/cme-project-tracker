"""Tests for the audit log."""

import unittest

from app.audit import record_audit
from app.store import store
from app.utils import new_id
from tests.helpers import MIGRATION, PORTAL, ApiTestCase, uid


class AuditTests(ApiTestCase):
    """Recording, protecting, and filtering audit entries."""

    def test_changes_are_recorded_with_actor(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "New"})
        log = self.ok("GET", f"/projects/{PORTAL}/audit-log", "adm001", query={"entity_id": PORTAL})
        entry = log["entries"][0]
        self.assertEqual(entry["action"], "update")
        self.assertEqual(entry["actor_id"], uid("mgr001"))
        self.assertEqual(entry["changes"]["description"]["after"], "New")
        self.assertNotIn("updated_at", entry["changes"])

    def test_passwords_are_never_logged(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "emp001",
                {"password": "Another123", "current_password": "ChangeMe123"})
        entry = self.ok("GET", "/audit-log", "adm001")["entries"][0]
        self.assertEqual(entry["changes"]["password_hash"]["after"], "[changed]")

    def test_role_and_team_changes_get_their_own_actions(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001",
                {"role": "manager", "job_title": "Lead"})
        actions = {e["action"] for e in self.ok("GET", "/audit-log", "adm001",
                                                query={"entity_id": uid("emp001")})["entries"]}
        self.assertEqual(actions, {"assign_role", "assign_team", "update"})

    def test_only_admins_can_read(self) -> None:
        self.error("GET", "/audit-log", "mgr001", 403, "forbidden")
        self.error("GET", "/audit-log", "emp001", 403, "forbidden")

    def test_entries_cannot_be_changed(self) -> None:
        entry = record_audit(None, "create", "test", new_id(), None, {"a": 1})
        with self.assertRaises(PermissionError):
            store.update("audit_log", entry["id"], {"action": "update"})
        self.assertFalse(hasattr(store, "delete"))
        with self.assertRaises(ValueError):
            record_audit(None, "delete", "test", new_id(), None, None)

    def test_filters_and_paging(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "emp001", {"first_name": "Samuel"})
        self.ok("PATCH", f"/users/{uid('emp002')}", "adm001", {"job_title": "Lead QA"})
        self.ok("DELETE", f"/users/{uid('emp002')}", "adm001")
        by_action = self.ok("GET", "/audit-log", "adm001", query={"action": "archive"})
        self.assertEqual(by_action["total"], 1)
        by_actor = self.ok("GET", "/audit-log", "adm001", query={"actor_id": uid("emp001")})
        self.assertEqual(by_actor["total"], 1)
        paged = self.ok("GET", "/audit-log", "adm001", query={"limit": "1", "offset": "1"})
        self.assertEqual(len(paged["entries"]), 1)
        self.assertGreaterEqual(paged["total"], 3)
        future = self.ok("GET", "/audit-log", "adm001", query={"from": "2999-01-01"})
        self.assertEqual(future["total"], 0)
        past = self.ok("GET", "/audit-log", "adm001", query={"to": "2000-01-01", "limit": "x"})
        self.assertEqual(past["total"], 0)
        self.assertEqual(past["limit"], 100)

    @unittest.skipUnless(store.backend_name == "postgres", "PostgreSQL only")
    def test_database_trigger_blocks_changes(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "Logged"})
        with self.assertRaises(Exception):
            store._execute("UPDATE audit_log SET action = 'update'")  # pylint: disable=protected-access
        with self.assertRaises(Exception):
            store._execute("DELETE FROM audit_log")  # pylint: disable=protected-access


class TransactionTests(ApiTestCase):
    """A failed request leaves no partial changes behind."""

    def test_failed_request_rolls_back(self) -> None:
        from app.router import Router
        from app.responses import ApiError
        router = Router()

        def half_done(_request):
            store.update("projects", PORTAL, {"description": "half-written"})
            raise ApiError(409, "conflict", "Stopped partway.")
        router.add("POST", "/half", half_done)
        result = router.dispatch({"rawPath": "/half", "requestContext": {"http": {"method": "POST"}}})
        self.assertEqual(result["statusCode"], 409)
        self.assertNotEqual(store.get("projects", PORTAL)["description"], "half-written")


class AuditSplitTests(ApiTestCase):
    """Project activity lives in each project's log; account activity in the general log."""

    def test_general_log_has_no_project_activity(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "Project change"})
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001", {"job_title": "Lead"})
        types = {e["entity_type"] for e in self.ok("GET", "/audit-log", "adm001")["entries"]}
        self.assertEqual(types, {"user"})

    def test_project_log_has_project_milestone_and_hours_activity(self) -> None:
        from tests.helpers import PORTAL_M2, NEXT_MONDAY
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "Project change"})
        self.ok("PATCH", f"/milestones/{PORTAL_M2}", "mgr001", {"goal": "New goal"})
        self.ok("POST", "/hour-assignments", "mgr001",
                {"user_id": uid("emp002"), "milestone_id": PORTAL_M2, "hours": 5, "week_start": NEXT_MONDAY},
                expected=201)
        self.ok("PATCH", f"/projects/{MIGRATION}", "mgr002", {"description": "Other project"})
        log = self.ok("GET", f"/projects/{PORTAL}/audit-log", "adm001")
        self.assertEqual({e["entity_type"] for e in log["entries"]}, {"project", "milestone", "hour_assignment"})
        self.assertEqual(log["total"], 3)
        only_hours = self.ok("GET", f"/projects/{PORTAL}/audit-log", "adm001", query={"entity_type": "hour_assignment"})
        self.assertEqual(only_hours["total"], 1)

    def test_project_log_is_admin_only(self) -> None:
        self.error("GET", f"/projects/{PORTAL}/audit-log", "mgr001", 403, "forbidden")
        self.error("GET", f"/projects/{PORTAL}/audit-log", "emp001", 403, "forbidden")
        self.error("GET", "/projects/missing/audit-log", "adm001", 404)
