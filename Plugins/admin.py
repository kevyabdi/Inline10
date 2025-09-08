"""
Admin Commands Handler
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from utils import is_admin, format_file_size
from config import Config
import asyncio

logger = logging.getLogger(__name__)

# Admin filter
admin_filter = filters.user(Config.ADMINS)

@Client.on_message(filters.command("stats") & admin_filter)
async def stats_command(client: Client, message: Message):
    """Show bot statistics"""
    try:
        stats = await client.db.get_stats()
        total_size = await client.db.get_total_size()
        user_count = await client.db.get_user_count()
        
        stats_text = f"""
📊 <b>Bot Statistics</b>

👥 <b>Total Users:</b> {user_count:,}
📁 <b>Total Files:</b> {stats['total_files']:,}
💾 <b>Total Size:</b> {format_file_size(total_size)}

<b>📂 Files by Type:</b>
"""
        
        for file_type, count in stats['by_type'].items():
            emoji_map = {
                "video": "🎬",
                "document": "📄",
                "audio": "🎵", 
                "photo": "🖼",
                "gif": "🎞"
            }
            emoji = emoji_map.get(file_type, "📎")
            stats_text += f"• {emoji} {file_type.title()}: {count:,}\n"
        
        stats_text += f"\n<b>⚙️ Configuration:</b>\n"
        stats_text += f"• Indexed Channels: {len(Config.CHANNELS)}\n"
        stats_text += f"• Cache Time: {Config.CACHE_TIME}s\n"
        stats_text += f"• Max Results: {Config.MAX_RESULTS}\n"
        stats_text += f"• Caption Filter: {'✅' if Config.USE_CAPTION_FILTER else '❌'}\n"
        
        await message.reply(stats_text)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await message.reply("❌ Error retrieving statistics.")

@Client.on_message(filters.command("total") & admin_filter)
async def total_command(client: Client, message: Message):
    """Show total files count"""
    try:
        stats = await client.db.get_stats()
        total_size = await client.db.get_total_size()
        
        await message.reply(
            f"📊 <b>Total Files:</b> {stats['total_files']:,}\n"
            f"💾 <b>Total Size:</b> {format_file_size(total_size)}"
        )
        
    except Exception as e:
        logger.error(f"Error in total command: {e}")
        await message.reply("❌ Error retrieving total count.")

@Client.on_message(filters.command("broadcast") & admin_filter)
async def broadcast_command(client: Client, message: Message):
    """Broadcast message to all users"""
    if not message.reply_to_message:
        await message.reply("❌ Reply to a message to broadcast it.")
        return
    
    # Get all user IDs from database who have used /start
    all_users = await client.db.get_all_user_ids()
    
    # Filter out banned users
    users = []
    for user_id in all_users:
        if not await client.db.is_banned(user_id):
            users.append(user_id)
    
    if not users:
        await message.reply("❌ No users found to broadcast to.")
        return
    
    broadcast_msg = message.reply_to_message
    success_count = 0
    failed_count = 0
    
    status_msg = await message.reply("📡 <b>Broadcasting...</b>\n\n⏳ Starting broadcast...")
    
    for user_id in users:
        try:
            await broadcast_msg.copy(user_id)
            success_count += 1
            
            # Update status every 10 users
            if (success_count + failed_count) % 10 == 0:
                await status_msg.edit_text(
                    f"📡 <b>Broadcasting...</b>\n\n"
                    f"✅ Sent: {success_count}\n"
                    f"❌ Failed: {failed_count}\n"
                    f"⏳ Progress: {success_count + failed_count}/{len(users)}"
                )
            
            # Sleep to avoid flood limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    
    # Final status
    await status_msg.edit_text(
        f"📡 <b>Broadcast Complete!</b>\n\n"
        f"✅ Successfully sent: {success_count}\n"
        f"❌ Failed: {failed_count}\n"
        f"📊 Total users: {len(users)}"
    )

@Client.on_message(filters.command("ban") & admin_filter)
async def ban_command(client: Client, message: Message):
    """Ban a user from using the bot"""
    args = message.text.split(None, 1)
    
    if len(args) < 2:
        await message.reply("❌ Usage: /ban <user_id>")
        return
    
    try:
        user_id = int(args[1])
        
        # Add to banned users
        await client.db.ban_user(user_id)
        await message.reply(f"✅ User {user_id} has been banned from using the bot.")
            
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await message.reply("❌ Error banning user.")

@Client.on_message(filters.command("unban") & admin_filter)
async def unban_command(client: Client, message: Message):
    """Unban a user"""
    args = message.text.split(None, 1)
    
    if len(args) < 2:
        await message.reply("❌ Usage: /unban <user_id>")
        return
    
    try:
        user_id = int(args[1])
        
        # Remove from banned users
        await client.db.unban_user(user_id)
        await message.reply(f"✅ User {user_id} has been unbanned and can now use the bot.")
            
    except ValueError:
        await message.reply("❌ Invalid user ID. Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await message.reply("❌ Error unbanning user.")

@Client.on_message(filters.command("logger") & admin_filter)
async def logger_command(client: Client, message: Message):
    """Show recent log entries"""
    try:
        # Read last 20 lines from log file
        log_lines = []
        try:
            with open("bot.log", "r", encoding="utf-8") as f:
                log_lines = f.readlines()[-20:]
        except FileNotFoundError:
            await message.reply("❌ Log file not found.")
            return
        
        if not log_lines:
            await message.reply("📋 Log file is empty.")
            return
        
        log_text = "📋 <b>Recent Log Entries:</b>\n\n"
        log_text += "<code>" + "".join(log_lines[-10:]) + "</code>"
        
        if len(log_text) > 4000:
            log_text = log_text[:4000] + "\n... (truncated)"
        
        await message.reply(log_text)
        
    except Exception as e:
        logger.error(f"Error in logger command: {e}")
        await message.reply("❌ Error reading log file.")

@Client.on_message(filters.command("commands") & admin_filter)
async def commands_command(client: Client, message: Message):
    """Show all available admin commands"""
    try:
        commands_text = """
