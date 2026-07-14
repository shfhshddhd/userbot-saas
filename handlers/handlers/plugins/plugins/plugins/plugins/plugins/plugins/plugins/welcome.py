"""
Welcome/Goodbye Messages Plugin
"""

from telethon import events
from telethon.tl.types import MessageActionChatAddUser, MessageActionChatDeleteUser
from plugins.base import BasePlugin
from database.mongo import (
    save_welcome_message, save_goodbye_message, 
    get_welcome_message, add_log
)
from utils.logger import logger


class WelcomePlugin(BasePlugin):
    name = "welcome"
    description = "Welcome and goodbye messages for groups"
    version = "1.0.0"
    
    async def on_load(self):
        @self.bot.on(events.NewMessage(pattern=r'^/setwelcome'))
        async def setwelcome_command(event):
            await self._handle_setwelcome(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/setgoodbye'))
        async def setgoodbye_command(event):
            await self._handle_setgoodbye(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/delwelcome$'))
        async def delwelcome_command(event):
            await self._handle_delwelcome(event)
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type == "chat_action":
            await self._handle_chat_action(telegram_id, event)
    
    async def _handle_chat_action(self, telegram_id: int, event):
        """Handle user join/leave in groups"""
        if not event.user_added and not event.user_kicked:
            return
        
        client = self.get_user_client(telegram_id)
        if not client:
            return
        
        chat_id = event.chat_id
        action = event.action_message.action
        
        # Check welcome/goodbye settings
        settings = await get_welcome_message(telegram_id, chat_id)
        if not settings or not settings.get("is_active"):
            return
        
        try:
            if isinstance(action, MessageActionChatAddUser):
                # User joined
                if settings.get("is_welcome", True):
                    new_users = action.users
                    for user_id in new_users:
                        await client.send_message(
                            chat_id,
                            settings["message"].replace("{name}", f"[user](tg://user?id={user_id})")
                        )
            
            elif isinstance(action, MessageActionChatDeleteUser):
                # User left
                if not settings.get("is_welcome", True):
                    user_id = action.user_id
                    await client.send_message(
                        chat_id,
                        settings["message"].replace("{name}", f"[user](tg://user?id={user_id})")
                    )
        
        except Exception as e:
            logger.error(f"Welcome/goodbye error for {telegram_id}: {e}")
    
    async def _handle_setwelcome(self, event):
        """Set welcome message for this group"""
        telegram_id = event.sender_id
        text = event.text
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply(
                "📋 **Usage:** `/setwelcome [message]`\n"
                "Use `{name}` as placeholder for the new user's name.\n\n"
                "Example: `/setwelcome Welcome {name} to our group! 🎉`"
            )
            return
        
        message = parts[1]
        await save_welcome_message(telegram_id, event.chat_id, message)
        await event.reply(f"✅ **Welcome message set!**\n\n{message}")
    
    async def _handle_setgoodbye(self, event):
        """Set goodbye message for this group"""
        telegram_id = event.sender_id
        text = event.text
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply(
                "📋 **Usage:** `/setgoodbye [message]`\n"
                "Use `{name}` as placeholder.\n\n"
                "Example: `/setgoodbye Goodbye {name}! We'll miss you.`"
            )
            return
        
        message = parts[1]
        await save_goodbye_message(telegram_id, event.chat_id, message)
        await event.reply(f"✅ **Goodbye message set!**\n\n{message}")
    
    async def _handle_delwelcome(self, event):
        """Delete welcome/goodbye message for this group"""
        telegram_id = event.sender_id
        from database.mongo import get_db
        db = get_db()
        
        await db.welcome_messages.delete_one({
            "telegram_id": telegram_id,
            "chat_id": event.chat_id
        })
        
        await event.reply("✅ Welcome/Goodbye message removed for this chat.")
