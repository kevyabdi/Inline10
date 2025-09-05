"""
Inline Query Handler for Search Functionality
"""

import logging
from pyrogram import Client
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InlineQueryResultCachedVideo, InlineQueryResultCachedDocument,
    InlineQueryResultCachedAudio, InlineQueryResultCachedPhoto,
    InlineQueryResultCachedAnimation,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
)
from utils import is_subscribed, is_authorized_user, format_file_size, get_file_type_emoji
from config import Config

logger = logging.getLogger(__name__)

@Client.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    """Handle inline queries for media search"""
    user_id = query.from_user.id
    search_query = query.query.strip()

    # ✅ Check subscription
    if not await is_subscribed(client, user_id):
        results = [
            InlineQueryResultArticle(
                id="auth_required",
                title="🔒 Authorization Required",
                description="Join our channel to use this bot",
                input_message_content=InputTextMessageContent(
                    "🔒 You need to join our channel to use this bot.\n"
                    f"Start the bot @{(await client.get_me()).username} for more information."
                )
            )
        ]
        await query.answer(results=results, cache_time=0, is_personal=True)
        return

    # ✅ Check authorization
    if not await is_authorized_user(user_id, client):
        results = [
            InlineQueryResultArticle(
                id="unauthorized",
                title="❌ Unauthorized Access",
                description="Contact admin for access",
                input_message_content=InputTextMessageContent(
                    "❌ You are not authorized to use this bot.\n"
                    "Contact an administrator for access."
                )
            )
        ]
        await query.answer(results=results, cache_time=0, is_personal=True)
        return

    # ✅ Empty query → show recent videos (10 latest)
    if not search_query:
        try:
            # Show 10 latest videos when no search query is provided
            recent_media = await client.db.get_recent_videos(limit=10)
            results = []
            if recent_media:
                for idx, media in enumerate(recent_media):
                    try:
                        result = create_inline_result(media, idx)
                        if result:
                            results.append(result)
                    except Exception as media_error:
                        # Skip problematic media files and continue
                        logger.warning(f"Skipped media at index {idx}: {media_error}")
                        continue

            if not results:
                results = [
                    InlineQueryResultArticle(
                        id="no_videos",
                        title="🎬 No Recent Videos",
                        description="Upload videos to channels to see them here",
                        input_message_content=InputTextMessageContent(
                            "🎬 <b>No recent videos found</b>\n\n"
                            "Recent videos will appear here when you upload them.\n"
                            "Type a search term to find specific content."
                        )
                    )
                ]

            await query.answer(results=results, cache_time=5, is_personal=True)
            return

        except Exception as e:
            logger.error(f"Error getting recent media: {e}")
            results = [
                InlineQueryResultArticle(
                    id="error_fallback",
                    title="🔍 Search Your Media",
                    description="Type to search your media collection",
                    input_message_content=InputTextMessageContent(
                        "🔍 <b>Search your media</b>\n\n"
                        "Type your search query to find specific content."
                    )
                )
            ]
            await query.answer(results=results, cache_time=5, is_personal=True)
            return

    # ✅ Parse query for file type filter
    file_type_filter = None
    if " | " in search_query:
        search_query, file_type_filter = search_query.split(" | ", 1)
        file_type_filter = file_type_filter.strip().lower()
        search_query = search_query.strip()

    try:
        media_results = await client.db.search_media(search_query, file_type_filter)
        results = []

        if not media_results:
            results = [
                InlineQueryResultArticle(
                    id="no_results",
                    title="🔍 Not Found",
                    description=f"No results for '{search_query}'",
                    input_message_content=InputTextMessageContent(
                        f"🔍 <b>Not Found</b>\n\nNo videos found for: <code>{search_query}</code>"
                    )
                )
            ]
        else:
            for idx, media in enumerate(media_results):
                result = create_inline_result(media, idx)
                if result:
                    results.append(result)

        await query.answer(
            results=results[:50],
            cache_time=Config.CACHE_TIME,
            is_personal=True,
            next_offset=str(len(results)) if len(media_results) >= Config.MAX_RESULTS else ""
        )

    except Exception as e:
        logger.error(f"Error handling inline query: {e}")
        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Search Error",
                description="An error occurred while searching",
                input_message_content=InputTextMessageContent(
                    "❌ <b>Search Error</b>\n\nPlease try again later."
                )
            )
        ]
        await query.answer(results=results, cache_time=0, is_personal=True)


def create_inline_result(media: dict, index: int):
    """Create inline result based on media type"""
    file_type = media.get("file_type", "document")
    file_name = media.get("file_name", "Unknown")
    file_size = media.get("file_size", 0)
    caption = media.get("caption", "")
    file_id = media.get("file_id")
    
    # Validate required fields
    if not file_id:
        logger.error(f"Missing file_id for media at index {index}")
        return None
    
    if not file_type:
        file_type = "document"

    display_name = file_name if len(file_name) <= 50 else file_name[:47] + "..."
    description = format_file_size(file_size) if file_size else "Unknown size"
    if caption:
        description += " • " + (caption[:100] + "..." if len(caption) > 100 else caption)

    emoji = get_file_type_emoji(file_type)
    title = f"{emoji} {display_name}"

    try:
        if file_type == "video":
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔍 Search", switch_inline_query_current_chat=""),
                    InlineKeyboardButton("📢 Join", url="https://t.me/daawotv")
                ]
            ])
            try:
                return InlineQueryResultCachedVideo(
                    id=f"video_{index}",
                    video_file_id=file_id,
                    title=title,
                    description=description,
                    caption=f"{file_name}\n\nKUSO BIIT @DAAWOTV",
                    reply_markup=keyboard
                )
            except Exception as video_error:
                # If video fails due to content type issues, fallback to document
                logger.warning(f"Video inline result failed, falling back to document: {video_error}")
                return InlineQueryResultCachedDocument(
                    id=f"doc_fallback_{index}",
                    title=f"📄 {display_name}",
                    description=description,
                    document_file_id=file_id
                )

        elif file_type == "document":
            return InlineQueryResultCachedDocument(
                id=f"doc_{index}",
                title=title,
                description=description,
                document_file_id=file_id
            )

        elif file_type == "audio":
            return InlineQueryResultCachedAudio(
                id=f"audio_{index}",
                audio_file_id=file_id
            )

        elif file_type == "photo":
            return InlineQueryResultCachedPhoto(
                id=f"photo_{index}",
                photo_file_id=file_id
            )

        elif file_type == "gif":
            return InlineQueryResultCachedAnimation(
                id=f"gif_{index}",
                animation_file_id=file_id,
                title=title
            )

        else:
            return InlineQueryResultCachedDocument(
                id=f"file_{index}",
                title=title,
                description=description,
                document_file_id=file_id
            )

    except Exception as e:
        logger.error(f"Error creating inline result for {file_type}: {e}")
        return None
