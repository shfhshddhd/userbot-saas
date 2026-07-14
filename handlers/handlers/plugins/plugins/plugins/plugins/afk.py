"""
AFK (Away From Keyboard) Plugin
Automatically replies when user is offline
"""

from telethon import events
from datetime import datetime
from plugins.base import BasePlugin
from database.mongo import get_user, update_user, add_log
from utils.logger import logger


class AFKPlugin(BasePlugin):
    name = "afk"
    description = "AFK mode - auto-reply when offline"
    version = "1.0.0"
    
    def __init__(self, manager):
        super().__init__(manager)
        self.afk_users = {}  # telegram_id -> {message, start_time}
        
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type in ["private_message", "group_message"]:
            await self._check_afk_reply(telegram_id, event)
    
    async def _check_afk_reply(self, telegram_id: int, event):
        """Check if user is AFK and reply on their behalf"""
        # Get user settings
        user = await get_user(telegram_id)
        if not user:
            return
        
        settings = user.get("settings", {})
        if not settings.get("afk", False):
            return
        
        # Don't reply to self
        if event.out:
            return
        
        # Get AFK data
        afk_data = self.afk_users.get(telegram_id)
        if not afk_data:
            return
        
        # Check if message is sent by the user (deactivates AFK)
        client = self.get_user_client(telegram_id)
        if client and event.sender_id == client.me.id:
            # User is back!
            duration = datetime.now() - afk_data["start_time"]
            hours = duration.total_seconds() / 3600
            self.afk_users.pop(telegram_id, None)
            await update_user(telegram_id, settings={**settings, "afk": False})
            logger.info(f"User {telegram_id} is back from AFK")
            return
        
        # Don't reply to AFK in groups unless mentioned
        if event.is_group:
            me = None
            client = self.get_user_client(telegram_id)
            if client:
                me = await client.get_me()
            if me and (not event.mentioned and me.id not in [e.id for e in event.message.entities if hasattr(e, 'user_id')]):
                return
        
        # Send AFK reply
        try:
            duration = datetime.now() - afk_data["start_time"]
            minutes = int(duration.total_seconds() / 60)
            
            reply_text = f"😴 **AFK**\n{afk_data['message']}\n\n⏱ Since: {minutes} minutes ago"
            
            client = self.get_user_client(telegram_id)
            if client:
                await client.send_message(event.chat_id, reply_text, reply_to=event.id)
                await add_log(telegram_id, "afk_reply", f"Replied to {event.sender_id}")
        except Exception as e:
            logger.error(f"AFK reply error for {telegram_id}: {e}")
    
    async def set_afk(self, telegram_id: int, message: str = "I'm currently AFK. I'll reply soon!"):
        """Set AFK mode for a user"""
        user = await get_user(telegram_id)
        if not user:
            return False
        
        settings = user.get("settings", {})
        settings["afk"] = True
        settings["afk_message"] = message
        
        self.afk_users[telegram_id] = {
            "message": message,
            "start_time": datetime.now()
        }
        
        await update_user(telegram_id, settings=settings)
        await add_log(telegram_id, "afk_set", message[:50])
        return True
    
    async def unset_afk(self, telegram_id: int):
        """Remove AFK mode"""
        user = await get_user(telegram_id)
        if not user:
            return False
        
        settings = user.get("settings", {})
        settings["afk"] = False
        self.afk_users.pop(telegram_id, None)
        
        await update_user(telegram_id, settings=settings)
        await add_log(telegram_id, "afk_unset", "AFK mode removed")
        return True
