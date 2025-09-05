"""
Configuration Management
"""

import os
from typing import List

class Config:
    # Telegram API credentials
    API_ID = int(os.getenv("API_ID", ""))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Database configuration
    DATABASE_URI = os.getenv("DATABASE_URI", "")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "media")
    
    # Bot configuration
    ADMINS = [int(x) for x in os.getenv("ADMINS", "").split() if x.strip()]
    CHANNELS = [int(x) for x in os.getenv("CHANNELS", "1001981747992").split() if x.strip()]
    AUTH_CHANNEL = int(os.getenv("AUTH_CHANNEL", "0")) if os.getenv("AUTH_CHANNEL") else None
    AUTH_USERS = [int(x) for x in os.getenv("AUTH_USERS", "").split() if x.strip()]
    
    # Search configuration
    CACHE_TIME = int(os.getenv("CACHE_TIME", "300"))
    USE_CAPTION_FILTER = os.getenv("USE_CAPTION_FILTER", "True").lower() == "true"
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", "50"))
    
    # Validate required configs
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ["API_ID", "API_HASH", "BOT_TOKEN", "DATABASE_URI"]
        missing = []
        
        for field in required:
            if not getattr(cls, field):
                missing.append(field)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        if not cls.ADMINS:
            raise ValueError("At least one admin must be specified in ADMINS")
        
        if not cls.CHANNELS:
            raise ValueError("At least one channel must be specified in CHANNELS")

# Validate configuration on import
Config.validate()
