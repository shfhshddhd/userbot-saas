"""
Auto-React Plugin
Automatically reacts to messages with emoji
"""

from plugins.base import BasePlugin
from database.mongo import get_user, add_log
from utils.logger import logger


class AutoReactPlugin(BasePlugin):
    name = "autoreact"
    description = "Auto-react to messages with emoji"
    version = "1.0.0"
    
    # Common reactions
    emoji_map = {
        "like": "👍",
        "love": "❤️",
        "laugh": "😂",
        "wow": "😮",
        "sad": "😢",
        "angry": "😡",
        "fire": "🔥",
        "clap": "👏",
        "ok": "👌",
        "eyes": "👀"
    }
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type in ["private_message", "group_message"]:
            await self._auto_react(telegram_id, event)
    
    async def _auto_react(self, telegram_id: int, event):
        """Auto-react to incoming messages"""
        if event.out:
            return
        
        user = await get_user(telegram_id)
        if not user:
            return
        
        settings = user.get("settings", {})
        auto_react = settings.get("auto_react", False)
        
        if not auto_react:
            return
        
        # Default emoji
        emoji = settings.get("auto_react_emoji", "👍")
        
        try:
            client = self.get_user_client(telegram_id)
            if client:
                await client.send_reaction(event.chat_id, event.id, emoji)
        except Exception as e:
            logger.error(f"Auto-react error for {telegram_id}: {e}")
    
    async def set_react(self, telegram_id: int, enabled: bool, emoji: str = "👍"):
        """Set auto-react preferences"""
        from database.mongo import update_user
        user = await get_user(telegram_id)
        if not user:
            return False
        
        settings = user.get("settings", {})
        settings["auto_react"] = enabled
        settings["auto_react_emoji"] = emoji
        await update_user(telegram_id, settings=settings)
        return True
