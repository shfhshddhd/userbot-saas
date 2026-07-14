"""
Plugin utility functions
"""

from database.mongo import get_user, update_user
from utils.logger import logger


async def ensure_user(telegram_id: int) -> bool:
    """Check if user exists and is active"""
    user = await get_user(telegram_id)
    if not user:
        return False
    if user.get("is_banned", False):
        return False
    return True


async def increment_stat(telegram_id: int, stat_name: str, amount: int = 1):
    """Increment a user stat"""
    user = await get_user(telegram_id)
    if not user:
        return
    
    stats = user.get("stats", {})
    stats[stat_name] = stats.get(stat_name, 0) + amount
    await update_user(telegram_id, stats=stats)
