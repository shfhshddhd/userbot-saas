"""
Logging system for the Userbot SaaS
"""

import logging
import sys
from datetime import datetime

logger = logging.getLogger("UserbotSaaS")


def setup_logger(level=logging.INFO):
    """Setup logging configuration"""
    logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # File handler
    file_handler = logging.FileHandler(f"logs/userbot_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler.setLevel(level)
    
    # Format
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
