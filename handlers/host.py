"""
Handler for /host command - login flow
"""

from telethon import events
from bot.client_manager import ClientManager
from database.mongo import get_user
from database.redis_client import check_rate_limit
from utils.logger import logger

# Store login states for multi-step process
_login_states = {}


async def host_handler(manager, event):
    """Handle /host command"""
    telegram_id = event.sender_id
    
    # Rate limiting
    allowed, remaining = await check_rate_limit(f"host:{telegram_id}", limit=3, window=300)
    if not allowed:
        await event.reply("⏳ Too many login attempts. Please wait 5 minutes.")
        return
    
    # Check if already logged in
    existing = await get_user(telegram_id)
    if existing and telegram_id in manager.user_clients:
        client = manager.user_clients[telegram_id]
        if client and client.is_connected():
            await event.reply(
                "✅ **You're already logged in!**\n\n"
                "Use /help to see available commands.\n"
                "Use /logout to disconnect."
            )
            return
    
    # Check for existing pending login state
    client_manager = ClientManager(manager)
    
    if telegram_id in _login_states:
        state = _login_states[telegram_id]
        
        if state["step"] == "phone":
            # User sent phone number
            phone = state["data"].strip()
            result = await client_manager.initiate_login(telegram_id, phone)
            
            if result["success"]:
                _login_states[telegram_id] = {"step": "otp", "data": phone}
                await event.reply(result["message"])
            else:
                del _login_states[telegram_id]
                await event.reply(result["message"])
        
        elif state["step"] == "otp":
            # User sent OTP code
            code = state["data"].strip()
            result = await client_manager.verify_otp(telegram_id, code)
            
            if result.get("step") == "2fa":
                _login_states[telegram_id] = {"step": "2fa", "data": code}
                await event.reply(result["message"])
            else:
                del _login_states[telegram_id]
                await event.reply(result["message"])
                if result["success"]:
                    # Also send plugin list
                    await event.reply(
                        "🚀 **Your Plugins Are Ready!**\n"
                        "Use /plugins to see all available modules."
                    )
        
        elif state["step"] == "2fa":
            # User sent 2FA password
            password = state["data"].strip()
            result = await client_manager.verify_2fa(telegram_id, password)
            del _login_states[telegram_id]
            await event.reply(result["message"])
    
    else:
        # Start new login - ask for phone number
        _login_states[telegram_id] = {"step": "phone", "data": ""}
        await event.reply(
            "📱 **Host Your Account**\n\n"
            "To connect your Telegram account, please send your **phone number**\n"
            "in international format (+1234567890).\n\n"
            "⚠️ Your data is encrypted and secure.\n"
            "❌ Send /cancel to abort."
        )


# Hook into the bot to catch the phone/OTP/2FA messages
async def register_host_flow(manager):
    """Register the multi-step host flow"""
    
    @manager.bot_client.on(events.NewMessage(func=lambda e: e.sender_id in _login_states))
    async def host_flow_handler(event):
        telegram_id = event.sender_id
        state = _login_states.get(telegram_id)
        
        if not state:
            return
        
        # Don't intercept commands
        if event.text.startswith("/"):
            if event.text.lower() == "/cancel":
                del _login_states[telegram_id]
                await event.reply("❌ Login cancelled.")
            return
        
        # Store the data and re-trigger the host handler
        state["data"] = event.text
        await host_handler(manager, event)
