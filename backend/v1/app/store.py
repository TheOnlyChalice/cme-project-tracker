"""
Choose the storage backend once, at startup.

Everything else imports `store` from here and never needs to know whether
it's talking to PostgreSQL or to memory.
"""

import os

from app.storage.cache import CachedStore
from app.storage.memory import InMemoryStore


# [ACME: STORAGE SELECTION HERE]
# How: STORE_BACKEND=postgres or STORE_BACKEND=memory picks a backend
#      explicitly. If it isn't set, PostgreSQL is used whenever POSTGRES_HOST
#      is set (always true on Lambda, where the workshop injects it), and
#      memory otherwise.
# Why: Deployed code automatically uses the real database, while unit tests
#      and quick local runs still work with no database installed. The same
#      84 tests can also run against PostgreSQL by setting STORE_BACKEND.
def create_store():  # type: ignore[no-untyped-def]
    """
    Build the configured store.

    Returns:
        A PostgresStore or an InMemoryStore.
    """
    choice = os.getenv("STORE_BACKEND", "").strip().lower()
    if choice == "postgres" or (not choice and os.getenv("POSTGRES_HOST")):
        from app.storage.postgres import PostgresStore
        return CachedStore(PostgresStore())
    return CachedStore(InMemoryStore())


store = create_store()
