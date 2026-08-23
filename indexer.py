import logging
from datetime import datetime

from config import DATABASE_CHANNEL_ID

from database import (
    add_media,
    get_indexer_state,
    save_indexer_state
)

from utils.helpers import (
    get_message_title,
    get_search_key,
    human_size,
    is_media_message
)


logger = logging.getLogger(__name__)


# ============================================================
# INDEXER STATE
# ============================================================

indexer_running = False


# ============================================================
# CHECK DATABASE CHANNEL
# ============================================================

def is_database_channel(message):

    if not message:
        return False

    if not message.chat:
        return False

    try:

        return int(message.chat.id) == int(
            DATABASE_CHANNEL_ID
        )

    except (TypeError, ValueError):

        return False


# ============================================================
# GET MEDIA INFORMATION
# ============================================================

def get_media_information(message):

    media_type = None

    file_name = ""

    file_size = 0

    mime_type = ""

    # --------------------------------------------------------
    # DOCUMENT
    # --------------------------------------------------------

    if message.document:

        media_type = "document"

        file_name = (
            message.document.file_name
            or ""
        )

        file_size = (
            message.document.file_size
            or 0
        )

        mime_type = (
            message.document.mime_type
            or ""
        )

    # --------------------------------------------------------
    # VIDEO
    # --------------------------------------------------------

    elif message.video:

        media_type = "video"

        file_name = (
            message.video.file_name
            or ""
        )

        file_size = (
            message.video.file_size
            or 0
        )

        mime_type = (
            message.video.mime_type
            or ""
        )

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    elif message.audio:

        media_type = "audio"

        file_name = (
            message.audio.file_name
            or ""
        )

        file_size = (
            message.audio.file_size
            or 0
        )

        mime_type = (
            message.audio.mime_type
            or ""
        )

    else:

        return None

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = get_message_title(
        message
    )

    # --------------------------------------------------------
    # DATABASE DOCUMENT
    # --------------------------------------------------------

    return {

        "channel_id": message.chat.id,

        "message_id": message.id,

        "title": title,

        "title_key": get_search_key(
            title
        ),

        "search_key": get_search_key(
            title
        ),

        "file_name": file_name,

        "file_size": file_size,

        "file_size_text": human_size(
            file_size
        ),

        "mime_type": mime_type,

        "media_type": media_type,

        "caption": (
            message.caption
            or ""
        ),

        "date": message.date,

        "indexed_at": datetime.utcnow()
    }


# ============================================================
# INDEX ONE MESSAGE
# ============================================================

async def index_message(message):

    # --------------------------------------------------------
    # ONLY DATABASE CHANNEL
    # --------------------------------------------------------

    if not is_database_channel(
        message
    ):

        return False

    # --------------------------------------------------------
    # CHECK MEDIA
    # --------------------------------------------------------

    if not is_media_message(
        message
    ):

        return False

    # --------------------------------------------------------
    # GET MEDIA DATA
    # --------------------------------------------------------

    data = get_media_information(
        message
    )

    if not data:

        return False

    # --------------------------------------------------------
    # SAVE TO MONGODB
    # --------------------------------------------------------

    try:

        success = await add_media(
            data
        )

        if success:

            logger.info(
                "Indexed message %s",
                message.id
            )

            return True

        return False

    except Exception as e:

        logger.exception(
            "Failed to index message %s: %s",
            message.id,
            e
        )

        return False


# ============================================================
# AUTO INDEX DATABASE CHANNEL POST
# ============================================================

async def handle_database_post(
    client,
    message
):

    if not is_database_channel(
        message
    ):

        return

    if not is_media_message(
        message
    ):

        return

    try:

        indexed = await index_message(
            message
        )

        if indexed:

            state = await get_indexer_state()

            current_count = state.get(
                "indexed_count",
                0
            )

            await save_indexer_state(

                last_message_id=message.id,

                indexed_count=current_count + 1
            )

            logger.info(
                "New database file indexed: "
                "message_id=%s",
                message.id
            )

    except Exception as e:

        logger.exception(
            "Automatic indexing failed: %s",
            e
        )

# ============================================================
# HANDLE NEW DATABASE CHANNEL POST
# ============================================================

async def handle_database_post(
    client,
    message
):

    try:

        if message.chat.id != DATABASE_CHANNEL_ID:
            return False

        indexed = await index_message(
            message
        )

        if indexed:

            state = await get_indexer_state()

            current_count = state.get(
                "indexed_count",
                0
            )

            await save_indexer_state(
                last_message_id=message.id,
                indexed_count=current_count + 1
            )

            logger.info(
                "Auto-indexed message %s",
                message.id
            )

            return True

        return False

    except Exception as e:

        logger.exception(
            "Failed to auto-index message %s: %s",
            message.id,
            e
        )

        return False

# ============================================================
# MANUAL INDEX COMMAND
# ============================================================

async def start_indexer(
    app,
    force=False
):

    logger.warning(
        "Manual history indexing is not available "
        "with a Telegram bot account."
    )

    return {

        "success": False,

        "message": (
            "Telegram bots cannot read channel history "
            "using get_chat_history().\n\n"
            "New database files are indexed "
            "automatically when they are posted."
        ),

        "scanned": 0,

        "indexed": 0
    }


# ============================================================
# INDEX DATABASE CHANNEL
# ============================================================

async def index_database_channel(
    app,
    force=False
):

    return await start_indexer(
        app,
        force=force
    )


# ============================================================
# CHECK INDEXER
# ============================================================

def is_indexer_running():

    return indexer_running
