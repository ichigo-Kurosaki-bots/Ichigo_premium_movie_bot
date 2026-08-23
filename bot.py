import asyncio
import logging
import os
import threading

from flask import Flask

from pyrogram import Client

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    PORT,
    LOG_LEVEL
)

from database import (
    init_database,
    close_database
)

from handlers.start import (
    register_start_handlers
)

from handlers.premium import (
    register_premium_handlers
)

from handlers.search import (
    register_search_handlers
)

from handlers.admin import (
    register_admin_handlers
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=getattr(
        logging,
        LOG_LEVEL.upper(),
        logging.INFO
    ),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(
    "premium_movie_bot"
)


# ============================================================
# FLASK WEB SERVER
# ============================================================

web_app = Flask(
    __name__
)


@web_app.route("/")
def home():

    return (
        "Premium Movie Bot is running."
    )


@web_app.route("/health")
def health():

    return {
        "status": "ok",
        "bot": "running"
    }


def run_web_server():

    web_app.run(
        host="0.0.0.0",
        port=PORT
    )


# ============================================================
# VALIDATE CONFIG
# ============================================================

def validate_config():

    missing = []

    if not BOT_TOKEN:
        missing.append(
            "BOT_TOKEN"
        )

    if not API_ID:
        missing.append(
            "API_ID"
        )

    if not API_HASH:
        missing.append(
            "API_HASH"
        )

    if missing:

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# PYROGRAM CLIENT
# ============================================================

app = Client(
    "premium_movie_bot",

    api_id=API_ID,

    api_hash=API_HASH,

    bot_token=BOT_TOKEN,

    workers=4
)


# ============================================================
# REGISTER HANDLERS
# ============================================================

register_start_handlers(
    app
)

register_premium_handlers(
    app
)

register_search_handlers(
    app
)

register_admin_handlers(
    app
)

# ============================================================
# DEBUG UPDATE HANDLER
# ============================================================

from pyrogram import filters


@app.on_message(
    filters.all,
    group=99
)
async def debug_update_handler(client, message):

    logger.info(
        "UPDATE RECEIVED | chat_id=%s | user_id=%s | text=%r",
        message.chat.id if message.chat else None,
        message.from_user.id if message.from_user else None,
        message.text
    )

# ============================================================
# MAIN
# ============================================================

async def main():

    validate_config()

    logger.info(
        "Starting Premium Movie Bot..."
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    await init_database()

    logger.info(
        "MongoDB initialized."
    )

    # --------------------------------------------------------
    # START TELEGRAM CLIENT
    # --------------------------------------------------------

    await app.start()

    me = await app.get_me()

    logger.info(
        "Telegram bot connected."
    )

    logger.info(
        "Bot username: @%s",
        me.username
    )

    logger.info(
        "Bot ID: %s",
        me.id
    )

    # --------------------------------------------------------
    # KEEP PROCESS ALIVE
    # --------------------------------------------------------

    try:

        await asyncio.Event().wait()

    finally:

        logger.info(
            "Stopping bot..."
        )

        await app.stop()

        await close_database()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # START WEB SERVER FOR RENDER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    logger.info(
        "Web server started on port %s.",
        PORT
    )

    # --------------------------------------------------------
    # START BOT
    # --------------------------------------------------------

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped by user."
        )

    except Exception as e:

        logger.exception(
            "Critical startup error: %s",
            e
        )
