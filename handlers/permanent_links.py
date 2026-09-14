# ============================================================
# handlers/permanent_links.py
# ============================================================

import logging
import re

from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import DATABASE_CHANNEL_ID
from handlers.fsub import check_all_fsubs, send_fsub_message


logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

# Maximum number of files allowed in one batch link.
# This prevents accidental huge message floods.
MAX_BATCH_FILES = 50


# ============================================================
# HELPERS
# ============================================================

def get_message_id_from_link(text):
    """
    Extract Telegram message ID from:
    
    https://t.me/c/1234567890/123
    https://t.me/channelname/123
    """
    if not text:
        return None

    text = text.strip()

    # Private channel link
    match = re.search(
        r"(?:https?://)?t\.me/c/(\d+)/(\d+)",
        text
    )

    if match:
        channel_number = match.group(1)
        message_id = int(match.group(2))

        channel_id = int(
            "-100" + channel_number
        )

        return channel_id, message_id

    # Public channel link
    match = re.search(
        r"(?:https?://)?t\.me/([A-Za-z0-9_]+)/(\d+)",
        text
    )

    if match:
        username = match.group(1)
        message_id = int(match.group(2))

        return username, message_id

    return None


def parse_message_reference(value):
    """
    Supports:

    12345

    https://t.me/c/1234567890/12345

    https://t.me/channel/12345
    """

    value = value.strip()

    if value.isdigit():
        return DATABASE_CHANNEL_ID, int(value)

    return get_message_id_from_link(value)


def make_single_token(message_id):
    """
    Protected permanent single-file link.
    """
    return f"pl_{message_id}"


def make_batch_token(first_id, last_id, protected=False):
    """
    Batch token.
    """
    prefix = "pb_" if protected else "ba_"

    return f"{prefix}{first_id}_{last_id}"


async def get_bot_username(client):
    """
    Get bot username for permanent links.
    """
    me = await client.get_me()

    if not me.username:
        return None

    return me.username


async def make_start_link(client, token):
    """
    Create Telegram deep link.
    """
    username = await get_bot_username(client)

    if not username:
        return None

    return (
        f"https://t.me/{username}"
        f"?start={token}"
    )


# ============================================================
# DATABASE CHANNEL MESSAGE CHECK
# ============================================================

async def get_database_message(
    client,
    message_id
):
    """
    Retrieve one known message from the database channel.

    This uses get_messages() with a known message ID.
    It does NOT use get_chat_history().
    """

    try:
        message = await client.get_messages(
            DATABASE_CHANNEL_ID,
            message_id
        )

        if not message:
            return None

        if getattr(message, "empty", False):
            return None

        return message

    except Exception as e:
        logger.error(
            "Failed to get database message "
            "%s: %s",
            message_id,
            e
        )

        return None


# ============================================================
# MEDIA CHECK
# ============================================================

def has_supported_media(message):
    """
    Check whether the message contains supported media.
    """

    if not message:
        return False

    return any(
        [
            message.document,
            message.video,
            message.audio,
            message.animation,
            message.voice,
            message.photo,
        ]
    )


# ============================================================
# SEND ONE FILE
# ============================================================

async def send_permanent_file(
    client,
    user_id,
    message_id,
    protected=False
):
    """
    Copy one file from the database channel
    to the user's PM.
    """

    message = await get_database_message(
        client,
        message_id
    )

    if not message:
        return False

    if not has_supported_media(message):
        return False

    try:

        await client.copy_message(
            chat_id=user_id,
            from_chat_id=DATABASE_CHANNEL_ID,
            message_id=message.id,
            protect_content=protected
        )

        logger.info(
            "Permanent file sent | "
            "user=%s | message_id=%s | protected=%s",
            user_id,
            message_id,
            protected
        )

        return True

    except Exception as e:

        logger.error(
            "Permanent file delivery failed | "
            "user=%s | message_id=%s | error=%s",
            user_id,
            message_id,
            e
        )

        return False


# ============================================================
# SEND BATCH
# ============================================================

async def send_permanent_batch(
    client,
    user_id,
    first_id,
    last_id,
    protected=False
):
    """
    Send a range of database-channel messages.

    Only known message IDs are requested.
    No history enumeration is used.
    """

    if first_id > last_id:
        first_id, last_id = last_id, first_id

    total = (
        last_id
        - first_id
        + 1
    )

    if total > MAX_BATCH_FILES:
        return 0, True

    sent = 0

    for message_id in range(
        first_id,
        last_id + 1
    ):

        success = await send_permanent_file(
            client=client,
            user_id=user_id,
            message_id=message_id,
            protected=protected
        )

        if success:
            sent += 1

    return sent, False


