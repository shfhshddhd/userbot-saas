"""
Scheduler Plugin - Schedule messages for later delivery
"""

import asyncio
from datetime import datetime, timedelta
from telethon import events
from plugins.base import BasePlugin
from database.mongo import (
    save_scheduled_message, get_pending_scheduled_messages,
    mark_scheduled_sent, delete_scheduled_message, add_log
)
from utils.logger import logger
from utils.helpers import parse_time_string


class SchedulerPlugin(BasePlugin):
    name = "scheduler"
    description = "Schedule messages for future delivery"
    version = "1.0.0"
    
    def __init__(self, manager):
        super().__init__(manager)
        self._scheduler_task = None
    
    async def on_load(self):
        # Register commands
        @self.bot.on(events.NewMessage(pattern=r'^/schedule'))
        async def schedule_command(event):
            await self._handle_schedule(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/scheduled$'))
        async def scheduled_list_command(event):
            await self._handle_scheduled_list(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/cancelschedule'))
        async def cancel_schedule_command(event):
            await self._handle_cancel_schedule(event)
        
        # Start scheduler loop
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler loop started")
    
    async def on_unload(self):
        if self._scheduler_task:
            self._scheduler_task.cancel()
    
    async def _scheduler_loop(self):
        """Background loop to check and send scheduled messages"""
        while True:
            try:
                pending = await get_pending_scheduled_messages()
                
                for msg in pending:
                    try:
                        telegram_id = msg["telegram_id"]
                        client = self.get_user_client(telegram_id)
                        
                        if client and client.is_connected():
                            await client.send_message(
                                msg["chat_id"],
                                msg["message"]
                            )
                            await mark_scheduled_sent(msg["_id"])
                            await add_log(
                                telegram_id, 
                                "scheduled_sent", 
                                f"Sent scheduled message to {msg['chat_id']}"
                            )
                        else:
                            logger.warning(f"Client not available for scheduled msg {telegram_id}")
                    
                    except Exception as e:
                        logger.error(f"Error sending scheduled message: {e}")
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _handle_schedule(self, event):
        """Handle /schedule command"""
        telegram_id = event.sender_id
        text = event.text
        
        # Parse: /schedule 1h30m Hello everyone!
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await event.reply(
                "📋 **Usage:** `/schedule [time] [message]`\n\n"
                "Time formats:\n"
                "• `10m` - 10 minutes\n"
                "• `1h30m` - 1 hour 30 minutes\n"
                "• `2h` - 2 hours\n"
                "• `1d` - 1 day\n\n"
                "Example: `/schedule 2h Meeting in 2 hours!`"
            )
            return
        
        time_str = parts[1]
        message = parts[2]
        
        seconds = parse_time_string(time_str)
        if seconds < 60:
            await event.reply("❌ Minimum time is 1 minute.")
            return
        
        if seconds > 86400 * 7:
            await event.reply("❌ Maximum time is 7 days.")
            return
        
        schedule_at = datetime.utcnow() + timedelta(seconds=seconds)
        
        await save_scheduled_message(
            telegram_id=telegram_id,
            chat_id=event.chat_id,
            message=message,
            schedule_at=schedule_at
        )
        
        # Format time for display
        if seconds < 3600:
            time_display = f"{seconds // 60} minutes"
        elif seconds < 86400:
            time_display = f"{seconds // 3600} hours"
        else:
            time_display = f"{seconds // 86400} days"
        
        await event.reply(
            f"✅ **Message Scheduled!**\n\n"
            f"📝 Message: {message[:50]}{'...' if len(message) > 50 else ''}\n"
            f"⏱ Sends in: {time_display}\n"
            f"📅 At: {schedule_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
    
    async def _handle_scheduled_list(self, event):
        """List all scheduled messages"""
        telegram_id = event.sender_id
        from database.mongo import get_db
        db = get_db()
        
        cursor = db.scheduled_messages.find({
            "telegram_id": telegram_id,
            "is_sent": False
        }).sort("schedule_at", 1)
        
        messages = await cursor.to_list(length=None)
        
        if not messages:
            await event.reply("📅 **No scheduled messages.**")
            return
        
        text = "📅 **Scheduled Messages:**\n\n"
        for i, msg in enumerate(messages, 1):
            time_left = msg["schedule_at"] - datetime.utcnow()
            hours = time_left.total_seconds() / 3600
            text += f"{i}. `{msg['message'][:40]}` - in {hours:.1f}h\n"
        
        await event.reply(text)
    
    async def _handle_cancel_schedule(self, event):
        """Cancel a scheduled message"""
        telegram_id = event.sender_id
        text = event.text
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/cancelschedule [id]`\nUse `/scheduled` to see IDs.")
            return
        
        try:
            msg_id = int(parts[1])
            from database.mongo import get_db
            db = get_db()
            from bson.objectid import ObjectId
            
            # Get scheduled messages
            cursor = db.scheduled_messages.find({
                "telegram_id": telegram_id,
                "is_sent": False
            }).sort("schedule_at", 1)
            
            messages = await cursor.to_list(length=None)
            
            if 1 <= msg_id <= len(messages):
                await delete_scheduled_message(messages[msg_id - 1]["_id"])
                await event.reply(f"✅ Scheduled message #{msg_id} cancelled.")
            else:
                await event.reply("❌ Invalid ID.")
        
        except:
            await event.reply("❌ Invalid ID.")
