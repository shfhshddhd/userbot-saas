"""
Core manager that orchestrates multiple user clients
"""

import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from config import config
from database.mongo import (
    get_user, get_all_users, save_session, get_session, 
    create_user, add_log, get_plugin_state, set_plugin_state
)
from database.redis_client import set_user_online
from handlers.host import host_handler
from handlers.callback import callback_handler
from plugins.loader import PluginLoader
from utils.logger import logger


class UserbotManager:
    def __init__(self):
        self.bot_client = None
        self.user_clients = {}
        self.plugin_loader = PluginLoader(self)
        self.active_tasks = set()

    async def start(self):
        """Start the bot and all user clients"""
        # Create the main bot client
        self.bot_client = TelegramClient(
            "bot_session", 
            config.API_ID, 
            config.API_HASH
        )
        
        await self.bot_client.start(bot_token=config.BOT_TOKEN)
        logger.info(f"✅ Bot logged in as @{self.bot_client.me.username or 'unknown'}")

        # Register global event handlers
        self._register_handlers()

        # Load plugins
        self.plugin_loader.load_all()

        # Start all active user clients
        users = await get_all_users(active_only=True)
        logger.info(f"Found {len(users)} active users. Starting clients...")
        
        for user in users:
            await self.start_user_client(user["telegram_id"])

        logger.info("✅ Userbot SaaS is running!")
        
        # Keep running
        await self.bot_client.run_until_disconnected()

    def _register_handlers(self):
        """Register all event handlers"""
        @self.bot_client.on(events.NewMessage(pattern=r'^/host'))
        async def host_wrapper(event):
            await host_handler(self, event)

        @self.bot_client.on(events.CallbackQuery)
        async def callback_wrapper(event):
            await callback_handler(self, event)

        @self.bot_client.on(events.NewMessage(pattern=r'^/start'))
        async def start_handler(event):
            await event.reply(
                "🤖 **Userbot SaaS**\n\n"
                f"Welcome! Use /host to login with your Telegram account.\n"
                f"Commands:\n"
                f"• /host - Login your account\n"
                f"• /help - Show all commands\n"
                f"• /status - Check your account status",
                buttons=[
                    [Button.inline("🎯 Host Account", "host_start")],
                    [Button.inline("❓ Help", "help_show")]
                ]
            )

        @self.bot_client.on(events.NewMessage(pattern=r'^/help'))
        async def help_handler(event):
            await event.reply(
                "📚 **Available Commands**\n\n"
                "**Account:**\n"
                "• /host - Login your Telegram account\n"
                "• /logout - Logout your account\n"
                "• /status - Check account status\n\n"
                "**AI & Auto-Reply:**\n"
                "• /ai [on/off] - Toggle AI auto-reply\n"
                "• /setpersonality [type] - Set AI personality\n"
                "• /autoreply [trigger] [response] - Add auto-reply\n"
                "• /delautoreply [trigger] - Delete auto-reply\n"
                "• /listautoreply - List all auto-replies\n\n"
                "**AFK:**\n"
                "• /afk [message] - Set AFK mode\n"
                "• /unafk - Remove AFK mode\n\n"
                "**Auto Features:**\n"
                "• /autoread [on/off] - Auto-read messages\n"
                "• /autoreact [on/off] [emoji] - Auto-react with emoji\n\n"
                "**Raid Tools:**\n"
                "• /raid [count] [message] - Start raid\n"
                "• /replyraid [on/off] - Toggle reply raid\n"
                "• /spam [count] [message] - Spam messages\n"
                "• /stopraid - Stop active raid\n\n"
                "**Notes:**\n"
                "• /save [name] [content] - Save a note\n"
                "• /get [name] - Get a note\n"
                "• /notes - List all notes\n"
                "• /delnote [name] - Delete a note\n\n"
                "**Scheduler:**\n"
                "• /schedule [time] [message] - Schedule a message\n"
                "• /scheduled - List scheduled messages\n\n"
                "**Welcome/Goodbye:**\n"
                "• /setwelcome [message] - Set welcome message\n"
                "• /setgoodbye [message] - Set goodbye message\n\n"
                "**Plugins:**\n"
                "• /plugins - List all plugins\n"
                "• /enable [plugin] - Enable a plugin\n"
                "• /disable [plugin] - Disable a plugin\n\n"
                "**Owner Commands:**\n"
                "• /broadcast [message] - Broadcast to all users\n"
                "• /users - List all users\n"
                "• /ban [id] - Ban a user\n"
                "• /unban [id] - Unban a user\n"
                "• /backup - Backup all data\n"
                "• /restore - Restore from backup"
            )

        @self.bot_client.on(events.NewMessage(pattern=r'^/status'))
        async def status_handler(event):
            user_id = event.sender_id
            user = await get_user(user_id)
            if not user:
                await event.reply("❌ You haven't hosted your account yet! Use /host")
                return
            
            client = self.user_clients.get(user_id)
            status = "✅ Online" if client and client.is_connected() else "❌ Offline"
            
            await event.reply(
                f"📊 **Account Status**\n\n"
                f"👤 Name: {user.get('first_name', 'N/A')}\n"
                f"🆔 ID: `{user_id}`\n"
                f"📱 Phone: {user.get('phone', 'N/A')}\n"
                f"🔗 Status: {status}\n"
                f"🤖 AI Auto-Reply: {'✅ ON' if user.get('settings', {}).get('ai_autoreply') else '❌ OFF'}\n"
                f"📖 Auto-Read: {'✅ ON' if user.get('settings', {}).get('auto_read') else '❌ OFF'}\n"
                f"💬 Auto-Reply: {'✅ ON' if user.get('settings', {}).get('custom_autoreply') else '❌ OFF'}\n"
                f"😴 AFK: {'✅ ON' if user.get('settings', {}).get('afk') else '❌ OFF'}\n"
                f"📊 Stats: {user.get('stats', {}).get('auto_replies_sent', 0)} auto-replies sent"
            )

    async def start_user_client(self, telegram_id: int):
        """Start a user client for a specific user"""
        try:
            # Skip if already running
            if telegram_id in self.user_clients:
                client = self.user_clients[telegram_id]
                if client and client.is_connected():
                    return True
            
            session_string = await get_session(telegram_id)
            if not session_string:
                logger.warning(f"No session found for user {telegram_id}")
                return False

            user_data = await get_user(telegram_id)
            if not user_data:
                logger.warning(f"User {telegram_id} not found in database")
                return False

            # Create user client
            client = TelegramClient(
                StringSession(session_string),
                config.API_ID,
                config.API_HASH,
                # Disable auto-reconnect to handle errors gracefully
                auto_reconnect=True,
                # Connection retries
                request_retries=5,
                connection_retries=3
            )

            await client.connect()
            
            # Check if authorized
            if not await client.is_user_authorized():
                logger.warning(f"Session expired for user {telegram_id}")
                return False

            me = await client.get_me()
            logger.info(f"✅ User client started: {me.first_name} (ID: {me.id})")
            
            self.user_clients[telegram_id] = client
            
            # Register event handlers for this user
            self._register_user_handlers(client, telegram_id)
            
            return True

        except Exception as e:
            logger.error(f"Failed to start user client for {telegram_id}: {e}")
            return False

    def _register_user_handlers(self, client: TelegramClient, telegram_id: int):
        """Register per-user event handlers"""
        
        @client.on(events.NewMessage(func=lambda e: e.is_private and not e.out))
        async def private_message_handler(event):
            await self.plugin_loader.handle_event("private_message", telegram_id, event)

        @client.on(events.NewMessage(func=lambda e: e.is_group))
        async def group_message_handler(event):
            await self.plugin_loader.handle_event("group_message", telegram_id, event)

        @client.on(events.MessageEdited)
        async def message_edit_handler(event):
            await self.plugin_loader.handle_event("message_edit", telegram_id, event)

        @client.on(events.ChatAction)
        async def chat_action_handler(event):
            await self.plugin_loader.handle_event("chat_action", telegram_id, event)

    async def stop_user_client(self, telegram_id: int):
        """Stop a user client"""
        client = self.user_clients.pop(telegram_id, None)
        if client:
            try:
                await client.disconnect()
                logger.info(f"User client disconnected: {telegram_id}")
            except Exception as e:
                logger.error(f"Error disconnecting user {telegram_id}: {e}")

    async def stop_all_clients(self):
        """Stop all user clients"""
        for tid in list(self.user_clients.keys()):
            await self.stop_user_client(tid)

    async def restart_user_client(self, telegram_id: int):
        """Restart a user client"""
        await self.stop_user_client(telegram_id)
        await asyncio.sleep(1)
        return await self.start_user_client(telegram_id)

    def get_user_client(self, telegram_id: int):
        """Get a user's client instance"""
        return self.user_clients.get(telegram_id)

    async def get_online_users(self):
        """Get count of online user clients"""
        count = 0
        for tid, client in self.user_clients.items():
            if client and client.is_connected():
                count += 1
                await set_user_online(tid)
        return count
