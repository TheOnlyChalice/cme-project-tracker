"""A per-request read cache that sits in front of either storage backend."""

import threading
from contextlib import contextmanager
from typing import Any, Callable, Iterator

Record = dict[str, Any]

# Tables read whole and kept for the rest of the request. The audit log is
# left out: it only grows, and is read with its own filters.
CACHED_TABLES = frozenset({"users", "projects", "milestones", "hour_assignments"})


# [ACME: REQUEST READ CACHE HERE]
# How: Inside a request, the first read of a table loads all of it in one
#      query; every later read in that request (by ID or by matching fields)
#      is answered from that copy. Any write to a table, any row lock, and the
#      end of the request throw the copy away, so the next read is fresh.
# Why: Reports like the dashboard check every project, milestone, and booking.
#      With ~1,000 records that meant about 750 separate database round trips
#      per page (seconds on Lambda and Aurora); now it is a handful. Dropping
#      the copy before a row lock means the 40-hour check always counts the
#      very latest bookings, so the double-booking protection still holds.
class CachedStore:
    """Wraps a store and caches whole-table reads for the length of a request."""

    def __init__(self, inner: Any) -> None:
        """
        Wrap a storage backend.

        Args:
            inner: The PostgreSQL or in-memory store.
        """
        self._inner = inner
        self._local = threading.local()

    def __getattr__(self, name: str) -> Any:
        """Pass anything not handled here straight to the real store."""
        return getattr(self._inner, name)

    @property
    def backend_name(self) -> str:
        """The wrapped backend's name ("postgres" or "memory")."""
        return self._inner.backend_name

    def _state(self) -> Any:
        """This thread's cache state."""
        if not hasattr(self._local, "depth"):
            self._local.depth = 0
            self._local.tables = {}
        return self._local

    def _clear(self, table: str | None = None) -> None:
        """Forget cached rows for one table, or all of them."""
        state = self._state()
        if table is None:
            state.tables = {}
        else:
            state.tables.pop(table, None)

    def _rows(self, table: str) -> list[Record] | None:
        """Cached rows for a table, loading them if needed (only inside a request)."""
        state = self._state()
        if state.depth == 0 or table not in CACHED_TABLES:
            return None
        if table not in state.tables:
            rows = self._inner.find(table)
            state.tables[table] = (rows, {row["id"]: row for row in rows})
        return state.tables[table][0]

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Run work as one unit; the cache lives exactly as long as the outer unit."""
        state = self._state()
        state.depth += 1
        try:
            with self._inner.transaction():
                yield
        finally:
            state.depth -= 1
            if state.depth == 0:
                self._clear()

    def get(self, table: str, record_id: str) -> Record | None:
        """Fetch one record by ID, from the request cache when possible."""
        rows = self._rows(table)
        if rows is None:
            return self._inner.get(table, record_id)
        row = self._state().tables[table][1].get(record_id)
        return dict(row) if row else None

    def find(self, table: str, predicate: Callable[[Record], bool] | None = None,
             where: dict[str, Any] | None = None) -> list[Record]:
        """Find matching records, from the request cache when possible."""
        rows = self._rows(table)
        if rows is None:
            return self._inner.find(table, predicate, where=where)
        conditions = where or {}
        return [dict(r) for r in rows
                if all(r.get(k) == v for k, v in conditions.items())
                and (predicate is None or predicate(r))]

    def insert(self, table: str, record: Record) -> Record:
        """Insert, then drop that table's cached rows."""
        self._clear(table)
        return self._inner.insert(table, record)

    def update(self, table: str, record_id: str, changes: Record) -> Record:
        """Update, then drop that table's cached rows."""
        self._clear(table)
        return self._inner.update(table, record_id, changes)

    def lock_row(self, table: str, record_id: str) -> None:
        """Lock a row, then drop every cached table so later checks read fresh data."""
        self._inner.lock_row(table, record_id)
        self._clear()

    def lock_named(self, name: str) -> None:
        """Take a named lock, then drop every cached table."""
        self._inner.lock_named(name)
        self._clear()

    def reset(self) -> None:
        """Delete all data (tests only) and clear the cache."""
        self._clear()
        self._inner.reset()
