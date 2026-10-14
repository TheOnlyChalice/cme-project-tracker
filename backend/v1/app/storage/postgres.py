"""
PostgreSQL storage: the real database used locally and on AWS (Aurora).

It offers the same methods as the in-memory store, so the business code
works unchanged. Values come back in the same Python types the rest of the
code expects: IDs, dates, and timestamps as strings, money and hours as Decimal.
"""

import json
import logging
import os
import re
import threading
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Iterator

from app.responses import ApiError

logger = logging.getLogger(__name__)

Record = dict[str, Any]

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
SCHEMA_FILE = Path(__file__).with_name("schema.sql")
SCHEMA_LOCK_ID = 724001

# [ACME: COLUMN TYPE MAP HERE]
# (The "# nosec B608" notes below tell the Bandit security scan that these
#  SQL strings are safe: table and column names only ever come from this map,
#  and every value is passed separately as a %s parameter.)
# How: Lists every column and its PostgreSQL type. Values are cast to these
#      types in SQL (e.g. %s::uuid) and converted back to strings on the way out.
# Why: The rest of the code treats IDs and dates as plain strings. Casting in
#      SQL makes PostgreSQL check each value's format, and the map doubles as an
#      allow-list of column names, so a table or column name can never be
#      injected into a query.
COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "id": "uuid", "username": "text", "first_name": "text", "last_name": "text",
        "email": "text", "password_hash": "text", "role": "text", "job_title": "text",
        "salary": "numeric", "profile_picture_url": "text", "manager_id": "uuid",
        "token_version": "integer", "failed_login_count": "integer", "locked_until": "timestamptz",
        "is_archived": "boolean", "archived_at": "timestamptz",
        "created_at": "timestamptz", "updated_at": "timestamptz",
    },
    "projects": {
        "id": "uuid", "name": "text", "description": "text", "start_date": "date",
        "end_date": "date", "allocated_hours": "integer", "budget": "numeric",
        "manager_id": "uuid", "active_milestone_id": "uuid", "status": "text",
        "is_archived": "boolean", "archived_at": "timestamptz", "created_by": "uuid",
        "created_at": "timestamptz", "updated_at": "timestamptz",
    },
    "milestones": {
        "id": "uuid", "project_id": "uuid", "sequence": "integer", "name": "text",
        "goal": "text", "deliverables": "jsonb", "start_date": "date", "end_date": "date",
        "status": "text", "completed_at": "timestamptz", "is_archived": "boolean",
        "archived_at": "timestamptz", "created_at": "timestamptz", "updated_at": "timestamptz",
    },
    "hour_assignments": {
        "id": "uuid", "user_id": "uuid", "milestone_id": "uuid", "project_id": "uuid",
        "week_start": "date", "hours": "numeric", "assigned_by": "uuid",
        "is_archived": "boolean", "archived_at": "timestamptz",
        "created_at": "timestamptz", "updated_at": "timestamptz",
    },
    "audit_log": {
        "id": "uuid", "actor_id": "uuid", "action": "text", "entity_type": "text",
        "entity_id": "uuid", "changes": "jsonb", "created_at": "timestamptz",
    },
}


def _json_default(value: Any) -> Any:
    """Convert values json can't handle (Decimals, dates) for JSONB columns."""
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _to_db(column_type: str, value: Any) -> Any:
    """
    Prepare a Python value for a column.

    Args:
        column_type: The column's PostgreSQL type.
        value: The Python value.

    Returns:
        A value psycopg can send.
    """
    if value is None:
        return None
    if column_type == "jsonb":
        return json.dumps(value, default=_json_default)
    return value


