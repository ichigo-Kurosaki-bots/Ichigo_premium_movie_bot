from database import add_media

from utils.helpers import (
    clean_title,
    get_message_title,
    is_media_message
)

from config import (
    DATABASE_CHANNEL_ID,
    INDEX_BATCH_SIZE
)


def build_media_data(message):

    if not is_media_message(message):
        return None

    title = get_message_title(
        message
    )

    file_name = title

    if message.document:

        file_id = message.document.file_id

        file_size = message.document.file_size

        mime_type = message.document.mime_type

    elif message.video:

        file_id = message.video.file_id

        file_size = message.video.file_size

        mime_type = message.video.mime_type

    elif message.audio:

        file_id = message.audio.file_id

        file_size = message.audio.file_size

        mime_type = message.audio.mime_type

    else:

        return None

    return {
        "channel_id": message.chat.id,

        "message_id": message.id,

        "title": title,

        "title_key": clean_title(
            title
        ),

        "file_name": file_name,

        "file_id": file_id,

        "file_size": file_size or 0,

        "mime_type": mime_type or "",

        "caption": message.caption or ""
    }


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


async def index_channel(
    app,
    limit=None
):
    """
    Index existing messages from the
    configured database channel.

    Set limit=None to scan all available
    history.
    """

    if not DATABASE_CHANNEL_ID:

        raise RuntimeError(
            "DATABASE_CHANNEL_ID is not configured."
        )

    count = 0

    async for message in app.get_chat_history(
        DATABASE_CHANNEL_ID
    ):

        if limit is not None and count >= limit:
            break

        if not is_media_message(
            message
        ):
            continue

        try:

            if await index_message(
                message
            ):

                count += 1

                if (
                    count %
                    INDEX_BATCH_SIZE
                    == 0
                ):

                    print(
                        f"Indexed {count} files..."
                    )

        except Exception as e:

            print(
                f"Indexer error "
                f"message={message.id}: {e}"
            )

    print(
        f"Indexing completed. "
        f"Total indexed: {count}"
    )

    return count