🛠 <b>Admin Commands List</b>

<b>📊 Statistics & Analytics:</b>
• <code>/stats</code> - View comprehensive bot statistics
• <code>/total</code> - Show total files count and storage size
• <code>/top10</code> - Show top searched movies & active users
• <code>/notfound</code> - Show most searched unavailable videos

<b>📁 Media Management:</b>
• <code>/index &lt;channel_id&gt; [limit]</code> - Manually index channel messages
• <code>/delete</code> - Delete media from database (reply to media)

<b>👥 User Management:</b>
• <code>/ban &lt;user_id&gt;</code> - Ban a user from using the bot
• <code>/unban &lt;user_id&gt;</code> - Unban a user
• <code>/broadcast</code> - Send message to all users (reply to message)

<b>🔧 System Management:</b>
• <code>/logger</code> - View recent log entries
• <code>/commands</code> - Show this commands list
• <code>/help</code> - Show general help (user + admin commands)

<b>💡 Usage Tips:</b>
• Reply to messages when using /delete or /broadcast
• Use channel ID with /index (e.g., -1001234567890)
• Check /logger for troubleshooting issues
• Use /stats regularly to monitor bot performance

<b>👨‍💼 Admin Status:</b> ✅ Verified Admin Access
"""
        
        await message.reply(commands_text)
        
    except Exception as e:
        logger.error(f"Error in commands command: {e}")
        await message.reply("❌ Error retrieving commands list.")

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Show help information"""
    
    # Check if user is admin to show admin commands
    is_user_admin = is_admin(message.from_user.id)
    
    help_text = """
ℹ️ <b>Sidee loo isticmaalo Bot-ka Filimada</b>

<b>🔍 Raadinta:</b>
Qor <code>@{bot_username} magaca filimka</code> chat kasta.

<b>🎯 Tusaalooyin:</b>
• <code>@{bot_username} action movies</code>
• <code>@{bot_username} comedy films</code>
• <code>@{bot_username} horror movies</code>
• <code>@{bot_username} "specific movie name"</code>

<b>📝 Tilmaamo:</b>
• Isticmaal erayo gaar ah
• Qor magaca filimka si sax ah
• Isticmaal <code>" "</code> magaca dhabta ah

<b>❓ Caawimaad?</b>
La xidhiidh maamulka bot-ka.@viizet
"""
    
    # Add admin commands if user is admin
    if is_user_admin:
        help_text += """

<b>👨‍💼 Admin Commands:</b>
• <code>/stats</code> - View bot statistics
• <code>/total</code> - Show total files count
• <code>/top10</code> - Show top searched movies & active users
• <code>/notfound</code> - Show most searched unavailable videos
• <code>/broadcast</code> - Send message to all users
• <code>/ban</code> - Ban a user
• <code>/unban</code> - Unban a user
• <code>/logger</code> - View recent logs
• <code>/delete</code> - Delete media from database
"""
    
    # Get bot username for examples
    try:
        bot_me = await client.get_me()
        help_text = help_text.replace("{bot_username}", bot_me.username or "BotUsername")
    except:
        help_text = help_text.replace("{bot_username}", "BotUsername")
    
    await message.reply(help_text)

