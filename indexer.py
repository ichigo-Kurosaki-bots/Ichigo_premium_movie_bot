import asyncio
from datetime import datetime

from pyrogram.errors import FloodWait

from database import (
    add_media,
    settings_collection
)

from utils.helpers import (
    clean_title,
    get_message_title,
    get_search_key,
    get_original_filename,
    is_media_message
)

from config import (
    DATABASE_CHANNEL_ID,
    INDEX_BATCH_SIZE
)


# ============================================================
# INDEXER STATE
# ============================================================

INDEX_RUNNING = False


# ============================================================
# BUILD MEDIA DATA
# ============================================================

def build_media_data(message):

    if not is_media_message(message):

        return None

    title = get_message_title(
        message
    )

    original_filename = (
        get_original_filename(
            message
        )
    )

    # --------------------------------------------------------
    # FILE INFORMATION
    # --------------------------------------------------------

    if message.document:

        file_id = (
            message.document.file_id
        )

        file_size = (
            message.document.file_size
            or 0
        )

        mime_type = (
            message.document.mime_type
            or ""
        )

        media_type = "document"

    elif message.video:

        file_id = (
            message.video.file_id
        )

        file_size = (
            message.video.file_size
            or 0
        )

        mime_type = (
            message.video.mime_type
            or ""
        )

        media_type = "video"

    elif message.audio:

        file_id = (
            message.audio.file_id
        )

        file_size = (
            message.audio.file_size
            or 0
        )

        mime_type = (
            message.audio.mime_type
            or ""
        )

        media_type = "audio"

    else:

        return None


    # --------------------------------------------------------
    # DATABASE DOCUMENT
    # --------------------------------------------------------

    return {

        "channel_id":
            message.chat.id,

        "message_id":
            message.id,

        "title":
            title,

        "title_key":
            clean_title(title),

        "search_key":
            get_search_key(title),

        "file_name":
            original_filename,

        "file_id":
            file_id,

        "file_size":
            file_size,

        "mime_type":
            mime_type,

        "media_type":
            media_type,

        "caption":
            message.caption or "",

        "indexed_at":
            datetime.utcnow()
    }


# ============================================================
# INDEX ONE MESSAGE
# ============================================================

async def index_message(message):

    data = build_media_data(
        message
    )

    if not data:
        return False

    await add_media(
        data
    )

    return True


# ============================================================
# SAVE INDEXER STATE
# ============================================================

async def save_state(
    last_message_id,
    indexed_count
):

    await settings_collection.update_one(
        {
            "_id": "indexer"
        },
        {
            "$set": {
                "last_message_id": last_message_id,
                "indexed_count": indexed_count,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )


# ============================================================
# GET INDEXER STATE
# ============================================================

async def get_state():

    state = await settings_collection.find_one(
        {
            "_id": "indexer"
        }
    )

    if not state:

        return {
            "last_message_id": 0,
            "indexed_count": 0
        }

    return state


# ============================================================
# STOP INDEXING
# ============================================================

def stop_indexing():

    global INDEX_RUNNING

    INDEX_RUNNING = False


# ============================================================
# INDEX CHANNEL
# ============================================================

async def index_channel(
    app,
    status_message=None
):

    global INDEX_RUNNING

    if INDEX_RUNNING:

        return 0

    if not DATABASE_CHANNEL_ID:

        raise RuntimeError(
            "DATABASE_CHANNEL_ID is not configured."
        )

    INDEX_RUNNING = True

    state = await get_state()

    last_message_id = state.get(
        "last_message_id",
        0
    )

    indexed_count = state.get(
        "indexed_count",
        0
    )

    current_batch = 0

    print(
        "========================================"
    )

    print(
        "DATABASE INDEXER STARTED"
    )

    print(
        f"Resume message ID: {last_message_id}"
    )

    print(
        f"Already indexed: {indexed_count}"
    )

    print(
        "========================================"
    )

    try:

        async for message in app.get_chat_history(
            DATABASE_CHANNEL_ID
        ):

            if not INDEX_RUNNING:

                print(
                    "Indexer stopped by administrator."
                )

                break

            # ------------------------------------------------
            # Skip messages already processed.
            # ------------------------------------------------

            if (
                last_message_id
                and message.id >= last_message_id
            ):
                continue

            # ------------------------------------------------
            # Process media only.
            # ------------------------------------------------

            try:

                if await index_message(
                    message
                ):

                    indexed_count += 1

                    current_batch += 1

            except FloodWait as e:

                print(
                    f"FloodWait: sleeping "
                    f"{e.value} seconds."
                )

                await asyncio.sleep(
                    e.value
                )

                continue

            except Exception as e:

                print(
                    f"Message {message.id} "
                    f"index error: {e}"
                )

            # ------------------------------------------------
            # Save progress after every batch.
            # ------------------------------------------------

            if current_batch >= INDEX_BATCH_SIZE:

                last_message_id = message.id

                await save_state(
                    last_message_id,
                    indexed_count
                )

                current_batch = 0

                print(
                    f"Indexed: {indexed_count} | "
                    f"Message: {message.id}"
                )

                # Update Telegram status.
                if status_message:

                    try:

                        await status_message.edit_text(
                            "🔄 <b>Indexing Database...</b>\n\n"
                            f"🎬 Indexed: "
                            f"<b>{indexed_count}</b>\n"
                            f"🆔 Current message: "
                            f"<code>{message.id}</code>\n\n"
                            "The process can be resumed "
                            "if the bot restarts."
                        )

                    except Exception:
                        pass

        # ----------------------------------------------------
        # Save final progress.
        # ----------------------------------------------------

        if last_message_id:

            await save_state(
                last_message_id,
                indexed_count
            )

    finally:

        INDEX_RUNNING = False

    print(
        "========================================"
    )

    print(
        f"INDEXING FINISHED: {indexed_count}"
    )

    print(
        "========================================"
    )

    return indexed_count


# ============================================================
# INDEXER STATUS
# ============================================================

async def get_index_status():

    state = await get_state()

    return {
        "running": INDEX_RUNNING,

        "last_message_id": state.get(
            "last_message_id",
            0
        ),

        "indexed_count": state.get(
            "indexed_count",
            0
        ),

        "updated_at": state.get(
            "updated_at"
        )
        }
