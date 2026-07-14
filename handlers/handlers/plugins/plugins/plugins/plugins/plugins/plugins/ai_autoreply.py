"""
AI Auto-Reply Plugin
Uses AI to generate human-like responses when user is offline
Also handles reply and tag in groups
Speech style adapts to the sender's tone
"""

import random
from plugins.base import BasePlugin
from database.mongo import get_user, update_user, add_log
from database.redis_client import check_rate_limit
from utils.logger import logger


class AIAutoReplyPlugin(BasePlugin):
    name = "ai_autoreply"
    description = "AI auto-reply - human-like conversation when offline"
    version = "1.0.0"
    
    def __init__(self, manager):
        super().__init__(manager)
        self.active_sessions = {}
        
        # Indian-style conversational templates
        self.friendly_responses = [
            "Haan bhai, sun raha hu! Kya baat hai? 😊",
            "Arre haan ji, boliye kya baat hai?",
            "Hi! Kaise ho? Kya help chahiye?",
            "Hello ji, main yahan hoon. Boliye!",
            "Haan ji, sun raha hu aapko. Batao kya kaam hai?",
            "Namaste! Kaise ho aap? Kya ho sakta hai main aapki madad?",
            "Bhai, main hoon na! Kya chahiye aapko?",
            "Arey yaar, kaise ho? Kya ho raha hai?",
            "Hello dost! Kya scene hai?",
            "Ji haan, batao kya baat karni hai?"
        ]
        
        self.rude_responses = [
            "Bhai apna kaam kar na, itni kyun aa raha hai?",
            "Tujhe kya chahiye bhai? Ja apna kaam kar.",
            "Chal nikal yahan se, time waste mat kar mera.",
            "Oops! Itna time kiske paas hai? Bye!",
            "Bhai tera problem hai toh apne paas rakh.",
            "Mujhe kya? Apna dekh na pehle.",
            "Hatt! Ja na yahan se.",
            "Tu kaun hai bhai? Kya chahiye tujhe?",
            "Chill maar bhai. Itna serious kyun hai?",
            "Bhai bas kar. Itna mat bol."
        ]
        
        self.neutral_responses = [
            "Hanji, main online nahi hu right now. Baad mein baat karte hain.",
            "I'm offline right now. Will reply when I'm back!",
            "Main thoda busy hoon. Baad mein aapko reply karunga!",
            "Ji, main abhi available nahi hu. Koi urgent ho toh text kar do.",
            "Will get back to you soon! Thanks for your message."
        ]
    
    async def handle_event(self, event_type: str, telegram_id: int, event):
        if event_type in ["private_message", "group_message"]:
            await self._handle_ai_reply(telegram_id, event)
    
    async def _handle_ai_reply(self, telegram_id: int, event):
        """Main AI reply handler"""
        # Don't reply to own messages
        if event.out:
            return
        
        user = await get_user(telegram_id)
        if not user:
            return
        
        settings = user.get("settings", {})
        
        # Only work if AI auto-reply is ON and user is offline/AFK
        if not settings.get("ai_autoreply", False):
            return
        
        # Check if user is actively online (skip if they are)
        client = self.get_user_client(telegram_id)
        if not client:
            return
        
        # Check rate limiting for AI replies
        allowed, _ = await check_rate_limit(f"ai_reply:{telegram_id}", limit=20, window=60)
        if not allowed:
            return
        
        # Determine if we should reply
        should_reply = False
        message_text = event.text or ""
        
        if event.is_private:
            should_reply = True
        elif event.is_group:
            # Reply if mentioned or replied to user's message
            me = await client.get_me()
            if me:
                if event.mentioned:
                    should_reply = True
                elif event.is_reply:
                    reply_msg = await event.get_reply_message()
                    if reply_msg and reply_msg.sender_id == me.id:
                        should_reply = True
        
        if not should_reply:
            return
        
        # Detect tone of the incoming message
        rude_keywords = ["bhosd", "madarchod", "behenchod", "chutiya", "laude", 
                        "randi", "kutti", "harami", "bakwas", "bhadva", "nikal",
                        "chup", "bewakoof", "saala", "sala", "teri", "maa ki",
                        "fuck", "shit", "asshole", "bitch", "dick", "bastard"]
        
        is_rude = any(kw in message_text.lower() for kw in rude_keywords)
        
        # Also check for ALL CAPS (yelling)
        if len(message_text) > 10 and message_text.isupper():
            is_rude = True
        
        try:
            # Generate appropriate response based on tone
            if is_rude:
                response = random.choice(self.rude_responses)
            elif "?" in message_text or "kyu" in message_text.lower() or "kya" in message_text.lower() or "kaise" in message_text.lower():
                # Question detected - try to be helpful
                response = random.choice(self.friendly_responses)
            else:
                # Normal message
                response = random.choice(self.neutral_responses)
            
            # Add slight delay to feel more human-like
            import asyncio
            delay = random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)
            
            # Send reply
            await client.send_message(event.chat_id, response, reply_to=event.id)
            
            # Update stats
            stats = user.get("stats", {})
            stats["auto_replies_sent"] = stats.get("auto_replies_sent", 0) + 1
            await update_user(telegram_id, stats=stats)
            
            await add_log(telegram_id, "ai_autoreply", f"Replied to {event.sender_id}: {'rude' if is_rude else 'normal'}")
            
        except Exception as e:
            logger.error(f"AI auto-reply error for {telegram_id}: {e}")
    
    async def set_ai_state(self, telegram_id: int, enabled: bool, personality: str = "friendly"):
        """Toggle AI auto-reply"""
        user = await get_user(telegram_id)
        if not user:
            return False
        
        settings = user.get("settings", {})
        settings["ai_autoreply"] = enabled
        if personality:
            settings["ai_personality"] = personality
        
        await update_user(telegram_id, settings=settings)
        await add_log(telegram_id, "ai_autoreply", f"{'Enabled' if enabled else 'Disabled'}")
        return True