def _from_db(value: Any) -> Any:
    """
    Convert a database value back to the type the rest of the code uses.

    Args:
        value: The value psycopg returned.

    Returns:
        Strings for UUIDs, dates, and timestamps; everything else unchanged.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _columns(table: str) -> dict[str, str]:
    """
    Look up a table's columns, refusing unknown tables.

    Args:
        table: Table name.

    Returns:
        The column-to-type map.

    Raises:
        ValueError: If the table isn't known.
    """
    if table not in COLUMNS:
        raise ValueError(f"Unknown table: {table}")
    return COLUMNS[table]


class PostgresStore:
    """A store backed by PostgreSQL through psycopg 3."""

    backend_name = "postgres"
    APPEND_ONLY_TABLES = frozenset({"audit_log"})

    def __init__(self) -> None:
        """Prepare the store; the connection opens on first use."""
        self._conn: Any = None
        self._lock = threading.RLock()
        self._schema_ready = False

    # [ACME: DATABASE CONNECTION HERE]
    # How: One connection is opened on first use and reused for later requests,
    #      using the POSTGRES_* settings the workshop injects into Lambda (or
    #      your own locally). If it breaks, it's dropped and reopened next time.
    #      Every session uses UTC.
    # Why: Opening a connection is slow, and a warm Lambda handles many
    #      requests, so reusing one connection keeps requests fast. This is the
    #      same pattern as the workshop's postgres_service.py example. UTC keeps
    #      timestamps identical to the in-memory store's.
    def _connection(self) -> Any:
        """
        Return an open connection, reconnecting if needed.

        Returns:
            A psycopg connection.
        """
        import psycopg
        from psycopg.rows import dict_row

        if self._conn is None or self._conn.closed or self._conn.broken:
            self._conn = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASS", ""),
                dbname=os.getenv("POSTGRES_NAME", "postgres"),
                sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
                connect_timeout=10,
                autocommit=True,
                row_factory=dict_row,
            )
            self._conn.execute("SET TIME ZONE 'UTC'")
        return self._conn

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> list[Record]:
        """
        Run a query and return its rows, translating database errors.

        Args:
            query: SQL with %s placeholders.
            params: Values for the placeholders.

        Returns:
            Result rows converted to API types (empty for statements without rows).
        """
        import psycopg
        from psycopg import errors

        # [ACME: DATABASE ERROR TRANSLATION HERE]
        # How: Constraint errors from PostgreSQL become normal API errors
        #      (409 for duplicates and broken links, 400 for failed checks).
        #      Lost connections are dropped so the next request reconnects.
        # Why: The Python code checks these rules first, so these only fire in
        #      rare cases such as two requests racing each other. When they do,
        #      the client gets a clear error instead of a generic 500.
        try:
            with self._connection().cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall() if cursor.description else []
        except errors.UniqueViolation as exc:
            raise ApiError(409, "conflict", "That conflicts with an existing record.") from exc
        except errors.ForeignKeyViolation as exc:
            raise ApiError(409, "invalid_reference", "That refers to a record that doesn't exist.") from exc
        except errors.CheckViolation as exc:
            raise ApiError(400, "constraint_violation", "A value broke a database rule.") from exc
        except psycopg.OperationalError:
            self._conn = None
            raise
        return [{key: _from_db(value) for key, value in row.items()} for row in rows]

    # [ACME: SCHEMA SETUP HERE]
    # How: On first use, schema.sql runs inside a transaction holding a
    #      PostgreSQL advisory lock.
    # Why: Lambda can start several copies at once; the lock makes them take
    #      turns, so two copies never try to create the same table at the same
    #      moment. The script is safe to rerun, so no separate migration step
    #      is needed for this project.
    def ensure_schema(self) -> None:
        """Create any missing tables, indexes, and triggers."""
        if self._schema_ready:
            return
        with self._lock:
            connection = self._connection()
            with connection.transaction():
                connection.execute(f"SELECT pg_advisory_xact_lock({SCHEMA_LOCK_ID})")
                connection.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
            self._schema_ready = True

    def ping(self) -> bool:
        """
        Check that the database answers.

        Returns:
            True if a trivial query succeeds.
        """
        try:
            self._execute("SELECT 1 AS ok")
            return True
        except Exception:  # pylint: disable=broad-except
            logger.exception("Database ping failed")
            return False

    # [ACME: DATABASE TRANSACTION HERE]
    # How: Each request runs inside one PostgreSQL transaction. If the request
    #      raises any error, every change it made is rolled back. Nested calls
    #      become savepoints.
    # Why: Many actions write several rows (a change plus its audit entry, or a
    #      completed milestone plus released hours). They must all succeed or
    #      all fail, or the audit log and data could disagree.
    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run a block of work as one all-or-nothing unit."""
        with self._lock:
            with self._connection().transaction():
                yield

    # [ACME: ROW LOCK HERE]
    # How: SELECT ... FOR UPDATE locks a row until the transaction ends.
    # Why: Used before checking an employee's 40-hour cap and a project's hour
    #      budget. Without it, two managers booking the same person at the same
    #      instant could both pass the check and push them over 40.
    def lock_row(self, table: str, record_id: str) -> None:
        """
        Lock a row until the current transaction ends.

        Args:
            table: Table name.
            record_id: The row's ID.
        """
        _columns(table)
        if UUID_PATTERN.match(str(record_id)):
            self._execute(f'SELECT id FROM "{table}" WHERE id = %s::uuid FOR UPDATE',  # nosec B608
                          (record_id,))

    def lock_named(self, name: str) -> None:
        """
        Take a named PostgreSQL advisory lock until the transaction ends.

        Args:
            name: Any label, e.g. "seed".
        """
        self._execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (name,))

    def insert(self, table: str, record: Record) -> Record:
        """
        Add a record to a table.

        Args:
            table: Table name.
            record: The record to insert.

        Returns:
            The stored record.
        """
        columns = _columns(table)
        names = [name for name in record if name in columns]
        placeholders = ", ".join(f"%s::{columns[name]}" for name in names)
        query = (f'INSERT INTO "{table}" ({", ".join(names)}) '  # nosec B608
                 f"VALUES ({placeholders}) RETURNING *")
        return self._execute(query, tuple(_to_db(columns[n], record[n]) for n in names))[0]

    def get(self, table: str, record_id: str) -> Record | None:
        """
        Fetch one record by ID.

        Args:
            table: Table name.
            record_id: The record's ID.

        Returns:
            The record, or None if it doesn't exist or the ID isn't a valid UUID.
        """
        _columns(table)
        if not isinstance(record_id, str) or not UUID_PATTERN.match(record_id):
            return None
        rows = self._execute(f'SELECT * FROM "{table}" WHERE id = %s::uuid',  # nosec B608
                             (record_id,))
        return rows[0] if rows else None

    def find(self, table: str, predicate: Callable[[Record], bool] | None = None,
             where: dict[str, Any] | None = None) -> list[Record]:
        """
        Return records matching exact field values and an optional condition.

        Args:
            table: Table name.
            predicate: Extra filter function, applied in Python after the query.
            where: Field values that must match exactly; filtered in SQL.

        Returns:
            Matching records, oldest first.
        """
        # [ACME: SQL FILTERING HERE]
        # How: Exact-match conditions become a SQL WHERE clause, so PostgreSQL
        #      uses its indexes and returns only matching rows. Anything more
        #      complex (visibility rules, searches) runs as a Python check
        #      on those rows.
        # Why: The rules stay in one place (the services), shared by both
        #      backends, while the heavy filtering happens in the database.
        columns = _columns(table)
        clauses: list[str] = []
        params: list[Any] = []
        for name, value in (where or {}).items():
            if name not in columns:
                raise ValueError(f"Unknown column {name} on {table}")
            if value is None:
                clauses.append(f"{name} IS NULL")
                continue
            if columns[name] == "uuid" and not UUID_PATTERN.match(str(value)):
                return []
            clauses.append(f"{name} = %s::{columns[name]}")
            params.append(_to_db(columns[name], value))
        query = f'SELECT * FROM "{table}"'  # nosec B608
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at, id"
        rows = self._execute(query, tuple(params))
        return [r for r in rows if predicate is None or predicate(r)]

    def update(self, table: str, record_id: str, changes: Record) -> Record:
        """
        Apply changes to an existing record.

        Args:
            table: Table name.
            record_id: The record's ID.
            changes: Fields to overwrite.

        Returns:
            The updated record.

        Raises:
            PermissionError: If the table is append-only.
            KeyError: If the record doesn't exist.
        """
        if table in self.APPEND_ONLY_TABLES:
            raise PermissionError(f"Table '{table}' is append-only.")
        columns = _columns(table)
        names = [name for name in changes if name in columns and name != "id"]
        if not names:
            record = self.get(table, record_id)
            if record is None:
                raise KeyError(record_id)
            return record
        assignments = ", ".join(f"{name} = %s::{columns[name]}" for name in names)
        params = tuple(_to_db(columns[n], changes[n]) for n in names) + (record_id,)
        rows = self._execute(
            f'UPDATE "{table}" SET {assignments} WHERE id = %s::uuid RETURNING *',  # nosec B608
            params)
        if not rows:
            raise KeyError(record_id)
        return rows[0]

    def reset(self) -> None:
        """Delete all data (tests only; see the test database guard)."""
        self.ensure_schema()
        self._execute("TRUNCATE " + ", ".join(f'"{t}"' for t in COLUMNS) + " CASCADE")
