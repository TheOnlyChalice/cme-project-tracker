"""Tests for users, reporting lines, visibility, and archiving."""

import re

from tests.helpers import MIGRATION, PORTAL, ApiTestCase, uid

NEW_EMPLOYEE = {"first_name": "Jane", "last_name": "Smith", "email": "Jane@Example.com",
                "role": "employee", "password": "Passw0rd1", "salary": 80000}


class UserVisibilityTests(ApiTestCase):
    """Who can see which users and fields."""

    def test_each_role_sees_the_right_people(self) -> None:
        names = lambda u: sorted(x["username"] for x in self.ok("GET", "/users", u)["users"])
        self.assertEqual(len(names("adm001")), 6)
        self.assertEqual(names("mgr001"), ["emp001", "emp002", "mgr001"])
        self.assertEqual(names("emp001"), ["emp001"])

    def test_salary_and_password_hash_are_hidden(self) -> None:
        me = self.ok("GET", "/me", "emp001")
        self.assertNotIn("salary", me)
        self.assertNotIn("password_hash", me)
        self.assertIn("salary", self.ok("GET", "/me", "adm001"))

    def test_users_outside_view_look_missing(self) -> None:
        self.error("GET", f"/users/{uid('emp003')}", "emp001", 404)
        self.error("GET", f"/users/{uid('emp003')}", "mgr001", 404)
        self.ok("GET", f"/users/{uid('emp003')}", "mgr002")

    def test_filters_and_search(self) -> None:
        found = self.ok("GET", "/users", "adm001", query={"search": "JORDAN"})["users"]
        self.assertEqual([u["username"] for u in found], ["emp002"])
        managers = self.ok("GET", "/users", "adm001", query={"role": "manager"})["users"]
        self.assertEqual(len(managers), 2)
        team = self.ok("GET", "/users", "adm001", query={"manager_id": uid("mgr002")})["users"]
        self.assertEqual([u["username"] for u in team], ["emp003"])

    def test_team_listing(self) -> None:
        team = self.ok("GET", f"/users/{uid('mgr001')}/team", "mgr001")["users"]
        self.assertEqual(sorted(u["username"] for u in team), ["emp001", "emp002"])
        self.error("GET", f"/users/{uid('mgr001')}/team", "emp001", 404)
        self.error("GET", f"/users/{uid('mgr002')}/team", "mgr001", 404)

    def test_current_projects_are_derived(self) -> None:
        self.assertEqual(self.ok("GET", "/me", "emp001")["current_project_ids"], [PORTAL])
        self.assertEqual(self.ok("GET", "/me", "mgr002")["current_project_ids"], [MIGRATION])
        self.assertEqual(self.ok("GET", "/me", "adm001")["current_project_ids"], [])


class UserCreationTests(ApiTestCase):
    """Creating users."""

    def test_admin_creates_employee_with_generated_username(self) -> None:
        user = self.ok("POST", "/users", "adm001",
                       {**NEW_EMPLOYEE, "manager_id": uid("mgr001")}, expected=201)
        self.assertRegex(user["username"], r"^jsmi\d{2}$")
        self.assertEqual(user["email"], "jane@example.com")
        self.assertNotIn("password_hash", user)

    def test_only_admins_create_users(self) -> None:
        self.error("POST", "/users", "mgr001", 403, "forbidden", NEW_EMPLOYEE)

    def test_validation_reports_every_bad_field(self) -> None:
        err = self.error("POST", "/users", "adm001", 400, "validation_error",
                         {"first_name": " ", "email": "bad", "role": "boss", "password": "x",
                          "salary": -1})
        for field in ("first_name", "last_name", "email", "role", "password", "salary"):
            self.assertIn(field, err["details"])

    def test_employee_needs_a_valid_manager(self) -> None:
        self.error("POST", "/users", "adm001", 400, "validation_error", NEW_EMPLOYEE)
        self.error("POST", "/users", "adm001", 400, "validation_error",
                   {**NEW_EMPLOYEE, "manager_id": uid("emp001")})
        self.error("POST", "/users", "adm001", 400, "validation_error",
                   {**NEW_EMPLOYEE, "manager_id": "missing"})

    def test_duplicate_email_is_rejected(self) -> None:
        self.error("POST", "/users", "adm001", 409, "email_taken",
                   {**NEW_EMPLOYEE, "email": "EMP001@cme.example.com", "manager_id": uid("mgr001")})

    def test_unknown_fields_are_rejected(self) -> None:
        self.error("POST", "/users", "adm001", 400, "unknown_fields",
                   {**NEW_EMPLOYEE, "manager_id": uid("mgr001"), "is_admin": True})

    def test_usernames_stay_unique_and_six_characters(self) -> None:
        names = set()
        for i in range(15):
            user = self.ok("POST", "/users", "adm001",
                           {**NEW_EMPLOYEE, "first_name": "Al", "last_name": "X",
                            "email": f"al{i}@x.com", "manager_id": uid("mgr001")}, expected=201)
            self.assertEqual(len(user["username"]), 6)
            self.assertTrue(re.match(r"^[a-z0-9]{6}$", user["username"]))
            names.add(user["username"])
        self.assertEqual(len(names), 15)


