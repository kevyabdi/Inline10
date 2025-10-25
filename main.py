#!/usr/bin/env python33
"""
Telegram Media Search Bot - Main Entry Point
"""

import asyncio
import logging
from bot import MediaSearchBot
from keep_alive import keep_alive   # small web server for uptime (Render/Replit)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        # Start keep-alive server (important for Render/Replit uptime)
        keep_alive()

        # Initialize and start the bot
        bot = MediaSearchBot()
        await bot.start()
        logger.info("✅ Bot Started successfully!")

        # Keep running
        await idle()

    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}", exc_info=True)


if __name__ == "__main__":
    import pyrogram
    from pyrogram import idle

    asyncio.run(main())
