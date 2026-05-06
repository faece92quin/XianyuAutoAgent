#!/usr/bin/env python3
"""
XianyuAutoAgent - Main Entry Point

Automatically replies to Xianyu (闲鱼) messages using AI agents.
Fork of shaxiu/XianyuAutoAgent
"""

import asyncio
import os
import signal
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

from XianyuApis import XianyuApis
from XianyuAgent import XianyuReplyBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("XianyuAutoAgent")


def validate_env() -> bool:
    """Validate required environment variables are set."""
    required_vars = [
        "COOKIES_STR",
        "AI_API_KEY",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        logger.error("Please copy .env.example to .env and fill in the values.")
        return False
    return True


async def run_agent(apis: XianyuApis, bot: XianyuReplyBot) -> None:
    """Main agent loop — polls for new messages and replies."""
    logger.info("XianyuAutoAgent started at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Verify login status before starting
    if not apis.hasLogin():
        logger.error("Not logged in. Please check your COOKIES_STR in .env")
        return

    logger.info("Login verified. Starting message polling loop...")

    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))

    while True:
        try:
            # Fetch unread conversations
            conversations = apis.get_unread_conversations()
            if conversations:
                logger.info("Found %d unread conversation(s)", len(conversations))
                for conv in conversations:
                    try:
                        await process_conversation(apis, bot, conv)
                    except Exception as e:
                        logger.error("Error processing conversation %s: %s", conv.get("id", "?"), e)
            await asyncio.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error("Unexpected error in main loop: %s", e, exc_info=True)
            await asyncio.sleep(poll_interval * 2)  # Back off on error


async def process_conversation(apis: XianyuApis, bot: XianyuReplyBot, conv: dict) -> None:
    """Process a single conversation and send an AI-generated reply."""
    conv_id = conv.get("id")
    item_id = conv.get("item_id")
    last_message = conv.get("last_message", "")

    if not last_message:
        return

    logger.info("Processing conversation %s | item: %s | msg: %s", conv_id, item_id, last_message[:50])

    # Generate reply using the AI agent
    reply = await bot.generate_reply(
        conversation_id=conv_id,
        item_id=item_id,
        user_message=last_message,
        context=conv.get("context", {}),
    )

    if reply:
        success = apis.send_message(conv_id=conv_id, content=reply)
        if success:
            logger.info("Replied to %s: %s", conv_id, reply[:80])
        else:
            logger.warning("Failed to send reply to conversation %s", conv_id)
    else:
        logger.warning("No reply generated for conversation %s", conv_id)


def handle_shutdown(signum, frame):
    """Handle OS shutdown signals gracefully."""
    logger.info("Received signal %d, exiting...", signum)
    sys.exit(0)


def main():
    """Application entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("=" * 50)
    logger.info("  XianyuAutoAgent")
    logger.info("=" * 50)

    if not validate_env():
        sys.exit(1)

    # Initialize API client and AI bot
    cookies_str = os.getenv("COOKIES_STR", "")
    apis = XianyuApis(cookies_str=cookies_str)
    bot = XianyuReplyBot()

    # Run the async agent loop
    try:
        asyncio.run(run_agent(apis, bot))
    except SystemExit:
        pass
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)

    logger.info("XianyuAutoAgent stopped.")


if __name__ == "__main__":
    main()
