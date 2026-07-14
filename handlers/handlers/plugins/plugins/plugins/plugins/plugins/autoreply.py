"""
Custom Auto-Reply Plugin
Users can set custom trigger-response rules
"""

from plugins.base import BasePlugin
from database.mongo import get_auto_replies, add_log, update_user
from utils.logger import logger
import re


class AutoReplyPlugin(BasePlugin):
    name = "autoreply"
    description = "Custom auto-reply rules with trigger matching"
    version = "1.0.0"
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type in ["private_message", "group_message"]:
            await self._check_auto_reply(telegram_id, event)
    
    async def _check_auto_reply(self, telegram_id: int, event):
        """Check message against auto-reply rules"""
        if event.out:
            return
        
        user = None
        
        # Get user's auto-reply rules
        rules = await get_auto_replies(telegram_id)
        if not rules:
            return
        
        message_text = event.text or ""
        if not message_text:
            return
        
        for rule in rules:
            trigger = rule.get("trigger", "").lower()
            response = rule.get("response", "")
            match_type = rule.get("match_type", "exact")
            
            matched = False
            
            if match_type == "exact":
                matched = message_text.lower() == trigger
            elif match_type == "contains":
                matched = trigger in message_text.lower()
            elif match_type == "startswith":
                matched = message_text.lower().startswith(trigger)
            elif match_type == "endswith":
                matched = message_text.lower().endswith(trigger)
            elif match_type == "regex":
                try:
                    matched = bool(re.search(trigger, message_text, re.IGNORECASE))
                except:
                    matched = False
            
            if matched:
                try:
                    client = self.get_user_client(telegram_id)
                    if client:
                        await client.send_message(event.chat_id, response, reply_to=event.id)
                        
                        # Update stats
                        user = await get_user_from_db(telegram_id)
                        if user:
                            stats = user.get("stats", {})
                            stats["auto_replies_sent"] = stats.get("auto_replies_sent", 0) + 1
                            await update_user(telegram_id, stats=stats)
                        
                        await add_log(telegram_id, "auto_reply", f"Trigger: {trigger}")
                        break
                except Exception as e:
                    logger.error(f"Auto-reply error for {telegram_id}: {e}")


# Helper to avoid circular import
from database.mongo import get_user as get_user_from_db
