"""Tests for the audit log."""

from app.audit import record_audit
from app.store import store
from tests.helpers import PORTAL, ApiTestCase, uid


class AuditTests(ApiTestCase):
    """Recording, protecting, and filtering audit entries."""

    def test_changes_are_recorded_with_actor(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "New"})
        log = self.ok("GET", "/audit-log", "adm001", query={"entity_id": PORTAL})
        entry = log["entries"][0]
        self.assertEqual(entry["action"], "update")
        self.assertEqual(entry["actor_id"], uid("mgr001"))
        self.assertEqual(entry["changes"]["description"]["after"], "New")
        self.assertNotIn("updated_at", entry["changes"])

    def test_passwords_are_never_logged(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "emp001", {"password": "Another123"})
        entry = self.ok("GET", "/audit-log", "adm001")["entries"][0]
        self.assertEqual(entry["changes"]["password_hash"]["after"], "[changed]")

    def test_role_and_team_changes_get_their_own_actions(self) -> None:
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001",
                {"role": "manager", "manager_id": uid("adm001"), "job_title": "Lead"})
        actions = {e["action"] for e in self.ok("GET", "/audit-log", "adm001",
                                                query={"entity_id": uid("emp001")})["entries"]}
        self.assertEqual(actions, {"assign_role", "assign_team", "update"})

    def test_only_admins_can_read(self) -> None:
        self.error("GET", "/audit-log", "mgr001", 403, "forbidden")
        self.error("GET", "/audit-log", "emp001", 403, "forbidden")

    def test_entries_cannot_be_changed(self) -> None:
        entry = record_audit(None, "create", "test", "x", None, {"a": 1})
        with self.assertRaises(PermissionError):
            store.update("audit_log", entry["id"], {"action": "update"})
        self.assertFalse(hasattr(store, "delete"))
        with self.assertRaises(ValueError):
            record_audit(None, "delete", "test", "x", None, None)

    def test_filters_and_paging(self) -> None:
        self.ok("PATCH", f"/projects/{PORTAL}", "mgr001", {"description": "A"})
        self.ok("POST", f"/projects/{PORTAL}/complete", "adm001")
        by_action = self.ok("GET", "/audit-log", "adm001", query={"action": "complete"})
        self.assertEqual(by_action["total"], 1)
        by_actor = self.ok("GET", "/audit-log", "adm001", query={"actor_id": uid("mgr001")})
        self.assertEqual(by_actor["total"], 1)
        paged = self.ok("GET", "/audit-log", "adm001", query={"limit": "1", "offset": "1"})
        self.assertEqual(len(paged["entries"]), 1)
        self.assertGreaterEqual(paged["total"], 3)
        future = self.ok("GET", "/audit-log", "adm001", query={"from": "2999-01-01"})
        self.assertEqual(future["total"], 0)
        past = self.ok("GET", "/audit-log", "adm001", query={"to": "2000-01-01", "limit": "x"})
        self.assertEqual(past["total"], 0)
        self.assertEqual(past["limit"], 100)
