"""
Raid Plugin - Reply Raid & Spam Tools
"""

import asyncio
import random
from telethon import events
from plugins.base import BasePlugin
from database.mongo import get_user, add_log
from database.redis_client import check_rate_limit
from utils.logger import logger


class RaidPlugin(BasePlugin):
    name = "raid"
    description = "Raid tools: Reply Raid, Spam, and Raid"
    version = "1.0.0"
    
    def __init__(self, manager):
        super().__init__(manager)
        self.active_raids = {}  # telegram_id -> {chat_id, count, message, running}
        self.reply_raids = {}   # telegram_id -> {chat_id, active, message}
        
    async def on_load(self):
        # Register raid commands
        @self.bot.on(events.NewMessage(pattern=r'^/raid'))
        async def raid_command(event):
            await self._handle_raid_command(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/replyraid'))
        async def replyraid_command(event):
            await self._handle_replyraid_command(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/spam'))
        async def spam_command(event):
            await self._handle_spam_command(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/stopraid'))
        async def stopraid_command(event):
            await self._handle_stopraid_command(event)
        
        logger.info("Raid commands registered")
    
    async def _handle_raid_command(self, event):
        """Handle /raid command"""
        telegram_id = event.sender_id
        user = await get_user(telegram_id)
        if not user:
            await event.reply("❌ Host your account first! Use /host")
            return
        
        args = event.text.split(maxsplit=2)
        if len(args) < 2:
            await event.reply(
                "📋 **Raid Command Usage**\n\n"
                "• `/raid [count] [message]` - Start raid in current chat\n"
                "• `/raid stop` - Stop raiding\n\n"
                "Example: `/raid 10 Hello everyone!`"
            )
            return
        
        if args[1].lower() == "stop":
            await self._stop_raid(telegram_id)
            await event.reply("🛑 Raid stopped.")
            return
        
        try:
            count = int(args[1])
            message = args[2] if len(args) > 2 else "Raid!"
            
            if count > 100:
                await event.reply("⚠️ Max 100 messages allowed per raid.")
                return
            
            if count < 1:
                await event.reply("❌ Count must be at least 1.")
                return
            
            # Get the user's client and chat
            client = self.get_user_client(telegram_id)
            if not client:
                await event.reply("❌ Your client is not connected. Re-login with /host")
                return
            
            chat = await event.get_chat()
            chat_id = event.chat_id
            
            # Start raid
            self.active_raids[telegram_id] = {
                "chat_id": chat_id,
                "count": count,
                "message": message,
                "running": True
            }
            
            await event.reply(f"🚀 **Raid Started!**\nSending {count} messages...\nUse /stopraid to stop.")
            
            # Send raid messages
            for i in range(count):
                if not self.active_raids.get(telegram_id, {}).get("running", False):
                    break
                
                await client.send_message(chat_id, message)
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            self.active_raids.pop(telegram_id, None)
            await event.reply("✅ Raid completed!")
            
        except ValueError:
            await event.reply("❌ Invalid count. Use a number.")
        except Exception as e:
            logger.error(f"Raid error for {telegram_id}: {e}")
            await event.reply(f"❌ Error: {str(e)[:100]}")
    
    async def _handle_replyraid_command(self, event):
        """Handle /replyraid command"""
        telegram_id = event.sender_id
        user = await get_user(telegram_id)
        if not user:
            await event.reply("❌ Host your account first! Use /host")
            return
        
        args = event.text.split(maxsplit=1)
        
        if len(args) < 2:
            state = self.reply_raids.get(telegram_id, {}).get("active", False)
            status = "✅ ON" if state else "❌ OFF"
            await event.reply(
                f"📋 **Reply Raid**\n\n"
                f"Status: {status}\n\n"
                f"• `/replyraid on [message]` - Enable reply raid\n"
                f"• `/replyraid off` - Disable reply raid\n"
                f"• `/replyraid message [text]` - Set reply message"
            )
            return
        
        if args[1].startswith("off"):
            self.reply_raids.pop(telegram_id, None)
            await event.reply("🛑 Reply Raid disabled.")
            return
        
        if args[1].startswith("on"):
            message = args[1][3:].strip() or "Reply Raid!"
            self.reply_raids[telegram_id] = {
                "active": True,
                "message": message,
                "chat_id": event.chat_id
            }
            await event.reply(f"✅ Reply Raid enabled!\nReply message: {message}")
            return
        
        if args[1].startswith("message"):
            message = args[1][8:].strip()
            if telegram_id in self.reply_raids:
                self.reply_raids[telegram_id]["message"] = message
            await event.reply(f"✅ Reply message set to: {message}")
    
    async def _handle_spam_command(self, event):
        """Handle /spam command"""
        telegram_id = event.sender_id
        user = await get_user(telegram_id)
        if not user:
            await event.reply("❌ Host your account first! Use /host")
            return
        
        args = event.text.split(maxsplit=2)
        if len(args) < 2:
            await event.reply(
                "📋 **Spam Command Usage**\n\n"
                "• `/spam [count] [message]` - Spam messages\n\n"
                "Example: `/spam 5 Hello!`"
            )
            return
        
        try:
            count = int(args[1])
            message = args[2] if len(args) > 2 else "Spam!"
            
            if count > 50:
                await event.reply("⚠️ Max 50 messages allowed per spam.")
                return
            
            client = self.get_user_client(telegram_id)
            if not client:
                await event.reply("❌ Your client is not connected.")
                return
            
            await event.reply(f"🚀 Spamming {count} messages...")
            
            for i in range(count):
                await client.send_message(event.chat_id, f"{message} [{i+1}/{count}]")
                await asyncio.sleep(0.3)
            
            await event.reply("✅ Spam completed!")
            
        except ValueError:
            await event.reply("❌ Invalid count.")
        except Exception as e:
            logger.error(f"Spam error: {e}")
            await event.reply(f"❌ Error: {str(e)[:100]}")
    
    async def _handle_stopraid_command(self, event):
        """Handle /stopraid command"""
        telegram_id = event.sender_id
        await self._stop_raid(telegram_id)
        await event.reply("🛑 All raids stopped.")
    
    async def _stop_raid(self, telegram_id: int):
        """Stop active raid"""
        if telegram_id in self.active_raids:
            self.active_raids[telegram_id]["running"] = False
            del self.active_raids[telegram_id]
        self.reply_raids.pop(telegram_id, None)
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        """Handle reply raid events"""
        if event_type in ["private_message", "group_message"]:
            await self._handle_reply_raid_reply(telegram_id, event)
    
    async def _handle_reply_raid_reply(self, telegram_id: int, event):
        """Auto-reply to messages when reply raid is active"""
        if event.out:
            return
        
        raid_data = self.reply_raids.get(telegram_id)
        if not raid_data or not raid_data.get("active"):
            return
        
        # Check if in same chat
        if raid_data.get("chat_id") and raid_data["chat_id"] != event.chat_id:
            return
        
        # Rate limit reply raid
        allowed, _ = await check_rate_limit(f"replyraid:{telegram_id}:{event.chat_id}", limit=10, window=5)
        if not allowed:
            return
        
        try:
            client = self.get_user_client(telegram_id)
            if client:
                await client.send_message(
                    event.chat_id, 
                    raid_data.get("message", "Reply!"), 
                    reply_to=event.id
                )
        except Exception as e:
            logger.error(f"Reply raid error: {e}")
