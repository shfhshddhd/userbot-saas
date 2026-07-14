"""
Auto-Read Plugin
Automatically marks messages as read
"""

from plugins.base import BasePlugin
from database.mongo import get_user, add_log
from utils.logger import logger


class AutoReadPlugin(BasePlugin):
    name = "autoread"
    description = "Auto-read messages when user is offline"
    version = "1.0.0"
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type in ["private_message", "group_message"]:
            await self._auto_read(telegram_id, event)
    
    async def _auto_read(self, telegram_id: int, event):
        """Auto-read incoming messages"""
        if event.out:
            return
        
        user = await get_user(telegram_id)
        if not user:
            return
        
        settings = user.get("settings", {})
        if not settings.get("auto_read", False):
            return
        
        try:
            client = self.get_user_client(telegram_id)
            if client:
                await client.send_read_acknowledge(event.chat_id, clear_mentions=True)
        except Exception as e:
            logger.error(f"Auto-read error for {telegram_id}: {e}")
