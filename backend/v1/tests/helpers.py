"""Shared test setup: a frozen calendar, fresh data, and a request helper."""

import json
import os
import unittest
from datetime import date, timedelta
from typing import Any
from unittest import mock

from app import clock
from app.seed import seed_data, seed_id
from app.store import store
from function import handler

# A Wednesday, so "this week" started on Monday 2026-10-12.
FROZEN_TODAY = date(2026, 10, 14)
THIS_MONDAY = "2026-10-12"
NEXT_MONDAY = "2026-10-19"
LAST_MONDAY = "2026-10-05"


# [TEST BASE HERE]
# How: Every test freezes "today" to a fixed Wednesday, wipes the in-memory
#      store, and reloads the seed data, then calls handler() exactly the way
#      Lambda would.
# Why: A fixed date makes week and deadline rules give the same answer every
#      run, a fresh store stops tests affecting each other, and going through
#      handler() tests routing, permissions, and responses together.
class ApiTestCase(unittest.TestCase):
    """Base class for API tests."""

    @classmethod
    def setUpClass(cls) -> None:
        """Refuse to wipe a real database, then make sure tables exist."""
        # [TEST DATABASE GUARD HERE]
        # How: When the tests run against PostgreSQL, the database name must
        #      end in "_test", or every test stops before touching it.
        # Why: Each test empties every table before it starts. This makes it
        #      impossible to wipe your real development data by running the
        #      tests with the wrong settings.
        if store.backend_name == "postgres":
            name = os.getenv("POSTGRES_NAME", "")
            if not name.endswith("_test"):
                raise RuntimeError(
                    f"Refusing to run tests against database '{name}'. "
                    "Use a database whose name ends in _test.")
        store.ensure_schema()

    def setUp(self) -> None:
        """Freeze the date and load fresh seed data."""
        patcher = mock.patch.object(clock, "today", return_value=FROZEN_TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        store.reset()
        seed_data()

    def call(self, method: str, path: str, user: str | None = None,
             body: Any = None, query: dict[str, str] | None = None) -> tuple[int, Any]:
        """
        Send a request through the Lambda handler.

        Args:
            method: HTTP method.
            path: Path after /api/v1, e.g. "/projects".
            user: Username or ID for the X-User-Id header.
            body: JSON body, if any.
            query: Query parameters, if any.

        Returns:
            (status code, parsed JSON body or None).
        """
        event = {
            "rawPath": "/api/v1" + path,
            "requestContext": {"http": {"method": method}},
            "headers": {"x-user-id": user} if user else {},
            "body": json.dumps(body) if body is not None else None,
            "queryStringParameters": query,
        }
        result = handler(event)
        return result["statusCode"], json.loads(result["body"]) if result.get("body") else None

    def ok(self, method: str, path: str, user: str | None = None,
           body: Any = None, query: dict[str, str] | None = None, expected: int = 200) -> Any:
        """
        Send a request and assert the status code.

        Returns:
            The parsed response body.
        """
        status, data = self.call(method, path, user, body, query)
        self.assertEqual(status, expected, data)
        return data

    def error(self, method: str, path: str, user: str | None, status: int,
              code: str | None = None, body: Any = None) -> Any:
        """
        Send a request that should fail and check the error.

        Returns:
            The error object.
        """
        got, data = self.call(method, path, user, body)
        self.assertEqual(got, status, data)
        if code:
            self.assertEqual(data["error"]["code"], code, data)
        return data["error"]


def uid(username: str) -> str:
    """Return a seed user's fixed ID."""
    return seed_id(username)


PORTAL = seed_id("project:portal")
MIGRATION = seed_id("project:migration")
PORTAL_M1 = seed_id("milestone:portal:1")
PORTAL_M2 = seed_id("milestone:portal:2")
PORTAL_M3 = seed_id("milestone:portal:3")
MIGRATION_M1 = seed_id("milestone:migration:1")
MIGRATION_M2 = seed_id("milestone:migration:2")


def day(offset: int) -> str:
    """A date relative to the frozen today, as YYYY-MM-DD."""
    return (FROZEN_TODAY + timedelta(days=offset)).isoformat()
