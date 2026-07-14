"""
Security and encryption utilities
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from config import config
from utils.logger import logger


def _get_fernet():
    """Get Fernet cipher with key derived from config key"""
    if not config.ENCRYPTION_KEY:
        logger.warning("Encryption key not set! Session data will be insecure!")
        return None
    
    # Ensure 32-byte key for Fernet
    if len(config.ENCRYPTION_KEY) < 32:
        # Pad with zeros
        key = config.ENCRYPTION_KEY.ljust(32, b'\0')
    else:
        key = config.ENCRYPTION_KEY[:32]
    
    # Base64 encode for Fernet
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_session(session_string: str) -> str:
    """Encrypt a session string for storage"""
    if not session_string:
        return ""
    
    cipher = _get_fernet()
    if not cipher:
        return session_string  # Fallback - not recommended
    
    encrypted = cipher.encrypt(session_string.encode())
    return encrypted.decode()


def decrypt_session(encrypted_string: str) -> str:
    """Decrypt a stored session string"""
    if not encrypted_string:
        return ""
    
    cipher = _get_fernet()
    if not cipher:
        return encrypted_string  # Fallback
    
    try:
        decrypted = cipher.decrypt(encrypted_string.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt session: {e}")
        return ""


def generate_encryption_key() -> str:
    """Generate a random 32-byte hex key for .env file"""
    key = os.urandom(32)
    return key.hex()


def hash_telegram_id(telegram_id: int) -> str:
    """Hash Telegram ID for non-reversible lookup"""
    import hashlib
    return hashlib.sha256(str(telegram_id).encode()).hexdigest()
