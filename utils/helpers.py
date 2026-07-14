"""
Utility helper functions
"""

import uuid
import re
from datetime import datetime, timedelta


def generate_id():
    """Generate unique ID"""
    return str(uuid.uuid4())[:8]


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters"""
    if not text:
        return ""
    chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(chars)}])", r"\\\1", text)


def chunk_list(lst, chunk_size):
    """Split a list into chunks"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def format_time(seconds: int) -> str:
    """Format seconds into human readable time"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def parse_time_string(time_str: str) -> int:
    """Parse time string like '1h30m' to seconds"""
    total = 0
    pattern = re.findall(r'(\d+)([smhd])', time_str.lower())
    for value, unit in pattern:
        value = int(value)
        if unit == 's':
            total += value
        elif unit == 'm':
            total += value * 60
        elif unit == 'h':
            total += value * 3600
        elif unit == 'd':
            total += value * 86400
    return total


def get_readable_time(timestamp):
    """Get human readable time from timestamp"""
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return str(timestamp)
