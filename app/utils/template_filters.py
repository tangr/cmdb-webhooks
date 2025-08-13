from datetime import datetime, timezone
from typing import Union


def time_to_str(timestamp: Union[int, float, str]) -> str:
    """Convert timestamp to formatted string: 2006-01-02 15:04:05 Mon +0000"""
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # Format: 2006-01-02 15:04:05 Mon +0000
        return dt.strftime("%Y-%m-%d %H:%M:%S %a %z")
    except (ValueError, TypeError, OSError):
        return str(timestamp)


def time_diff_now(timestamp: Union[int, float, str]) -> str:
    """Calculate time difference from now, returns human readable string"""
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = now - dt

        total_seconds = int(diff.total_seconds())

        if total_seconds < 0:
            # Future time
            total_seconds = abs(total_seconds)
            suffix = " from now"
        else:
            suffix = " ago"

        # Calculate time units
        if total_seconds < 60:
            return f"{total_seconds} secs{suffix}"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} mins{suffix}"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours} hours{suffix}"
        elif total_seconds < 2592000:  # 30 days
            days = total_seconds // 86400
            return f"{days} days{suffix}"
        elif total_seconds < 31536000:  # 365 days
            months = total_seconds // 2592000
            return f"{months} months{suffix}"
        else:
            years = total_seconds // 31536000
            return f"{years} years{suffix}"

    except (ValueError, TypeError, OSError):
        return str(timestamp)
