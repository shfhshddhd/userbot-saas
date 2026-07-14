import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "UserbotSaaS")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", 0))

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/userbot_saas")

    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    # Security
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").encode()
    
    # AI
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")

    # Limits
    SESSION_EXPIRY_DAYS = int(os.getenv("SESSION_EXPIRY_DAYS", 30))
    MAX_USERS = int(os.getenv("MAX_USERS", 1000))


config = Config()
