"""
MongoDB connection and data models for the Userbot SaaS
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from config import config
from utils.secure import encrypt_session, decrypt_session
from utils.logger import logger

_db = None
_client = None


async def init_mongo():
    """Initialize MongoDB connection"""
    global _client, _db
    _client = AsyncIOMotorClient(config.MONGO_URI)
    _db = _client.get_default_database()
    
    # Ensure indexes
    await _db.users.create_index("telegram_id", unique=True)
    await _db.users.create_index("session_string", sparse=True)
    await _db.sessions.create_index("telegram_id", unique=True)
    await _db.sessions.create_index("created_at", expireAfterSeconds=config.SESSION_EXPIRY_DAYS * 86400)
    await _db.plugins.create_index("telegram_id")
    await _db.auto_replies.create_index("telegram_id")
    await _db.notes.create_index("telegram_id")
    await _db.scheduled_messages.create_index("telegram_id")
    await _db.logs.create_index("timestamp", expireAfterSeconds=86400 * 7)  # 7 days
    await _db.welcome_messages.create_index("telegram_id")
    await _db.backups.create_index("telegram_id")
    
    logger.info("MongoDB indexes ensured")


async def close_mongo():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_db():
    """Get database instance"""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


# ---- User Models ----

async def create_user(telegram_id: int, phone: str, session_string: str, 
                      first_name: str = "", username: str = ""):
    """Create a new user entry"""
    db = get_db()
    encrypted_session = encrypt_session(session_string)
    
    user_data = {
        "telegram_id": telegram_id,
        "phone": phone,
        "first_name": first_name,
        "username": username,
        "session_string": encrypted_session,
        "is_active": True,
        "is_banned": False,
        "is_2fa_enabled": False,
        "joined_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
        "settings": {
            "ai_autoreply": False,
            "custom_autoreply": False,
            "afk": False,
            "auto_read": False,
            "auto_react": False,
            "afk_message": "I'm currently AFK. I'll reply soon!",
            "ai_personality": "friendly",
            "language": "en"
        },
        "stats": {
            "messages_sent": 0,
            "messages_received": 0,
            "auto_replies_sent": 0,
            "commands_used": 0
        }
    }
    
    await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": user_data},
        upsert=True
    )
    return telegram_id


async def get_user(telegram_id: int):
    """Get user by Telegram ID"""
    db = get_db()
    return await db.users.find_one({"telegram_id": telegram_id})


async def update_user(telegram_id: int, **kwargs):
    """Update user data"""
    db = get_db()
    kwargs["last_active"] = datetime.utcnow()
    return await db.users.update_one(
        {"telegram_id": telegram_id},
        {"$set": kwargs}
    )


async def get_all_users(active_only: bool = True):
    """Get all registered users"""
    db = get_db()
    query = {"is_active": True} if active_only else {}
    cursor = db.users.find(query)
    return await cursor.to_list(length=None)


async def delete_user(telegram_id: int):
    """Delete a user and all their data"""
    db = get_db()
    await db.users.delete_one({"telegram_id": telegram_id})
    await db.sessions.delete_one({"telegram_id": telegram_id})
    await db.plugins.delete_many({"telegram_id": telegram_id})
    await db.auto_replies.delete_many({"telegram_id": telegram_id})
    await db.notes.delete_many({"telegram_id": telegram_id})
    await db.scheduled_messages.delete_many({"telegram_id": telegram_id})
    await db.welcome_messages.delete_many({"telegram_id": telegram_id})
    return True


# ---- Session Models ----

async def save_session(telegram_id: int, session_string: str, phone: str):
    """Save encrypted session"""
    db = get_db()
    encrypted = encrypt_session(session_string)
    await db.sessions.update_one(
        {"telegram_id": telegram_id},
        {"$set": {
            "telegram_id": telegram_id,
            "session_string": encrypted,
            "phone": phone,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow()
        }},
        upsert=True
    )
    return True


async def get_session(telegram_id: int):
    """Get decrypted session string"""
    db = get_db()
    doc = await db.sessions.find_one({"telegram_id": telegram_id})
    if doc and doc.get("session_string"):
        return decrypt_session(doc["session_string"])
    return None


async def delete_session(telegram_id: int):
    """Delete session"""
    db = get_db()
    return await db.sessions.delete_one({"telegram_id": telegram_id})


# ---- Auto Reply Models ----

async def save_auto_reply(telegram_id: int, trigger: str, response: str, 
                          match_type: str = "exact", is_active: bool = True):
    """Save custom auto-reply rule"""
    db = get_db()
    return await db.auto_replies.update_one(
        {"telegram_id": telegram_id, "trigger": trigger},
        {"$set": {
            "telegram_id": telegram_id,
            "trigger": trigger,
            "response": response,
            "match_type": match_type,
            "is_active": is_active,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )


async def get_auto_replies(telegram_id: int):
    """Get all auto-replies for a user"""
    db = get_db()
    cursor = db.auto_replies.find({"telegram_id": telegram_id, "is_active": True})
    return await cursor.to_list(length=None)


async def delete_auto_reply(telegram_id: int, trigger: str):
    """Delete auto-reply rule"""
    db = get_db()
    return await db.auto_replies.delete_one({"telegram_id": telegram_id, "trigger": trigger})


# ---- Notes Models ----

async def save_note(telegram_id: int, name: str, content: str, 
                    note_type: str = "text", file_id: str = None):
    """Save a note"""
    db = get_db()
    return await db.notes.update_one(
        {"telegram_id": telegram_id, "name": name},
        {"$set": {
            "telegram_id": telegram_id,
            "name": name,
            "content": content,
            "note_type": note_type,
            "file_id": file_id,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )


async def get_note(telegram_id: int, name: str):
    """Get a specific note"""
    db = get_db()
    return await db.notes.find_one({"telegram_id": telegram_id, "name": name})


async def get_all_notes(telegram_id: int):
    """Get all notes for a user"""
    db = get_db()
    cursor = db.notes.find({"telegram_id": telegram_id})
    return await cursor.to_list(length=None)


async def delete_note(telegram_id: int, name: str):
    """Delete a note"""
    db = get_db()
    return await db.notes.delete_one({"telegram_id": telegram_id, "name": name})


# ---- Scheduled Messages Models ----

async def save_scheduled_message(telegram_id: int, chat_id: int, 
                                  message: str, schedule_at: datetime,
                                  repeat: str = "once", job_id: str = None):
    """Save a scheduled message"""
    db = get_db()
    return await db.scheduled_messages.insert_one({
        "telegram_id": telegram_id,
        "chat_id": chat_id,
        "message": message,
        "schedule_at": schedule_at,
        "repeat": repeat,
        "job_id": job_id or str(datetime.utcnow().timestamp()),
        "is_sent": False,
        "created_at": datetime.utcnow()
    })


async def get_pending_scheduled_messages():
    """Get all pending scheduled messages"""
    db = get_db()
    cursor = db.scheduled_messages.find({
        "is_sent": False,
        "schedule_at": {"$lte": datetime.utcnow()}
    })
    return await cursor.to_list(length=None)


async def mark_scheduled_sent(message_id):
    """Mark scheduled message as sent"""
    db = get_db()
    return await db.scheduled_messages.update_one(
        {"_id": message_id},
        {"$set": {"is_sent": True}}
    )


async def delete_scheduled_message(message_id):
    """Delete scheduled message"""
    db = get_db()
    return await db.scheduled_messages.delete_one({"_id": message_id})


# ---- Welcome/Goodbye Models ----

async def save_welcome_message(telegram_id: int, chat_id: int, 
                                message: str, is_active: bool = True):
    """Save welcome message for a group"""
    db = get_db()
    return await db.welcome_messages.update_one(
        {"telegram_id": telegram_id, "chat_id": chat_id},
        {"$set": {
            "telegram_id": telegram_id,
            "chat_id": chat_id,
            "message": message,
            "is_active": is_active,
            "is_welcome": True,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )


async def save_goodbye_message(telegram_id: int, chat_id: int, 
                                message: str, is_active: bool = True):
    """Save goodbye message for a group"""
    db = get_db()
    return await db.welcome_messages.update_one(
        {"telegram_id": telegram_id, "chat_id": chat_id},
        {"$set": {
            "telegram_id": telegram_id,
            "chat_id": chat_id,
            "message": message,
            "is_active": is_active,
            "is_welcome": False,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )


async def get_welcome_message(telegram_id: int, chat_id: int):
    """Get welcome/goodbye message for a group"""
    db = get_db()
    return await db.welcome_messages.find_one({
        "telegram_id": telegram_id,
        "chat_id": chat_id
    })


# ---- Plugin Management ----

async def set_plugin_state(telegram_id: int, plugin_name: str, enabled: bool):
    """Enable or disable a plugin for a user"""
    db = get_db()
    return await db.plugins.update_one(
        {"telegram_id": telegram_id, "plugin_name": plugin_name},
        {"$set": {
            "telegram_id": telegram_id,
            "plugin_name": plugin_name,
            "enabled": enabled,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )


async def get_plugin_state(telegram_id: int, plugin_name: str):
    """Get plugin state for a user"""
    db = get_db()
    doc = await db.plugins.find_one({"telegram_id": telegram_id, "plugin_name": plugin_name})
    return doc["enabled"] if doc else True  # Enabled by default


async def get_all_plugin_states(telegram_id: int):
    """Get all plugin states for a user"""
    db = get_db()
    cursor = db.plugins.find({"telegram_id": telegram_id})
    states = await cursor.to_list(length=None)
    return {s["plugin_name"]: s["enabled"] for s in states}


# ---- Backup/Restore ----

async def create_backup(telegram_id: int):
    """Create a backup of user data"""
    db = get_db()
    user = await get_user(telegram_id)
    auto_replies = await get_auto_replies(telegram_id)
    notes = await get_all_notes(telegram_id)
    
    backup = {
        "telegram_id": telegram_id,
        "user_data": user,
        "auto_replies": auto_replies,
        "notes": notes,
        "created_at": datetime.utcnow()
    }
    
    result = await db.backups.insert_one(backup)
    return str(result.inserted_id)


async def get_backup(telegram_id: int, backup_id: str = None):
    """Get backup"""
    from bson.objectid import ObjectId
    db = get_db()
    if backup_id:
        return await db.backups.find_one({"_id": ObjectId(backup_id), "telegram_id": telegram_id})
    cursor = db.backups.find({"telegram_id": telegram_id}).sort("created_at", -1).limit(1)
    backups = await cursor.to_list(length=1)
    return backups[0] if backups else None


# ---- Logging ----

async def add_log(telegram_id: int, action: str, details: str = ""):
    """Add a log entry"""
    db = get_db()
    return await db.logs.insert_one({
        "telegram_id": telegram_id,
        "action": action,
        "details": details,
        "timestamp": datetime.utcnow()
    })


async def get_logs(telegram_id: int, limit: int = 50):
    """Get logs for a user"""
    db = get_db()
    cursor = db.logs.find({"telegram_id": telegram_id}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)
