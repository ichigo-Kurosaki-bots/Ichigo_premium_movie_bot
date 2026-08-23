import asyncio
import logging

from pyrogram import Client

from config import (
    DATABASE_CHANNEL_ID,
    INDEX_BATCH_SIZE
)

from database import (
    add_media,
    get_indexer_state,
    save_indexer_state
)

from utils.helpers import (
    get_message_title,
    get_original_filename,
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
# GET MEDIA INFORMATION
# ============================================================

def get_media_information(message):

    media_type = None
    file_name = ""
    file_size = 0
    mime_type = ""

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

    title = get_message_title(
        message
    )

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

        "indexed_at": None
    }


# ============================================================
# INDEX ONE MESSAGE
# ============================================================

async def index_message(message):

    if not is_media_message(
        message
    ):

        return False

    data = get_media_information(
        message
    )

    if not data:

        return False

    from datetime import datetime

    data["indexed_at"] = (
        datetime.utcnow()
    )

    await add_media(
        data
    )

    return True


# ============================================================
# INDEX DATABASE CHANNEL
# ============================================================

async def index_database_channel(
    app,
    force=False
):

    global indexer_running

    if indexer_running:

        logger.warning(
            "Indexer is already running."
        )

        return {
            "success": False,
            "message": "Indexer is already running."
        }

    if not DATABASE_CHANNEL_ID:

        return {
            "success": False,
            "message": (
                "DATABASE_CHANNEL_ID is not configured."
            )
        }

    indexer_running = True

    indexed_count = 0
    scanned_count = 0

    try:

        # ----------------------------------------------------
        # GET LAST INDEXED MESSAGE
        # ----------------------------------------------------

        state = await get_indexer_state()

        last_message_id = state.get(
            "last_message_id",
            0
        )

        if force:

            last_message_id = 0

            indexed_count = 0

        logger.info(
            "Starting database channel indexer."
        )

        logger.info(
            "Starting after message ID: %s",
            last_message_id
        )

        # ----------------------------------------------------
        # TELEGRAM HISTORY
        # ----------------------------------------------------

        async for message in app.get_chat_history(
            DATABASE_CHANNEL_ID
        ):

            # ------------------------------------------------
            # STOP AT ALREADY INDEXED MESSAGES
            # ------------------------------------------------

            if (
                not force
                and message.id <= last_message_id
            ):

                break

            scanned_count += 1

            # ------------------------------------------------
            # INDEX MEDIA
            # ------------------------------------------------

            try:

                indexed = await index_message(
                    message
                )

                if indexed:

                    indexed_count += 1

            except Exception as e:

                logger.exception(
                    "Failed to index message %s: %s",
                    message.id,
                    e
                )

            # ------------------------------------------------
            # SAVE PROGRESS
            # ------------------------------------------------

            if (
                scanned_count
                % INDEX_BATCH_SIZE
                == 0
            ):

                await save_indexer_state(
                    last_message_id=message.id,
                    indexed_count=(
                        state.get(
                            "indexed_count",
                            0
                        )
                        + indexed_count
                    )
                )

                logger.info(
                    "Indexer progress: "
                    "scanned=%s indexed=%s "
                    "last_message=%s",
                    scanned_count,
                    indexed_count,
                    message.id
                )

                # Give Telegram/network a little breathing room.
                await asyncio.sleep(
                    0.2
                )

        # ----------------------------------------------------
        # FINAL STATE
        # ----------------------------------------------------

        final_last_message_id = (
            last_message_id
        )

        if scanned_count > 0:

            # The history iterator processes newest
            # messages first, so get the newest scanned
            # message through the state saved during batches.
            current_state = (
                await get_indexer_state()
            )

            final_last_message_id = (
                current_state.get(
                    "last_message_id",
                    last_message_id
                )
            )

        await save_indexer_state(
            last_message_id=(
                final_last_message_id
            ),
            indexed_count=(
                state.get(
                    "indexed_count",
                    0
                )
                + indexed_count
            )
        )

        logger.info(
            "Indexer completed. "
            "Scanned=%s Indexed=%s",
            scanned_count,
            indexed_count
        )

        return {
            "success": True,
            "scanned": scanned_count,
            "indexed": indexed_count
        }

    except Exception as e:

        logger.exception(
            "Database channel indexer failed: %s",
            e
        )

        return {
            "success": False,
            "message": str(e),
            "scanned": scanned_count,
            "indexed": indexed_count
        }

    finally:

        indexer_running = False


# ============================================================
# START INDEXING
# ============================================================

async def start_indexer(
    app,
    force=False
):

    return await index_database_channel(
        app,
        force=force
    )


# ============================================================
# CHECK INDEXER
# ============================================================

def is_indexer_running():

    return indexer_running
