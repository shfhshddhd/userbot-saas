"""
Manages individual Telethon client lifecycle and operations
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    FloodWaitError
)
from config import config
from database.mongo import save_session, create_user
from utils.logger import logger


class ClientManager:
    """Manages the lifecycle of a single user client"""
    
    def __init__(self, userbot_manager):
        self.manager = userbot_manager
        self.auth_states = {}  # telegram_id -> auth state

    async def initiate_login(self, telegram_id: int, phone: str):
        """Start the OTP login process"""
        client = TelegramClient(
            StringSession(),
            config.API_ID,
            config.API_HASH
        )
        
        try:
            await client.connect()
            sent = await client.send_code_request(phone)
            
            self.auth_states[telegram_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": sent.phone_code_hash,
                "step": "otp"
            }
            
            logger.info(f"OTP sent to {phone[:5]}... for user {telegram_id}")
            
            return {
                "success": True,
                "message": "✅ OTP has been sent to your Telegram!\n\nReply with the code you received."
            }
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait on login for {telegram_id}: {e.seconds}s")
            return {
                "success": False,
                "message": f"⏳ Too many attempts. Please wait {e.seconds} seconds."
            }
        except Exception as e:
            logger.error(f"Login initiation failed for {telegram_id}: {e}")
            return {
                "success": False,
                "message": f"❌ Error: {str(e)}"
            }

    async def verify_otp(self, telegram_id: int, code: str):
        """Verify OTP code"""
        state = self.auth_states.get(telegram_id)
        if not state:
            return {"success": False, "message": "❌ No pending login. Use /host again."}
        
        client = state["client"]
        
        try:
            await client.sign_in(
                phone=state["phone"],
                code=code,
                phone_code_hash=state["phone_code_hash"]
            )
            
            me = await client.get_me()
            session_string = client.session.save()
            
            # Save to database
            await save_session(me.id, session_string, state["phone"])
            await create_user(
                telegram_id=me.id,
                phone=state["phone"],
                session_string=session_string,
                first_name=me.first_name or "",
                username=me.username or ""
            )
            
            # Start this user's client in the manager
            await self.manager.start_user_client(me.id)
            
            # Cleanup
            del self.auth_states[telegram_id]
            
            logger.info(f"✅ User {me.first_name} ({me.id}) logged in successfully!")
            
            return {
                "success": True,
                "message": f"🎉 **Login Successful!**\n\n"
                           f"Welcome {me.first_name}!\n"
                           f"Your account is now connected.\n"
                           f"Use /help to see all available commands.",
                "user_id": me.id
            }
            
        except SessionPasswordNeededError:
            state["step"] = "2fa"
            return {
                "success": True,
                "message": "🔐 **2FA Required**\n\nPlease enter your 2FA password.",
                "step": "2fa"
            }
        except PhoneCodeExpiredError:
            del self.auth_states[telegram_id]
            return {"success": False, "message": "❌ Code expired. Use /host again."}
        except PhoneCodeInvalidError:
            return {"success": False, "message": "❌ Invalid code. Please try again."}
        except Exception as e:
            logger.error(f"OTP verification failed for {telegram_id}: {e}")
            return {"success": False, "message": f"❌ Error: {str(e)}"}

    async def verify_2fa(self, telegram_id: int, password: str):
        """Verify 2FA password"""
        state = self.auth_states.get(telegram_id)
        if not state or state.get("step") != "2fa":
            return {"success": False, "message": "❌ No pending 2FA. Use /host again."}
        
        client = state["client"]
        
        try:
            await client.sign_in(password=password)
            
            me = await client.get_me()
            session_string = client.session.save()
            
            # Save to database with 2FA flag
            await save_session(me.id, session_string, state["phone"])
            await create_user(
                telegram_id=me.id,
                phone=state["phone"],
                session_string=session_string,
                first_name=me.first_name or "",
                username=me.username or ""
            )
            await self.manager.start_user_client(me.id)
            
            del self.auth_states[telegram_id]
            
            logger.info(f"✅ User {me.first_name} ({me.id}) logged in with 2FA!")
            
            return {
                "success": True,
                "message": f"🎉 **Login Successful!**\n\n"
                           f"Welcome {me.first_name}!\n"
                           f"2FA authentication completed.\n"
                           f"Use /help to see all available commands.",
                "user_id": me.id
            }
            
        except Exception as e:
            logger.error(f"2FA verification failed for {telegram_id}: {e}")
            return {"success": False, "message": f"❌ Wrong password: {str(e)}"}

    def cleanup_auth_state(self, telegram_id: int):
        """Clean up authentication state"""
        state = self.auth_states.pop(telegram_id, None)
        if state and state.get("client"):
            asyncio.create_task(state["client"].disconnect())
