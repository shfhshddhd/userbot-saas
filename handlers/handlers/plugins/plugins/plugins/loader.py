"""
Plugin loading system
"""

from plugins.afk import AFKPlugin
from plugins.autoreply import AutoReplyPlugin
from plugins.ai_autoreply import AIAutoReplyPlugin
from plugins.autoread import AutoReadPlugin
from plugins.autoreact import AutoReactPlugin
from plugins.scheduler import SchedulerPlugin
from plugins.notes import NotesPlugin
from plugins.welcome import WelcomePlugin
from plugins.raid import RaidPlugin
from plugins.admin import AdminPlugin
from utils.logger import logger


class PluginLoader:
    """Loads and manages all plugins"""
    
    def __init__(self, manager):
        self.manager = manager
        self.plugins = {}
    
    def load_all(self):
        """Register all available plugins"""
        plugin_classes = [
            AFKPlugin,
            AutoReplyPlugin,
            AIAutoReplyPlugin,
            AutoReadPlugin,
            AutoReactPlugin,
            SchedulerPlugin,
            NotesPlugin,
            WelcomePlugin,
            RaidPlugin,
            AdminPlugin,
        ]
        
        for plugin_class in plugin_classes:
            try:
                plugin = plugin_class(self.manager)
                self.plugins[plugin.name] = plugin
                logger.info(f"✅ Plugin registered: {plugin.name}")
            except Exception as e:
                logger.error(f"Failed to register plugin {plugin_class.__name__}: {e}")
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        """Route events to appropriate plugins"""
        for name, plugin in self.plugins.items():
            try:
                # Check if plugin is enabled for this user
                from database.mongo import get_plugin_state
                enabled = await get_plugin_state(telegram_id, name)
                if enabled:
                    await plugin.handle_event(event_type, telegram_id, event)
            except Exception as e:
                logger.error(f"Error in plugin {name} handling event: {e}")
    
    def get_plugin(self, name: str):
        """Get a specific plugin by name"""
        return self.plugins.get(name)
    
    def list_plugins(self):
        """List all registered plugins"""
        return {name: plugin.description for name, plugin in self.plugins.items()}
