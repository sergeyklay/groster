from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from groster.constants import TZ


def format_timestamp(ts: int | float | str | None, to_tz: str = TZ) -> str:
    """Convert a UNIX timestamp in milliseconds to a human-readable datetime string.

    Args:
        ts: UNIX timestamp in milliseconds. Returns "N/A" if 0 or None.
        to_tz: Target timezone string. Defaults to TZ constant.

    Returns:
        Formatted datetime string in "YYYY-MM-DD HH:MM:SS" format, or "N/A" for
        invalid timestamps.

    Raises:
        ValueError: If timestamp is not a valid integer or float.
    """
    if ts is None or ts == 0 or ts == "0":
        return "N/A"

    if isinstance(ts, str):
        ts = int(ts)

    if not isinstance(ts, (int, float)):
        raise ValueError(f"Timestamp must be a valid integer or float. Got: {type(ts)}")

    dt_utc = datetime.fromtimestamp(ts / 1000, tz=UTC)
    target_tz = ZoneInfo(to_tz)
    dt_local = dt_utc.astimezone(target_tz)

    return dt_local.strftime("%Y-%m-%d %H:%M:%S")
