"""Tests for login, tokens, refresh, logout, and lockout."""

import json
from unittest import mock

import jwt

from app import tokens
from app.store import store
from function import handler
from tests.helpers import ApiTestCase, uid

PASSWORD = "ChangeMe123"


class AuthTestCase(ApiTestCase):
    """Helpers for sending raw tokens."""

    def with_token(self, method: str, path: str, token: str, body=None):
        """Send a request with a specific Authorization header value."""
        result = handler({"rawPath": "/api/v1" + path,
                          "requestContext": {"http": {"method": method}},
                          "headers": {"authorization": token},
                          "body": json.dumps(body) if body is not None else None})
        return result["statusCode"], json.loads(result["body"]) if result.get("body") else None

    def login(self, username: str = "emp001", password: str = PASSWORD):
        """Call the login endpoint."""
        return self.call("POST", "/auth/login", body={"username": username, "password": password})


class LoginTests(AuthTestCase):
    """Signing in."""

    def test_login_with_username_or_email(self) -> None:
        status, body = self.login()
        self.assertEqual(status, 200, body)
        self.assertEqual(body["token_type"], "Bearer")
        self.assertEqual(body["user"]["username"], "emp001")
        self.assertNotIn("password_hash", body["user"])
        self.assertNotIn("token_version", body["user"])
        status, _ = self.login("EMP001@cme.example.com")
        self.assertEqual(status, 200)

    def test_token_works_on_protected_routes(self) -> None:
        _, body = self.login("mgr001")
        status, me = self.with_token("GET", "/me", f"Bearer {body['access_token']}")
        self.assertEqual((status, me["username"]), (200, "mgr001"))

    def test_wrong_password_and_unknown_user_look_the_same(self) -> None:
        wrong = self.login(password="Nope12345")
        missing = self.login(username="nobody")
        self.assertEqual(wrong[0], 401)
        self.assertEqual(wrong[1], missing[1])

    def test_archived_users_cannot_login(self) -> None:
        self.ok("DELETE", f"/users/{uid('emp002')}", "adm001")
        self.assertEqual(self.login("emp002")[0], 401)

    def test_login_validation(self) -> None:
        self.error("POST", "/auth/login", None, 400, "validation_error", {"username": ""})
        self.error("POST", "/auth/login", None, 400, "unknown_fields",
                   {"username": "a", "password": "b", "role": "admin"})

    def test_lockout_after_five_failures(self) -> None:
        for _ in range(4):
            self.assertEqual(self.login(password="Wrong1234")[0], 401)
        status, body = self.login(password="Wrong1234")
        self.assertEqual((status, body["error"]["code"]), (429, "account_locked"))
        status, body = self.login()  # right password, still locked
        self.assertEqual((status, body["error"]["code"]), (429, "account_locked"))
        self.assertIn("locked_until", self.ok("GET", f"/users/{uid('emp001')}", "adm001"))
        self.assertNotIn("locked_until", self.ok("GET", "/me", "emp001"))

    def test_admin_password_reset_unlocks(self) -> None:
        for _ in range(5):
            self.login(password="Wrong1234")
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001", {"password": "Fresh1234"})
        self.assertEqual(self.login(password="Fresh1234")[0], 200)

    def test_success_resets_failure_count(self) -> None:
        for _ in range(3):
            self.login(password="Wrong1234")
        self.assertEqual(self.login()[0], 200)
        for _ in range(4):
            self.login(password="Wrong1234")
        self.assertEqual(self.login()[0], 200)  # count restarted, not locked