@Client.on_message(filters.command("delete") & admin_filter)
async def delete_command(client: Client, message: Message):
    """Delete media from database"""
    if not message.reply_to_message:
        await message.reply("❌ Reply to a media message to delete it from database.")
        return
    
    replied_msg = message.reply_to_message
    
    if not (replied_msg.video or replied_msg.document or replied_msg.audio or 
            replied_msg.photo or replied_msg.animation):
        await message.reply("❌ Replied message doesn't contain any media.")
        return
    
    try:
        # Delete from database
        success = await client.db.delete_media(replied_msg.chat.id, replied_msg.id)
        
        if success:
            await message.reply("✅ Media deleted from database successfully.")
        else:
            await message.reply("❌ Media not found in database or already deleted.")
            
    except Exception as e:
        logger.error(f"Error deleting media: {e}")
        await message.reply("❌ Error deleting media from database.")

@Client.on_message(filters.command("top10") & admin_filter)
async def top10_command(client: Client, message: Message):
    """Show top 10 most searched movies and most active users"""
    try:
        # Get top searched movies
        top_movies = await client.db.get_top_searched_movies(10)
        
        # Get most active users
        top_users = await client.db.get_most_active_users(10)
        
        response = "📊 <b>Top 10 Analytics Report</b>\n\n"
        
        # Top searched movies section
        response += "🎬 <b>Most Searched Movies:</b>\n"
        if top_movies:
            for i, movie in enumerate(top_movies, 1):
                query = movie['query']
                count = movie['search_count']
                # Limit query length for display
                if len(query) > 30:
                    query = query[:27] + "..."
                response += f"{i}. <code>{query}</code> - {count:,} searches\n"
        else:
            response += "• No search data available yet\n"
        
        response += "\n👥 <b>Most Active Users:</b>\n"
        if top_users:
            for i, user in enumerate(top_users, 1):
                user_id = user['user_id']
                username = user.get('username')
                first_name = user.get('first_name', 'Unknown')
                search_count = user['search_count']
                
                # Format user display name
                if username:
                    user_display = f"@{username}"
                else:
                    user_display = f"{first_name} ({user_id})"
                
                response += f"{i}. {user_display} - {search_count:,} searches\n"
        else:
            response += "• No user activity data available yet\n"
        
        response += f"\n<i>📈 Data shows search activity patterns for optimization</i>"
        
        await message.reply(response)
        
    except Exception as e:
        logger.error(f"Error in top10 command: {e}")
        await message.reply("❌ Error retrieving top 10 analytics data.")

@Client.on_message(filters.command("notfound") & admin_filter)
async def not_found_command(client: Client, message: Message):
    """Show most searched queries that returned no results"""
    try:
        # Get most searched not found queries
        not_found_searches = await client.db.get_most_searched_not_found(15)
        
        response = "🔍 <b>Most Searched Not Found Videos</b>\n\n"
        response += "📋 <i>Videos users searched for but not available:</i>\n\n"
        
        if not_found_searches:
            for i, search in enumerate(not_found_searches, 1):
                query = search['query']
                count = search['search_count']
                unique_users = search['unique_users']
                
                # Limit query length for display
                if len(query) > 35:
                    query = query[:32] + "..."
                
                response += f"{i}. <code>{query}</code>\n"
                response += f"   🔢 {count:,} searches by {unique_users} users\n\n"
        else:
            response += "• No not found search data available yet\n"
        
        response += "💡 <b>Tip:</b> Add these popular missing videos to increase user satisfaction!\n"
        response += "\n<i>Use /top10 for overall search analytics</i>"
        
        await message.reply(response)
        
    except Exception as e:
        logger.error(f"Error in notfound command: {e}")
        await message.reply("❌ Error retrieving not found search data.")
