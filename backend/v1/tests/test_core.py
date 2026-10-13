"""Tests for routing, request parsing, responses, and passwords."""

import json
import unittest

from app.passwords import hash_password, password_problem, verify_password
from app.request import normalize_path
from app.responses import ApiError, json_response
from app.router import Router
from tests.helpers import ApiTestCase


class RoutingTests(ApiTestCase):
    """The router, path handling, and error format."""

    def test_health_works_with_and_without_prefix(self) -> None:
        health = self.ok("GET", "/health")
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["database"], "reachable")
        self.assertEqual(normalize_path("/api/v1/health/"), "/health")
        self.assertEqual(normalize_path("/health"), "/health")
        self.assertEqual(normalize_path(""), "/")

    def test_index_lists_routes(self) -> None:
        self.assertIn("GET /projects", self.ok("GET", "/")["routes"])

    def test_unknown_path_is_404_and_wrong_method_is_405(self) -> None:
        self.error("GET", "/nope", None, 404, "not_found")
        self.error("PUT", "/health", None, 405, "method_not_allowed")

    def test_invalid_json_body(self) -> None:
        status, data = self.call("POST", "/users", "adm001")
        self.assertEqual(status, 400)  # empty body -> missing fields
        from function import handler
        result = handler({"rawPath": "/users", "requestContext": {"http": {"method": "POST"}},
                          "headers": {"x-user-id": "adm001"}, "body": "{not json"})
        self.assertEqual(result["statusCode"], 400)
        self.assertEqual(json.loads(result["body"])["error"]["code"], "invalid_json")

    def test_base64_body_is_decoded(self) -> None:
        import base64
        from function import handler
        body = base64.b64encode(json.dumps({"first_name": "Bo"}).encode()).decode()
        result = handler({"rawPath": "/users/" + "x", "requestContext": {"http": {"method": "PATCH"}},
                          "headers": {"x-user-id": "adm001"}, "body": body, "isBase64Encoded": True})
        self.assertEqual(result["statusCode"], 404)

    def test_missing_or_unknown_user_header(self) -> None:
        self.error("GET", "/me", None, 401, "authentication_required")
        self.error("GET", "/me", "nobody", 401, "invalid_user")

    def test_unexpected_errors_become_500_without_details(self) -> None:
        router = Router()

        def broken(_request):
            raise RuntimeError("secret internal detail")
        router.add("GET", "/boom", broken)
        with self.assertLogs("app.router", level="ERROR"):
            result = router.dispatch({"rawPath": "/boom",
                                      "requestContext": {"http": {"method": "GET"}}})
        self.assertEqual(result["statusCode"], 500)
        self.assertNotIn("secret", result["body"])

    def test_error_details_and_204(self) -> None:
        router = Router()

        def fails(_request):
            raise ApiError(418, "teapot", "Short and stout.", {"spout": "yes"})
        router.add("GET", "/tea", fails)
        body = json.loads(router.dispatch({"rawPath": "/tea"})["body"])
        self.assertEqual(body["error"]["details"], {"spout": "yes"})
        self.assertNotIn("body", json_response(204))


class PasswordTests(unittest.TestCase):
    """Password hashing and rules."""

    def test_hash_and_verify(self) -> None:
        stored = hash_password("Secret123")
        self.assertNotIn("Secret123", stored)
        self.assertTrue(verify_password("Secret123", stored))
        self.assertFalse(verify_password("Wrong1234", stored))
        self.assertFalse(verify_password("Secret123", "garbage"))
        self.assertFalse(verify_password("Secret123", "md5$1$a$b"))

    def test_same_password_gets_different_hashes(self) -> None:
        self.assertNotEqual(hash_password("Secret123"), hash_password("Secret123"))

    def test_password_rules(self) -> None:
        self.assertIsNone(password_problem("Secret123"))
        self.assertIsNotNone(password_problem("short1"))
        self.assertIsNotNone(password_problem("lettersonly"))
        self.assertIsNotNone(password_problem(12345678))
        self.assertIsNotNone(password_problem("a1" * 70))
