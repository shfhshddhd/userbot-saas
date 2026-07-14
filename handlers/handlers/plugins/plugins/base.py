"""
Base plugin class that all plugins inherit from
"""

from utils.logger import logger


class BasePlugin:
    """Base class for all plugins"""
    
    name = "base"
    description = "Base plugin"
    version = "1.0.0"
    
    def __init__(self, manager):
        self.manager = manager
        self.bot = manager.bot_client
        
    async def on_load(self):
        """Called when plugin is loaded"""
        logger.info(f"Plugin loaded: {self.name} v{self.version}")
    
    async def on_unload(self):
        """Called when plugin is unloaded"""
        logger.info(f"Plugin unloaded: {self.name}")
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        """Handle an event. Override in subclass."""
        pass
    
    def get_user_client(self, telegram_id: int):
        """Get user's client instance"""
        return self.manager.get_user_client(telegram_id)