# ============================================================
# HANDLE PERMANENT LINK
# ============================================================

async def handle_permanent_link(
    client,
    message,
    token,
    user_id=None
):
    """
    Main permanent-link handler.

    Supported tokens:

    pl_<message_id>

    ba_<first_id>_<last_id>

    pb_<first_id>_<last_id>
    """

    if not user_id:

        if not message.from_user:
            return

        user_id = message.from_user.id

    if not token:
        return

    token = token.strip()

    # ========================================================
    # FORCE SUB CHECK
    # ========================================================

    not_joined = await check_all_fsubs(
        client,
        user_id
    )

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=token
        )

        return

    # ========================================================
    # SINGLE PROTECTED LINK
    # ========================================================

    if token.startswith("pl_"):

        raw_id = token[3:]

        if not raw_id.isdigit():

            await client.send_message(
                user_id,
                "❌ <b>Invalid permanent link.</b>",
                parse_mode=enums.ParseMode.HTML
            )

            return

        message_id = int(raw_id)

        sent = await send_permanent_file(
            client=client,
            user_id=user_id,
            message_id=message_id,
            protected=True
        )

        if not sent:

            await client.send_message(
                user_id,
                "❌ <b>File not found or unavailable.</b>",
                parse_mode=enums.ParseMode.HTML
            )

        return

    # ========================================================
    # NORMAL BATCH
    # ========================================================

    if token.startswith("ba_"):

        parts = token[3:].split("_")

        if len(parts) != 2:
            await client.send_message(
                user_id,
                "❌ <b>Invalid batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        if not all(
            part.isdigit()
            for part in parts
        ):
            await client.send_message(
                user_id,
                "❌ <b>Invalid batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        first_id = int(parts[0])
        last_id = int(parts[1])

        sent, too_many = await send_permanent_batch(
            client=client,
            user_id=user_id,
            first_id=first_id,
            last_id=last_id,
            protected=False
        )

        if too_many:

            await client.send_message(
                user_id,
                (
                    "❌ <b>Batch too large.</b>\n\n"
                    f"Maximum allowed files: "
                    f"<b>{MAX_BATCH_FILES}</b>"
                ),
                parse_mode=enums.ParseMode.HTML
            )

            return

        if sent == 0:

            await client.send_message(
                user_id,
                "❌ <b>No files were found in this batch.</b>",
                parse_mode=enums.ParseMode.HTML
            )

        return

    # ========================================================
    # PROTECTED BATCH
    # ========================================================

    if token.startswith("pb_"):

        parts = token[3:].split("_")

        if len(parts) != 2:
            await client.send_message(
                user_id,
                "❌ <b>Invalid protected batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        if not all(
            part.isdigit()
            for part in parts
        ):
            await client.send_message(
                user_id,
                "❌ <b>Invalid protected batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        first_id = int(parts[0])
        last_id = int(parts[1])

        sent, too_many = await send_permanent_batch(
            client=client,
            user_id=user_id,
            first_id=first_id,
            last_id=last_id,
            protected=True
        )

        if too_many:

            await client.send_message(
                user_id,
                (
                    "❌ <b>Batch too large.</b>\n\n"
                    f"Maximum allowed files: "
                    f"<b>{MAX_BATCH_FILES}</b>"
                ),
                parse_mode=enums.ParseMode.HTML
            )

            return

        if sent == 0:

            await client.send_message(
                user_id,
                "❌ <b>No files were found in this batch.</b>",
                parse_mode=enums.ParseMode.HTML
            )

        return

    # ========================================================
    # UNKNOWN TOKEN
    # ========================================================

    await client.send_message(
        user_id,
        "❌ <b>Invalid or expired permanent link.</b>",
        parse_mode=enums.ParseMode.HTML
    )


# ============================================================
# /PLINK
# ============================================================

async def plink_handler(
    client,
    message
):
    """
    Generate permanent link for one media message.

    Usage:

    Reply to a database-channel media:

    /plink
    """

    if not message.reply_to_message:

        await message.reply_text(
            (
                "❌ <b>Reply to a media message "
                "with /plink</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    replied = message.reply_to_message

    # --------------------------------------------------------
    # Only allow database channel
    # --------------------------------------------------------

    if message.chat.id != DATABASE_CHANNEL_ID:

        await message.reply_text(
            (
                "❌ <b>/plink can only be used "
                "inside the database channel.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    if not has_supported_media(replied):

        await message.reply_text(
            (
                "❌ <b>Reply to a supported media file.</b>\n\n"
                "Supported: Video, Document, Audio, Photo."
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    token = make_single_token(
        replied.id
    )

    link = await make_start_link(
        client,
        token
    )

    if not link:

        await message.reply_text(
            "❌ <b>Bot username is not available.</b>",
            parse_mode=enums.ParseMode.HTML
        )

        return

    await message.reply_text(
        (
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            f"🔐 <b>Protected:</b> Yes\n\n"
            f"🔗 <b>Link:</b>\n{link}"
        ),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# ============================================================
# BATCH COMMAND PARSER
# ============================================================

async def generate_batch_link(
    client,
    message,
    protected=False
):
    """
    Generate /batch or /pbatch link.

    Supported:

    /batch 100 120

    /pbatch 100 120

    /batch https://t.me/c/1234567890/100 https://t.me/c/1234567890/120

    /pbatch https://t.me/c/1234567890/100 https://t.me/c/1234567890/120
    """

    command_parts = (
        message.text or ""
    ).split()

    if len(command_parts) != 3:

        command_name = (
            "pbatch"
            if protected
            else "batch"
        )

        await message.reply_text(
            (
                f"❌ <b>Invalid format.</b>\n\n"
                f"Usage:\n"
                f"<code>/{command_name} FIRST LAST</code>\n\n"
                f"Example:\n"
                f"<code>/{command_name} 100 120</code>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    first_ref = parse_message_reference(
        command_parts[1]
    )

    last_ref = parse_message_reference(
        command_parts[2]
    )

    if not first_ref or not last_ref:

        await message.reply_text(
            "❌ <b>Invalid message references.</b>",
            parse_mode=enums.ParseMode.HTML
        )

        return

    first_chat, first_id = first_ref
    last_chat, last_id = last_ref

    # --------------------------------------------------------
    # Ensure both references belong to database channel
    # --------------------------------------------------------

    if (
        str(first_chat)
        != str(DATABASE_CHANNEL_ID)
        or
        str(last_chat)
        != str(DATABASE_CHANNEL_ID)
    ):

        await message.reply_text(
            (
                "❌ <b>Both messages must belong "
                "to the database channel.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    if first_id > last_id:

        first_id, last_id = (
            last_id,
            first_id
        )

    total = (
        last_id
        - first_id
        + 1
    )

    if total > MAX_BATCH_FILES:

        await message.reply_text(
            (
                "❌ <b>Batch too large.</b>\n\n"
                f"Maximum allowed: "
                f"<b>{MAX_BATCH_FILES}</b> files.\n"
                f"Requested: <b>{total}</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # Verify at least first and last messages exist
    # --------------------------------------------------------

    first_message = await get_database_message(
        client,
        first_id
    )

    last_message = await get_database_message(
        client,
        last_id
    )

    if not first_message or not last_message:

        await message.reply_text(
            (
                "❌ <b>One or more messages "
                "could not be found.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    token = make_batch_token(
        first_id,
        last_id,
        protected=protected
    )

    link = await make_start_link(
        client,
        token
    )

    if not link:

        await message.reply_text(
            "❌ <b>Bot username is not available.</b>",
            parse_mode=enums.ParseMode.HTML
        )

        return

    link_type = (
        "Protected Batch"
        if protected
        else "Normal Batch"
    )

    await message.reply_text(
        (
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Bᴀᴛᴄʜ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            f"📦 <b>Type:</b> {link_type}\n"
            f"📁 <b>Files:</b> {total}\n"
            f"🔢 <b>Range:</b> {first_id} - {last_id}\n\n"
            f"🔗 <b>Link:</b>\n{link}"
        ),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# ============================================================
# /BATCH
# ============================================================

async def batch_handler(
    client,
    message
):
    await generate_batch_link(
        client=client,
        message=message,
        protected=False
    )


# ============================================================
# /PBATCH
# ============================================================

async def pbatch_handler(
    client,
    message
):
    await generate_batch_link(
        client=client,
        message=message,
        protected=True
    )


# ============================================================
# REGISTER HANDLERS
# ============================================================

def register_permanent_link_handlers(app):

    # --------------------------------------------------------
    # /plink
    # --------------------------------------------------------

    app.on_message(
        filters.command("plink")
        & filters.private
    )(plink_handler)

    # --------------------------------------------------------
    # /batch
    # --------------------------------------------------------

    app.on_message(
        filters.command("batch")
        & filters.private
    )(batch_handler)

    # --------------------------------------------------------
    # /pbatch
    # --------------------------------------------------------

    app.on_message(
        filters.command("pbatch")
        & filters.private
    )(pbatch_handler)

    logger.info(
        "Permanent link handlers registered"
    )
