"""
Notes Plugin - Save and retrieve notes
"""

from telethon import events
from plugins.base import BasePlugin
from database.mongo import save_note, get_note, get_all_notes, delete_note, add_log
from utils.logger import logger


class NotesPlugin(BasePlugin):
    name = "notes"
    description = "Save and retrieve notes/quick texts"
    version = "1.0.0"
    
    async def on_load(self):
        @self.bot.on(events.NewMessage(pattern=r'^/save'))
        async def save_command(event):
            await self._handle_save(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/get'))
        async def get_command(event):
            await self._handle_get(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/notes$'))
        async def notes_list_command(event):
            await self._handle_notes_list(event)
        
        @self.bot.on(events.NewMessage(pattern=r'^/delnote'))
        async def delnote_command(event):
            await self._handle_delnote(event)
    
    async def _handle_save(self, event):
        """Save a note"""
        telegram_id = event.sender_id
        text = event.text
        
        # Parse: /save name content
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await event.reply(
                "📋 **Usage:** `/save [name] [content]`\n"
                "Example: `/save welcome Welcome to our group!`"
            )
            return
        
        name = parts[1].lower()
        content = parts[2]
        
        await save_note(telegram_id, name, content)
        await event.reply(f"✅ **Note saved!**\nName: `{name}`\nUse `/get {name}` to retrieve.")
        await add_log(telegram_id, "note_save", f"Saved note: {name}")
    
    async def _handle_get(self, event):
        """Get a note by name"""
        telegram_id = event.sender_id
        text = event.text
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/get [name]`")
            return
        
        name = parts[1].lower()
        note = await get_note(telegram_id, name)
        
        if note:
            await event.reply(f"📝 **{name}**\n\n{note['content']}")
        else:
            await event.reply(f"❌ Note `{name}` not found.")
    
    async def _handle_notes_list(self, event):
        """List all notes"""
        telegram_id = event.sender_id
        notes = await get_all_notes(telegram_id)
        
        if not notes:
            await event.reply("📝 **No notes saved.** Use `/save [name] [content]` to create one.")
            return
        
        text = "📝 **Your Notes:**\n\n"
        for note in notes:
            text += f"• `{note['name']}`\n"
        
        await event.reply(text)
    
    async def _handle_delnote(self, event):
        """Delete a note"""
        telegram_id = event.sender_id
        text = event.text
        
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("📋 **Usage:** `/delnote [name]`")
            return
        
        name = parts[1].lower()
        await delete_note(telegram_id, name)
        await event.reply(f"✅ Note `{name}` deleted.")
