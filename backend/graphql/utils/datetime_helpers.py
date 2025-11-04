"""DateTime utility functions for GraphQL resolvers."""

from datetime import datetime


def parse_datetime_to_naive_utc(dt_string: str) -> datetime:
    """Parse ISO datetime string to naive UTC datetime.

    Handles both aware (with Z or timezone) and naive datetime strings.
    Always returns a naive datetime for consistency with repository layer.

    Args:
        dt_string: ISO format datetime string (e.g., "2025-10-21T00:00:00Z")

    Returns:
        Naive datetime object in UTC

    Examples:
        >>> parse_datetime_to_naive_utc("2025-10-21T00:00:00Z")
        datetime(2025, 10, 21, 0, 0)
        >>> parse_datetime_to_naive_utc("2025-10-21T00:00:00")
        datetime(2025, 10, 21, 0, 0)
    """
    # Parse string to datetime
    if dt_string.endswith("Z"):
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    else:
        dt = datetime.fromisoformat(dt_string)

    # Convert to naive UTC
    if dt.tzinfo is not None:
        # Already aware, convert to UTC and remove tzinfo
        dt = dt.replace(tzinfo=None)

    return dt
