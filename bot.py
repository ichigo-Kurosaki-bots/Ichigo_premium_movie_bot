import asyncio
import logging
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

from database import init_database

from handlers.start import (
    register_start_handlers
)

from handlers.search import (
    register_search_handlers
)

from handlers.premium import (
    register_premium_handlers
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
# CHECK CONFIGURATION
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing."
    )

if not API_ID:
    raise RuntimeError(
        "API_ID is missing."
    )

if not API_HASH:
    raise RuntimeError(
        "API_HASH is missing."
    )


# ============================================================
# TELEGRAM CLIENT
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

register_search_handlers(
    app
)

register_premium_handlers(
    app
)

register_admin_handlers(
    app
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
        port=PORT,
        threaded=True
    )


# ============================================================
# STARTUP
# ============================================================

async def main():

    logger.info(
        "Starting Premium Movie Bot..."
    )

    # Initialize MongoDB.
    await init_database()

    logger.info(
        "MongoDB initialized."
    )

    # Start Flask in another thread.
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    logger.info(
        f"Web server started on port {PORT}."
    )

    # Start Telegram bot.
    await app.start()

    me = await app.get_me()

    logger.info(
        "========================================"
    )

    logger.info(
        "TELEGRAM BOT CONNECTED"
    )

    logger.info(
        f"Username: @{me.username}"
    )

    logger.info(
        f"Bot ID: {me.id}"
    )

    logger.info(
        "========================================"
    )

    # Keep the Telegram client alive.
    await asyncio.Event().wait()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped."
        )

    except Exception as e:

        logger.exception(
            f"Critical startup error: {e}"
        )