class TokenTests(AuthTestCase):
    """Token checking."""

    def token(self, user: str = "emp001", kind: str = tokens.ACCESS, lifetime=None) -> str:
        """Issue a token for a seed user."""
        record = store.get("users", uid(user))
        return tokens.issue_token(record, kind, lifetime)

    def test_missing_malformed_and_tampered_tokens(self) -> None:
        self.assertEqual(self.with_token("GET", "/me", "Basic abc")[1]["error"]["code"],
                         "authentication_required")
        self.assertEqual(self.with_token("GET", "/me", "Bearer not-a-jwt")[1]["error"]["code"],
                         "invalid_token")
        forged = jwt.encode(jwt.decode(self.token(), options={"verify_signature": False})
                            | {"role": "admin"}, "wrong-secret", algorithm="HS256")
        self.assertEqual(self.with_token("GET", "/me", f"Bearer {forged}")[1]["error"]["code"],
                         "invalid_token")

    def test_alg_none_is_rejected(self) -> None:
        claims = jwt.decode(self.token(), options={"verify_signature": False})
        unsigned = jwt.encode(claims, None, algorithm="none")
        self.assertEqual(self.with_token("GET", "/me", f"Bearer {unsigned}")[0], 401)

    def test_expired_token(self) -> None:
        status, body = self.with_token("GET", "/me", f"Bearer {self.token(lifetime=-5)}")
        self.assertEqual((status, body["error"]["code"]), (401, "token_expired"))

    def test_refresh_token_cannot_be_used_as_access(self) -> None:
        status, body = self.with_token("GET", "/me", f"Bearer {self.token(kind=tokens.REFRESH)}")
        self.assertEqual((status, body["error"]["code"]), (401, "invalid_token"))

    def test_role_comes_from_database_not_token(self) -> None:
        old = self.token("emp001")
        store.update("users", uid("emp001"), {"job_title": "Changed"})
        status, me = self.with_token("GET", "/me", f"Bearer {old}")
        self.assertEqual((status, me["job_title"]), (200, "Changed"))

    def test_missing_secret_on_lambda_is_an_error(self) -> None:
        with mock.patch.dict("os.environ", {"JWT_SECRET": "", "AWS_LAMBDA_FUNCTION_NAME": "x"}):
            with self.assertRaises(RuntimeError):
                tokens.issue_token(store.get("users", uid("emp001")), tokens.ACCESS)

    def test_local_fallback_secret(self) -> None:
        with mock.patch.dict("os.environ", {"JWT_SECRET": "", "AWS_LAMBDA_FUNCTION_NAME": ""}):
            with self.assertLogs("app.tokens", level="WARNING"):
                tokens._FALLBACK_SECRET = None  # pylint: disable=protected-access
                token = tokens.issue_token(store.get("users", uid("emp001")), tokens.ACCESS)
            self.assertEqual(tokens.decode_token(token, tokens.ACCESS)["sub"], uid("emp001"))


class RefreshLogoutTests(AuthTestCase):
    """Refreshing and revoking tokens."""

    def test_refresh_returns_new_pair(self) -> None:
        _, body = self.login()
        refreshed = self.ok("POST", "/auth/refresh", body={"refresh_token": body["refresh_token"]})
        self.assertIn("access_token", refreshed)
        self.error("POST", "/auth/refresh", None, 400, "validation_error", {})
        self.error("POST", "/auth/refresh", None, 401, "invalid_token",
                   {"refresh_token": body["access_token"]})

    def test_logout_revokes_every_token(self) -> None:
        _, body = self.login()
        access, refresh_token = body["access_token"], body["refresh_token"]
        self.assertEqual(self.with_token("POST", "/auth/logout", f"Bearer {access}")[0], 200)
        self.assertEqual(self.with_token("GET", "/me", f"Bearer {access}")[1]["error"]["code"],
                         "token_revoked")
        self.error("POST", "/auth/refresh", None, 401, "token_revoked",
                   {"refresh_token": refresh_token})

    def test_password_change_needs_current_password_and_signs_out(self) -> None:
        _, body = self.login()
        bearer = f"Bearer {body['access_token']}"
        status, err = self.with_token("PATCH", f"/users/{uid('emp001')}", bearer,
                                      {"password": "Another123"})
        self.assertIn("current_password", err["error"]["details"])
        status, err = self.with_token("PATCH", f"/users/{uid('emp001')}", bearer,
                                      {"password": "Another123", "current_password": "Wrong1234"})
        self.assertEqual(status, 400)
        status, _ = self.with_token("PATCH", f"/users/{uid('emp001')}", bearer,
                                    {"password": "Another123", "current_password": PASSWORD})
        self.assertEqual(status, 200)
        self.assertEqual(self.with_token("GET", "/me", bearer)[1]["error"]["code"], "token_revoked")
        self.assertEqual(self.login(password="Another123")[0], 200)
        self.error("PATCH", f"/users/{uid('emp002')}", "emp002", 400, "validation_error",
                   {"first_name": "X", "current_password": PASSWORD})

    def test_role_change_and_archive_sign_out(self) -> None:
        _, body = self.login("emp001")
        bearer = f"Bearer {body['access_token']}"
        self.ok("PATCH", f"/users/{uid('emp001')}", "adm001", {"role": "manager"})
        self.assertEqual(self.with_token("GET", "/me", bearer)[1]["error"]["code"], "token_revoked")
        _, body = self.login("emp002")
        self.ok("DELETE", f"/users/{uid('emp002')}", "adm001")
        self.assertEqual(self.with_token("GET", "/me", f"Bearer {body['access_token']}")[0], 401)
