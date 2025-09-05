"""
Utility Functions
"""

import logging
from typing import Optional, List
from pyrogram.types import Message, User
from config import Config

logger = logging.getLogger(__name__)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size_value = float(size_bytes)
    while size_value >= 1024 and i < len(size_names) - 1:
        size_value /= 1024.0
        i += 1
    
    return f"{size_value:.1f} {size_names[i]}"

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in Config.ADMINS

async def is_authorized_user(user_id: int, client) -> bool:
    """Check if user is authorized to use the bot"""
    # Check if user is banned first
    if await client.db.is_banned(user_id):
        return False
    # Then check if user is admin or authorized
    if not Config.AUTH_USERS:
        return True
    return user_id in Config.AUTH_USERS or is_admin(user_id)

async def is_subscribed(client, user_id: int) -> bool:
    """Check if user is subscribed to auth channel"""
    if not Config.AUTH_CHANNEL:
        return True
    
    try:
        member = await client.get_chat_member(Config.AUTH_CHANNEL, user_id)
        return member.status not in ["kicked", "left"]
    except Exception:
        return False

def extract_media_info(message: Message) -> Optional[dict]:
    """Extract media information from message"""
    media_info = None
    
    if message.video:
        media = message.video
        media_info = {
            "file_type": "video",
            "file_name": media.file_name or f"video_{message.id}.mp4",
            "file_size": media.file_size,
            "duration": media.duration,
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id
        }
    elif message.document:
        media = message.document
        media_info = {
            "file_type": "document",
            "file_name": media.file_name or f"document_{message.id}",
            "file_size": media.file_size,
            "mime_type": media.mime_type,
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id
        }
    elif message.audio:
        media = message.audio
        media_info = {
            "file_type": "audio",
            "file_name": media.file_name or f"audio_{message.id}.mp3",
            "file_size": media.file_size,
            "duration": media.duration,
            "performer": media.performer,
            "title": media.title,
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id
        }
    elif message.photo:
        media = message.photo
        media_info = {
            "file_type": "photo",
            "file_name": f"photo_{message.id}.jpg",
            "file_size": media.file_size,
            "width": media.width,
            "height": media.height,
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id
        }
    elif message.animation:
        media = message.animation
        media_info = {
            "file_type": "gif",
            "file_name": media.file_name or f"gif_{message.id}.gif",
            "file_size": media.file_size,
            "duration": media.duration,
            "width": media.width,
            "height": media.height,
            "file_unique_id": media.file_unique_id,
            "file_id": media.file_id
        }
    
    if media_info:
        # Add common fields
        media_info.update({
            "message_id": message.id,
            "chat_id": message.chat.id,
            "chat_title": message.chat.title,
            "date": message.date,
            "caption": message.caption or "",
            "from_user": message.from_user.id if message.from_user else None
        })
    
    return media_info

def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (text.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;")
               .replace("'", "&#x27;"))

def get_file_type_emoji(file_type: str) -> str:
    """Get emoji for file type"""
    emojis = {
        "video": "🎬",
        "document": "📄",
        "audio": "🎵",
        "photo": "🖼",
        "gif": "🎞"
    }
    return emojis.get(file_type, "📁")

