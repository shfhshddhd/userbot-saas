"""
Callback query handler for inline buttons
"""

from telethon import Button
from bot.client_manager import ClientManager
from database.mongo import (
    get_user, get_all_users, get_all_plugin_states, 
    set_plugin_state, create_backup, get_backup
)
from utils.logger import logger


async def callback_handler(manager, event):
    """Handle callback queries from inline buttons"""
    data = event.data.decode()
    telegram_id = event.sender_id
    
    if data == "host_start":
        # Simulate /host command
        from handlers.host import host_handler
        await host_handler(manager, event)
        await event.answer()
    
    elif data == "help_show":
        await event.edit(
            "📚 **Available Commands**\n\n"
            "**Account:**\n"
            "• /host - Login your Telegram account\n"
            "• /logout - Logout your account\n"
            "• /status - Check account status\n\n"
            "**AI & Auto-Reply:**\n"
            "• /ai [on/off] - Toggle AI auto-reply\n"
            "• /autoreply [trigger] [response] - Add auto-reply\n"
            "• /listautoreply - List all auto-replies\n\n"
            "**AFK:**\n"
            "• /afk [message] - Set AFK mode\n"
            "• /unafk - Remove AFK mode\n\n"
            "**Raid:**\n"
            "• /raid [count] [msg] - Start raid\n"
            "• /replyraid [on/off] - Reply raid\n"
            "• /stopraid - Stop all raids\n\n"
            "**Plugins:**\n"
            "• /plugins - List plugins\n"
            "• /enable [name] - Enable plugin\n"
            "• /disable [name] - Disable plugin",
            buttons=[Button.inline("◀ Back", "back_main")]
        )
        await event.answer()
    
    elif data == "back_main":
        await event.edit(
            "🤖 **Userbot SaaS**\n\n"
            "Welcome! Use /host to login with your Telegram account.",
            buttons=[
                [Button.inline("🎯 Host Account", "host_start")],
                [Button.inline("❓ Help", "help_show")]
            ]
        )
        await event.answer()
    
    elif data.startswith("plugin_toggle_"):
        # Toggle plugin
        plugin_name = data.replace("plugin_toggle_", "")
        user = await get_user(telegram_id)
        if not user:
            await event.answer("❌ Host your account first!", alert=True)
            return
        
        current_state = await get_plugin_state(telegram_id, plugin_name)
        new_state = not current_state
        await set_plugin_state(telegram_id, plugin_name, new_state)
        
        await event.answer(f"{'✅ Enabled' if new_state else '❌ Disabled'} {plugin_name}", alert=True)
        
        # Show updated plugins menu
        plugins_list = ["afk", "autoreply", "ai_autoreply", "autoread", "autoreact", 
                       "scheduler", "notes", "welcome", "raid"]
        buttons = []
        row = []
        for i, p in enumerate(plugins_list):
            state = await get_plugin_state(telegram_id, p)
            btn_text = f"{'✅' if state else '❌'} {p}"
            row.append(Button.inline(btn_text, f"plugin_toggle_{p}"))
            if len(row) == 2 or i == len(plugins_list) - 1:
                buttons.append(row)
                row = []
        
        buttons.append([Button.inline("◀ Back", "back_main")])
        
        await event.edit("🔌 **Plugin Manager**\nToggle plugins on/off:", buttons=buttons)
    
    elif data == "plugins_show":
        user = await get_user(telegram_id)
        if not user:
            await event.answer("❌ Host your account first!", alert=True)
            return
        
        plugins_list = ["afk", "autoreply", "ai_autoreply", "autoread", "autoreact", 
                       "scheduler", "notes", "welcome", "raid"]
        buttons = []
        row = []
        for i, p in enumerate(plugins_list):
            state = await get_plugin_state(telegram_id, p)
            btn_text = f"{'✅' if state else '❌'} {p}"
            row.append(Button.inline(btn_text, f"plugin_toggle_{p}"))
            if len(row) == 2 or i == len(plugins_list) - 1:
                buttons.append(row)
                row = []
        
        buttons.append([Button.inline("◀ Back", "back_main")])
        
        await event.edit("🔌 **Plugin Manager**\nToggle plugins on/off:", buttons=buttons)
        await event.answer()
