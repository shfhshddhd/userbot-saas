"""
Admin Panel & Owner Commands
Only accessible by the bot owner
"""

from telethon import events, Button
from datetime import datetime
from plugins.base import BasePlugin
from database.mongo import (
    get_user, get_all_users, update_user, delete_user,
    create_backup, get_backup, get_logs, add_log, get_db
)
from config import config
from utils.logger import logger


class AdminPlugin(BasePlugin):
    name = "admin"
    description = "Admin panel and owner-only commands"
    version = "1.0.0"
    
    async def on_load(self):
        # Register owner-only commands
        @self.bot.on(events.NewMessage(pattern=r'^/broadcast'))
        async def broadcast_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_broadcast(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/users$'))
        async def users_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_users(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/ban'))
        async def ban_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_ban(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/unban'))
        async def unban_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_unban(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/backup$'))
        async def backup_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_backup(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/restore$'))
        async def restore_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_restore(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/admin$'))
        async def admin_panel_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._show_admin_panel(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/logs'))
        async def logs_command(event):
            if event.sender_id != config.OWNER_ID:
                return
            await self._handle_logs(event)
    
    async def _show_admin_panel(self, event):
        """Show admin panel"""
        users = await get_all_users()
        online = await self.manager.get_online_users()
        
        text = (
            "👑 **Admin Panel**\n\n"
            f"👥 Total Users: {len(users)}\n"
            f"🟢 Online: {online}\n"
            f"📊 Bot Status: Running\n\n"
            "**Commands:**\n"
            "• `/users` - List all users\n"
            "• `/broadcast [msg]` - Message all users\n"
            "• `/ban [id]` - Ban a user\n"
            "• `/unban [id]` - Unban a user\n"
            "• `/backup` - Create database backup\n"
            "• `/restore` - Restore from backup\n"
            "• `/logs` - View recent logs"
        )
        
        await event.reply(text, buttons=[
            [Button.inline("👥 Users", "admin_users")],
            [Button.inline("📊 Stats", "admin_stats")],
            [Button.inline("💾 Backup", "admin_backup")],
            [Button.inline("📋 Logs", "admin_logs")]
        ])
    
    async def _handle_broadcast(self, event):
        """Broadcast message to all users"""
        text = event.text
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/broadcast [message]`")
            return
        
        message = parts[1]
        users = await get_all_users(active_only=True)
        sent = 0
        failed = 0
        
        status_msg = await event.reply(f"📢 Broadcasting to {len(users)} users...")
        
        for user in users:
            try:
                await event.client.send_message(user["telegram_id"], 
                    f"📢 **Broadcast:**\n\n{message}")
                sent += 1
                await asyncio.sleep(0.05)  # Rate limit
            except:
                failed += 1
        
        await status_msg.edit(f"✅ **Broadcast Complete!**\n\nSent: {sent}\nFailed: {failed}")
        await add_log(config.OWNER_ID, "broadcast", f"Sent to {sent} users, {failed} failed")
    
    async def _handle_users(self, event):
        """List all users"""
        users = await get_all_users(active_only=False)
        
        if not users:
            await event.reply("📭 No users registered.")
            return
        
        text = "👥 **Registered Users:**\n\n"
        for u in users:
            name = u.get("first_name", "Unknown")
            uid = u.get("telegram_id", "?")
            active = "🟢" if u.get("is_active") else "🔴"
            banned = "🚫" if u.get("is_banned") else ""
            text += f"{active}{banned} {name} (`{uid}`)\n"
        
        # Split long messages
        if len(text) > 4000:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await event.reply(chunk)
        else:
            await event.reply(text)
    
    async def _handle_ban(self, event):
        """Ban a user"""
        text = event.text
        parts = text.split()
        
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/ban [user_id]`")
            return
        
        try:
            target_id = int(parts[1])
            user = await get_user(target_id)
            
            if not user:
                await event.reply(f"❌ User `{target_id}` not found.")
                return
            
            await update_user(target_id, is_active=False, is_banned=True)
            await self.manager.stop_user_client(target_id)
            
            await event.reply(f"✅ User `{target_id}` has been banned.")
            await add_log(config.OWNER_ID, "ban", f"Banned user {target_id}")
            
        except ValueError:
            await event.reply("❌ Invalid user ID.")
    
    async def _handle_unban(self, event):
        """Unban a user"""
        text = event.text
        parts = text.split()
        
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/unban [user_id]`")
            return
        
        try:
            target_id = int(parts[1])
            await update_user(target_id, is_active=True, is_banned=False)
            
            await event.reply(f"✅ User `{target_id}` has been unbanned.")
            await add_log(config.OWNER_ID, "unban", f"Unbanned user {target_id}")
            
        except ValueError:
            await event.reply("❌ Invalid user ID.")
    
    async def _handle_backup(self, event):
        """Create a full database backup"""
        status_msg = await event.reply("💾 Creating backup...")
        
        try:
            db = get_db()
            backup_data = {}
            
            # Export all collections
            collections = await db.list_collection_names()
            for col_name in collections:
                collection = db[col_name]
                cursor = collection.find({})
                documents = await cursor.to_list(length=None)
                # Convert ObjectId to string
                for doc in documents:
                    doc["_id"] = str(doc["_id"])
                backup_data[col_name] = documents
            
            # Save backup to file
            import json
            from datetime import datetime
            backup_file = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import aiofiles
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps(backup_data, indent=2, default=str))
            
            await status_msg.edit(f"✅ **Backup Created!**\nFile: `{backup_file}`\nCollections: {len(backup_data)}")
            
        except Exception as e:
            logger.error(f"Backup error: {e}")
            await status_msg.edit(f"❌ Backup failed: {str(e)[:100]}")
    
    async def _handle_restore(self, event):
        """Restore from latest backup"""
        import os
        
        backups = sorted([f for f in os.listdir("backups") if f.endswith(".json")], reverse=True)
        if not backups:
            await event.reply("❌ No backups found.")
            return
        
        status_msg = await event.reply(f"🔄 Restoring from `{backups[0]}`...")
        
        try:
            import json, aiofiles
            async with aiofiles.open(f"backups/{backups[0]}", 'r') as f:
                content = await f.read()
            
            backup_data = json.loads(content)
            db = get_db()
            
            for col_name, documents in backup_data.items():
                if documents:
                    collection = db[col_name]
                    await collection.delete_many({})
                    for doc in documents:
                        from bson.objectid import ObjectId
                        doc["_id"] = ObjectId(doc["_id"])
                    await collection.insert_many(documents)
            
            await status_msg.edit(f"✅ **Restore Complete!**\nFrom: `{backups[0]}`")
            
            # Restart all clients
            await self.manager.stop_all_clients()
            users = await get_all_users(active_only=True)
            for user in users:
                await self.manager.start_user_client(user["telegram_id"])
            
        except Exception as e:
            logger.error(f"Restore error: {e}")
            await status_msg.edit(f"❌ Restore failed: {str(e)[:100]}")
    
    async def _handle_logs(self, event):
        """Show recent logs"""
        text = event.text
        parts = text.split()
        limit = 30
        
        if len(parts) > 1:
            try:
                limit = int(parts[1])
            except:
                pass
        
        logs = await get_logs(config.OWNER_ID, limit)
        
        if not logs:
            await event.reply("📋 No logs available.")
            return
        
        log_text = "📋 **Recent Logs:**\n\n"
        for log in logs:
            timestamp = log.get("timestamp", datetime.utcnow()).strftime("%H:%M:%S")
            action = log.get("action", "unknown")
            details = log.get("details", "")[:50]
            log_text += f"`{timestamp}` **{action}** - {details}\n"
        
        await event.reply(log_text)
