"""Small shared helpers for IDs and timestamps."""

import uuid
from datetime import datetime, timezone


# [ID AND TIMESTAMP HELPERS HERE]
# How: IDs are random UUID4 strings; timestamps are UTC in ISO 8601 format.
# Why: The data model specifies UUID primary keys. Storing every timestamp in
#      UTC avoids time zone bugs, since Lambda runs in UTC and your PC doesn't.
def new_id() -> str:
    """
    Generate a new UUID string.

    Returns:
        A random UUID4, e.g. "3f2b8c1e-...".
    """
    return str(uuid.uuid4())


def now_iso() -> str:
    """
    Return the current UTC time as an ISO 8601 string.

    Returns:
        A timestamp such as "2026-10-13T17:03:15.123456+00:00".
    """
    return datetime.now(timezone.utc).isoformat()