class UserEditTests(ApiTestCase):
    """Editing users and the role safeguards."""

    def test_users_edit_their_own_personal_details_only(self) -> None:
        me = self.ok("PATCH", f"/users/{uid('emp001')}", "emp001",
                     {"first_name": "Samuel", "password": "NewPass123",
                      "current_password": "ChangeMe123"})
        self.assertEqual(me["first_name"], "Samuel")
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 400, "unknown_fields",
                   {"role": "admin"})
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 400, "unknown_fields",
                   {"salary": 1})
        self.error("PATCH", f"/users/{uid('emp001')}", "mgr001", 403, "forbidden",
                   {"first_name": "X"})
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 400, "no_changes", {})
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 400, "validation_error",
                   {"password": "short"})

    def test_admin_changes_role_and_manager(self) -> None:
        user = self.ok("PATCH", f"/users/{uid('emp001')}", "adm001",
                       {"role": "manager", "manager_id": uid("adm001"), "salary": 99000})
        self.assertEqual(user["role"], "manager")

    def test_role_safeguards(self) -> None:
        self.error("PATCH", f"/users/{uid('mgr001')}", "adm001", 409, "has_reports",
                   {"role": "employee", "manager_id": uid("mgr002")})
        self.error("PATCH", f"/users/{uid('adm001')}", "adm001", 409, "last_admin",
                   {"role": "manager"})
        self.error("PATCH", f"/users/{uid('emp001')}", "adm001", 409, "manager_required",
                   {"manager_id": None})

    def test_reporting_loops_and_self_reporting_are_blocked(self) -> None:
        self.error("PATCH", f"/users/{uid('adm001')}", "adm001", 400, "validation_error",
                   {"manager_id": uid("mgr001")})
        self.error("PATCH", f"/users/{uid('mgr001')}", "adm001", 400, "validation_error",
                   {"manager_id": uid("mgr001")})

    def test_duplicate_email_on_edit(self) -> None:
        self.error("PATCH", f"/users/{uid('emp001')}", "emp001", 409, "email_taken",
                   {"email": "emp002@cme.example.com"})

    def test_team_move_releases_future_hours(self) -> None:
        before = self.ok("GET", "/hour-assignments", "adm001", query={"user_id": uid("emp001")})
        self.assertEqual(len(before["assignments"]), 2)
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001", {"manager_id": uid("mgr002")})
        after = self.ok("GET", "/hour-assignments", "adm001", query={"user_id": uid("emp001")})
        self.assertEqual(len(after["assignments"]), 1)  # this week's hours stay


class UserArchiveTests(ApiTestCase):
    """Archiving and restoring users."""

    def test_archive_and_restore(self) -> None:
        self.ok("DELETE", f"/users/{uid('emp002')}", "adm001")
        self.error("GET", f"/users/{uid('emp002')}", "mgr001", 404)
        self.error("GET", "/me", "emp002", 401, "invalid_user")
        hidden = self.ok("GET", "/users", "adm001")["users"]
        self.assertNotIn("emp002", [u["username"] for u in hidden])
        shown = self.ok("GET", "/users", "adm001", query={"include_archived": "true"})["users"]
        self.assertIn("emp002", [u["username"] for u in shown])
        self.error("PATCH", f"/users/{uid('emp002')}", "adm001", 409, "archived", {"first_name": "X"})
        self.error("DELETE", f"/users/{uid('emp002')}", "adm001", 409, "already_archived")
        self.ok("POST", f"/users/{uid('emp002')}/restore", "adm001")
        self.error("POST", f"/users/{uid('emp002')}/restore", "adm001", 409, "not_archived")

    def test_archive_safeguards(self) -> None:
        self.error("DELETE", f"/users/{uid('emp001')}", "mgr001", 403)
        self.error("DELETE", f"/users/{uid('adm001')}", "adm001", 409, "self_archive")
        self.error("DELETE", f"/users/{uid('mgr001')}", "adm001", 409, "has_reports")

    def test_manager_with_projects_and_restore_order(self) -> None:
        new_mgr = self.ok("POST", "/users", "adm001",
                          {**NEW_EMPLOYEE, "role": "manager"}, expected=201)
        project = self.ok("POST", "/projects", "adm001",
                          {"name": "Side project", "start_date": "2026-10-01",
                           "end_date": "2026-12-01", "allocated_hours": 10,
                           "manager_id": new_mgr["id"]}, expected=201)
        self.error("DELETE", f"/users/{new_mgr['id']}", "adm001", 409, "manages_projects")
        self.ok("DELETE", f"/projects/{project['id']}", "adm001")
        self.ok("DELETE", f"/users/{new_mgr['id']}", "adm001")
        self.error("POST", f"/projects/{project['id']}/restore", "adm001", 409, "manager_archived")

    def test_restore_needs_active_manager(self) -> None:
        manager = self.ok("POST", "/users", "adm001",
                          {**NEW_EMPLOYEE, "role": "manager", "email": "m@x.com"}, expected=201)
        worker = self.ok("POST", "/users", "adm001",
                         {**NEW_EMPLOYEE, "email": "w@x.com", "manager_id": manager["id"]},
                         expected=201)
        self.ok("DELETE", f"/users/{worker['id']}", "adm001")
        self.ok("DELETE", f"/users/{manager['id']}", "adm001")
        self.error("POST", f"/users/{worker['id']}/restore", "adm001", 409, "manager_archived")
        self.ok("POST", f"/users/{manager['id']}/restore", "adm001")
        self.ok("POST", f"/users/{worker['id']}/restore", "adm001")
