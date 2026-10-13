"""
Company calendar: today's date and the Monday-based work week.

Other modules call clock.today() rather than date.today(), so tests can
freeze the date and every "this week" rule uses the same time zone.
"""

import logging
import os
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

WEEKLY_CAPACITY_HOURS = 40


# [COMPANY TIME ZONE HERE]
# How: The week resets at 12:00 AM Monday in the zone named by the
#      COMPANY_TIMEZONE environment variable (default America/New_York).
#      If the zone can't be loaded, it falls back to UTC and logs a warning.
# Why: Lambda runs in UTC, so without a fixed company zone the week would flip
#      over at 7-8 PM Sunday Eastern. Windows Python has no time zone data of
#      its own, which is why the tzdata package is in requirements.txt; the
#      fallback keeps the API running if it's missing.
def _company_zone() -> tzinfo:
    """
    Load the company time zone.

    Returns:
        The configured zone, or UTC if it can't be loaded.
    """
    name = os.getenv("COMPANY_TIMEZONE", "America/New_York")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("Time zone %s not found (install tzdata); using UTC.", name)
        return timezone.utc


COMPANY_ZONE = _company_zone()


def today() -> date:
    """
    Return today's date in the company time zone.

    Returns:
        The current company date.
    """
    return datetime.now(COMPANY_ZONE).date()


# [WEEK START HERE]
# How: Any date is mapped back to the Monday of its week (Monday = weekday 0).
# Why: Hour assignments belong to a week, and every employee's 40 hours start
#      fresh at 12:00 AM Monday, so the Monday date identifies the week.
def week_start_of(day: date) -> date:
    """
    Return the Monday of the week containing a date.

    Args:
        day: Any date.

    Returns:
        The Monday on or before that date.
    """
    return day - timedelta(days=day.weekday())


def current_week_start() -> date:
    """
    Return the Monday of the current company week.

    Returns:
        This week's Monday.
    """
    return week_start_of(today())
