"""
In-memory storage: used by the unit tests and for quick local runs.

It behaves like the PostgreSQL store (same methods, same transaction
rollback), so the business code never needs to know which one it's using.
"""

import copy
import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator

Record = dict[str, Any]


class InMemoryStore:
    """A minimal table-based store held in memory."""

    backend_name = "memory"

    # [APPEND-ONLY AUDIT HERE]
    # How: Tables listed here reject update() calls, and the store has no
    #      delete method at all. PostgreSQL adds a database trigger on top.
    # Why: The requirements say no one can edit or delete an audit entry, not
    #      even an admin. Enforcing it in storage means no route can bypass it.
    APPEND_ONLY_TABLES = frozenset({"audit_log"})

    def __init__(self) -> None:
        """Create an empty store."""
        self._tables: dict[str, dict[str, Record]] = {}
        self._lock = threading.RLock()
        self._depth = 0

    def ensure_schema(self) -> None:
        """Nothing to create for in-memory storage."""

    def ping(self) -> bool:
        """
        Report whether storage is reachable.

        Returns:
            Always True for in-memory storage.
        """
        return True

    # [MEMORY TRANSACTION HERE]
    # How: The outermost transaction snapshots every table; if the request
    #      raises an error, the snapshot is put back. The lock is held for the
    #      whole request, so dev server threads run one request at a time.
    # Why: Matches PostgreSQL's all-or-nothing behavior, so a request that
    #      fails halfway (for example, after writing a record but before its
    #      audit entry) never leaves partial changes behind in either backend.
    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run a block of work as one all-or-nothing unit."""
        with self._lock:
            snapshot = copy.deepcopy(self._tables) if self._depth == 0 else None
            self._depth += 1
            try:
                yield
            except BaseException:
                if snapshot is not None:
                    self._tables = snapshot
                raise
            finally:
                self._depth -= 1

    def lock_row(self, table: str, record_id: str) -> None:
        """
        Lock a row until the transaction ends (a no-op here).

        Args:
            table: Table name.
            record_id: The row's ID.
        """
        # Requests already run one at a time inside transaction().

    def lock_named(self, name: str) -> None:
        """
        Take a named lock until the transaction ends (a no-op here).

        Args:
            name: Any label, e.g. "seed".
        """

    def insert(self, table: str, record: Record) -> Record:
        """
        Add a record to a table.

        Args:
            table: Table name, e.g. "users".
            record: The record, which must contain an "id".

        Returns:
            A copy of the stored record.
        """
        with self._lock:
            rows = self._tables.setdefault(table, {})
            rows[record["id"]] = copy.deepcopy(record)
            return copy.deepcopy(rows[record["id"]])

    def get(self, table: str, record_id: str) -> Record | None:
        """
        Fetch one record by ID.

        Args:
            table: Table name.
            record_id: The record's ID.

        Returns:
            A copy of the record, or None if it doesn't exist.
        """
        with self._lock:
            record = self._tables.get(table, {}).get(record_id)
            return copy.deepcopy(record) if record else None

    def find(self, table: str, predicate: Callable[[Record], bool] | None = None,
             where: dict[str, Any] | None = None) -> list[Record]:
        """
        Return records matching exact field values and an optional condition.

        Args:
            table: Table name.
            where: Field values that must match exactly (None matches empty).
            predicate: Extra filter function, applied after `where`.

        Returns:
            Copies of the matching records, in insertion order.
        """
        conditions = where or {}
        with self._lock:
            rows = self._tables.get(table, {}).values()
            return [copy.deepcopy(r) for r in rows
                    if all(r.get(k) == v for k, v in conditions.items())
                    and (predicate is None or predicate(r))]

    def update(self, table: str, record_id: str, changes: Record) -> Record:
        """
        Apply changes to an existing record.

        Args:
            table: Table name.
            record_id: The record's ID.
            changes: Fields to overwrite.

        Returns:
            A copy of the updated record.

        Raises:
            PermissionError: If the table is append-only.
            KeyError: If the record doesn't exist.
        """
        if table in self.APPEND_ONLY_TABLES:
            raise PermissionError(f"Table '{table}' is append-only.")
        with self._lock:
            record = self._tables[table][record_id]
            record.update(copy.deepcopy(changes))
            return copy.deepcopy(record)

    def reset(self) -> None:
        """Remove all data. Used by tests to start each case from a clean state."""
        with self._lock:
            self._tables.clear()
