#!/usr/bin/env python3
"""
Telegram Userbot SaaS - Main Entry Point
A professional multi-user Telegram userbot with AI features
"""

import asyncio
import sys
from bot.userbot_manager import UserbotManager
from database.mongo import init_mongo, close_mongo
from database.redis_client import init_redis, close_redis
from utils.logger import setup_logger, logger

BANNER = """
╔══════════════════════════════════════════╗
║       Telegram Userbot SaaS v1.0        ║
║     Professional Multi-User Platform     ║
╚══════════════════════════════════════════╝
"""


async def main():
    print(BANNER)
    setup_logger()
    logger.info("Starting Userbot SaaS...")

    try:
        # Initialize database connections
        logger.info("Connecting to MongoDB...")
        await init_mongo()
        logger.info("✅ MongoDB connected")

        logger.info("Connecting to Redis...")
        await init_redis()
        logger.info("✅ Redis connected")

        # Start the userbot manager
        manager = UserbotManager()
        await manager.start()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Cleaning up...")
        await close_mongo()
        await close_redis()
        logger.info("✅ Cleanup complete. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
