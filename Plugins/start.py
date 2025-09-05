"""
Start Command Handler
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils import is_subscribed, is_authorized_user
from config import Config

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    user = message.from_user
    
    # Track user in database
    try:
        await client.db.add_user(user.id, user.username, user.first_name)
    except Exception as e:
        logger.error(f"Error tracking user {user.id}: {e}")
    
    # Check if user is subscribed to auth channel
    if not await is_subscribed(client, user.id):
        auth_channel_link = f"https://t.me/{Config.AUTH_CHANNEL}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url=auth_channel_link)],
            [InlineKeyboardButton("Check Subscription", callback_data="check_sub")]
        ])
        
        await message.reply(
            "🔒 <b>Access Restricted</b>\n\n"
            "You need to join our channel to use this bot.\n"
            "Click the button below to join and then check your subscription.",
            reply_markup=keyboard
        )
        return
    
    # Check if user is authorized
    if not await is_authorized_user(user.id, client):
        await message.reply(
            "❌ <b>Unauthorized Access</b>\n\n"
            "You are not authorized to use this bot.\n"
            "Contact an administrator for access."
        )
        return
    
    # Welcome message
    bot_username = (await client.get_me()).username
    
    welcome_text = f"""
🎬 <b>Soo dhawoow Bot-ka Filimada!</b>

Salaan {user.first_name}! Waxaan ku caawinayaa raadinta filimada.

<b>Sidee loo isticmaalo:</b>
• Qor <code>@{bot_username} magaca filimka</code> chat kasta
• Filimka rabtay ayaan ku siinayaa
• Riix natijada aad rabto

<b>Tusaale:</b>
• <code>@{bot_username} action movies</code>
• <code>@{bot_username} comedy films</code>

Bilow qorista <code>@{bot_username}</code> si aad u raadiso filimada!
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])
    
    await message.reply(welcome_text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("check_sub"))
async def check_subscription(client: Client, callback_query):
    """Check user subscription status"""
    user_id = callback_query.from_user.id
    
    if await is_subscribed(client, user_id):
        await callback_query.answer("✅ Subscription verified! You can now use the bot.", show_alert=True)
        # Send start message
        await start_command(client, callback_query.message)
    else:
        await callback_query.answer("❌ Please join the channel first!", show_alert=True)

@Client.on_callback_query(filters.regex("help"))
async def handle_callbacks(client: Client, callback_query):
    """Handle callback queries"""
    data = callback_query.data
    
    if data == "help":
        help_text = """
ℹ️ <b>Sidee loo isticmaalo Bot-ka Filimada</b>

<b>🔍 Raadinta:</b>
Qor <code>@botusername magaca filimka</code> chat kasta.

<b>🎯 Tusaalooyin:</b>
• <code>@botusername action movies</code>
• <code>@botusername comedy films</code>
• <code>@botusername horror movies</code>
• <code>@botusername "specific movie name"</code>

<b>📝 Tilmaamo:</b>
• Isticmaal erayo gaar ah
• Qor magaca filimka si sax ah
• Isticmaal <code>" "</code> magaca dhabta ah

<b>❓ Caawimaad?</b>
La xidhiidh maamulka bot-ka.
"""
        await callback_query.edit_message_text(help_text)

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

def get_file_type_emoji(file_type: str) -> str:
    """Get emoji for file type"""
    emojis = {
        "video": "🎬",
        "document": "📄", 
        "audio": "🎵",
        "photo": "🖼",
        "gif": "🎞"
    }
    return emojis.get(file_type, "📎")
