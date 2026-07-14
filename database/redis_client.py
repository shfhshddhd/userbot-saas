"""
Redis connection for caching, rate limiting, and session storage
"""

import redis.asyncio as redis
from config import config
from utils.logger import logger

_redis = None


async def init_redis():
    """Initialize Redis connection"""
    global _redis
    try:
        _redis = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
            db=config.REDIS_DB,
            decode_responses=True
        )
        await _redis.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis not available (caching disabled): {e}")
        _redis = None


async def close_redis():
    """Close Redis connection"""
    global _redis
    if _redis:
        await _redis.close()
        logger.info("Redis connection closed")


def get_redis():
    """Get Redis instance"""
    return _redis


# ---- Cache Helpers ----

async def cache_get(key: str):
    """Get a cached value"""
    if not _redis:
        return None
    return await _redis.get(key)


async def cache_set(key: str, value: str, expiry: int = 300):
    """Set a cached value with expiry in seconds (default 5 min)"""
    if not _redis:
        return
    await _redis.setex(key, expiry, value)


async def cache_delete(key: str):
    """Delete a cached value"""
    if not _redis:
        return
    await _redis.delete(key)


# ---- Rate Limiting ----

async def check_rate_limit(key: str, limit: int = 5, window: int = 60):
    """Check if action is rate limited. Returns remaining actions."""
    if not _redis:
        return True, limit
    
    current = await _redis.get(f"ratelimit:{key}")
    if current is None:
        await _redis.setex(f"ratelimit:{key}", window, 1)
        return True, limit - 1
    
    count = int(current)
    if count >= limit:
        return False, 0
    
    await _redis.incr(f"ratelimit:{key}")
    return True, limit - count - 1


# ---- Online Status Cache ----

async def set_user_online(telegram_id: int):
    """Mark user as online for monitoring"""
    if not _redis:
        return
    await _redis.setex(f"online:{telegram_id}", 300, "1")  # 5 min expiry


async def is_user_online(telegram_id: int) -> bool:
    """Check if user is active"""
    if not _redis:
        return False
    return await _redis.exists(f"online:{telegram_id}") > 0


# ---- Queue System ----

async def push_to_queue(queue: str, data: str):
    """Push data to a Redis queue"""
    if not _redis:
        return
    await _redis.lpush(f"queue:{queue}", data)


async def pop_from_queue(queue: str):
    """Pop data from Redis queue (blocking)"""
    if not _redis:
        return None
    _, data = await _redis.brpop(f"queue:{queue}", timeout=5)
    return data
