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

    # Increased default poll interval to 10s to be gentler on the API
    # and reduce the chance of rate limiting on my account.
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))

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
