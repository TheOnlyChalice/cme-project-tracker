"""
In-memory storage for Phase 1.

Every read and write goes through this module, so it is the only file that
changes when PostgreSQL replaces in-memory storage.
"""

import copy
import threading
from typing import Any, Callable

Record = dict[str, Any]


# [IN-MEMORY STORAGE HERE]
# How: Each table is a dict of {id: record}. Records are deep-copied on the way
#      in and out, and a lock guards every operation.
# Why: Copying means code outside the store can't change stored data by
#      accident, which mimics how a real database behaves. The lock matters
#      because the local dev server handles requests on multiple threads.
#      Keeping the interface small (insert/get/find/update) makes swapping in
#      PostgreSQL later a change to this file only.
class InMemoryStore:
    """A minimal table-based store held in memory."""

    # [APPEND-ONLY AUDIT HERE]
    # How: Tables listed here reject update() calls, and the store has no
    #      delete method at all.
    # Why: The requirements say no one can edit or delete an audit entry, not
    #      even an admin. Enforcing it in storage means no route can bypass it.
    APPEND_ONLY_TABLES = frozenset({"audit_log"})

    def __init__(self) -> None:
        """Create an empty store."""
        self._tables: dict[str, dict[str, Record]] = {}
        self._lock = threading.RLock()

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

    def find(self, table: str, predicate: Callable[[Record], bool] | None = None) -> list[Record]:
        """
        Return all records in a table that match a condition.

        Args:
            table: Table name.
            predicate: Optional filter function; all records if omitted.

        Returns:
            Copies of the matching records, in insertion order.
        """
        with self._lock:
            rows = self._tables.get(table, {}).values()
            return [copy.deepcopy(r) for r in rows if predicate is None or predicate(r)]

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


store = InMemoryStore()
