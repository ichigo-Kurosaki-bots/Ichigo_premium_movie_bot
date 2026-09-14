# ============================================================
# handlers/permanent_links.py
# ============================================================

import logging
import re

from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup

from config import DATABASE_CHANNEL_ID
from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message
)


logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

MAX_BATCH_FILES = 50


# ============================================================
# MESSAGE / LINK HELPERS
# ============================================================

def get_message_id_from_link(text):
    """
    Supports:

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

    https://t.me/channelname/12345
    """

    if not value:
        return None

    value = value.strip()

    if value.isdigit():
        return DATABASE_CHANNEL_ID, int(value)

    return get_message_id_from_link(value)


def make_single_token(message_id):
    """
    Protected single-file permanent link.
    """
    return f"pl_{message_id}"


def make_batch_token(
    first_id,
    last_id,
    protected=False
):
    """
    Normal:
        ba_FIRST_LAST

    Protected:
        pb_FIRST_LAST
    """

    prefix = "pb_" if protected else "ba_"

    return (
        f"{prefix}"
        f"{first_id}_"
        f"{last_id}"
    )


async def make_start_link(
    client,
    token
):
    """
    Create Telegram bot deep link.
    """

    try:

        me = await client.get_me()

        if not me.username:
            return None

        return (
            f"https://t.me/"
            f"{me.username}"
            f"?start={token}"
        )

    except Exception as e:

        logger.error(
            "Failed to create start link: %s",
            e
        )

        return None


# ============================================================
# FORWARDED MESSAGE ORIGINAL SOURCE
# ============================================================

def get_original_message_reference(
    message
):
    """
    Get the original channel/message ID from
    a forwarded Telegram message.

    Supports modern Pyrogram forward_origin
    and older forward fields.
    """

    original_chat_id = None
    original_message_id = None

    # --------------------------------------------------------
    # Modern Pyrogram
    # --------------------------------------------------------

    try:

        forward_origin = getattr(
            message,
            "forward_origin",
            None
        )

        if forward_origin:

            original_message_id = getattr(
                forward_origin,
                "message_id",
                None
            )

            origin_chat = getattr(
                forward_origin,
                "chat",
                None
            )

            if origin_chat:

                original_chat_id = getattr(
                    origin_chat,
                    "id",
                    None
                )

    except Exception as e:

        logger.warning(
            "forward_origin read failed: %s",
            e
        )

    # --------------------------------------------------------
    # Older Pyrogram fields
    # --------------------------------------------------------

    if not original_message_id:

        original_message_id = getattr(
            message,
            "forward_from_message_id",
            None
        )

    if not original_chat_id:

        forward_chat = getattr(
            message,
            "forward_from_chat",
            None
        )

        if forward_chat:

            original_chat_id = getattr(
                forward_chat,
                "id",
                None
            )

    if not original_message_id:

        return None

    return (
        original_chat_id,
        int(original_message_id)
    )


# ============================================================
# DATABASE MESSAGE
# ============================================================

async def get_database_message(
    client,
    message_id
):
    """
    Retrieve a known message from the database channel.

    IMPORTANT:
    This does NOT use get_chat_history().
    """

    try:

        message = await client.get_messages(
            DATABASE_CHANNEL_ID,
            int(message_id)
        )

        if not message:
            return None

        if getattr(
            message,
            "empty",
            False
        ):
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

    if not message:
        return False

    return any(
        [
            message.document,
            message.video,
            message.audio,
            message.animation,
            message.voice,
            message.photo
        ]
    )


# ============================================================
# SEND ONE PERMANENT FILE
# ============================================================

async def send_permanent_file(
    client,
    user_id,
    message_id,
    protected=False
):
    """
    Copy one original database-channel message
    to the user's private chat.
    """

    database_message = (
        await get_database_message(
            client,
            message_id
        )
    )

    if not database_message:
        return False

    if not has_supported_media(
        database_message
    ):
        return False

    try:

        await client.copy_message(
            chat_id=user_id,
            from_chat_id=DATABASE_CHANNEL_ID,
            message_id=database_message.id,
            protect_content=protected
        )

        logger.info(
            "PERMANENT FILE SENT | "
            "user=%s | message_id=%s | protected=%s",
            user_id,
            message_id,
            protected
        )

        return True

    except Exception as e:

        logger.error(
            "PERMANENT FILE SEND ERROR | "
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
    Send database messages between first_id and last_id.
    """

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

        return 0, True

    sent = 0

    for message_id in range(
        first_id,
        last_id + 1
    ):

        success = (
            await send_permanent_file(
                client=client,
                user_id=user_id,
                message_id=message_id,
                protected=protected
            )
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
    Handles:

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

        success = (
            await send_permanent_file(
                client=client,
                user_id=user_id,
                message_id=message_id,
                protected=True
            )
        )

        if not success:

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

        if (
            len(parts) != 2
            or not all(
                part.isdigit()
                for part in parts
            )
        ):

            await client.send_message(
                user_id,
                "❌ <b>Invalid batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )

            return

        first_id = int(parts[0])
        last_id = int(parts[1])

        sent, too_many = (
            await send_permanent_batch(
                client=client,
                user_id=user_id,
                first_id=first_id,
                last_id=last_id,
                protected=False
            )
        )

        if too_many:

            await client.send_message(
                user_id,
                (
                    "❌ <b>Batch too large.</b>\n\n"
                    f"Maximum allowed: "
                    f"<b>{MAX_BATCH_FILES}</b> files."
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

        if (
            len(parts) != 2
            or not all(
                part.isdigit()
                for part in parts
            )
        ):

            await client.send_message(
                user_id,
                "❌ <b>Invalid protected batch link.</b>",
                parse_mode=enums.ParseMode.HTML
            )

            return

        first_id = int(parts[0])
        last_id = int(parts[1])

        sent, too_many = (
            await send_permanent_batch(
                client=client,
                user_id=user_id,
                first_id=first_id,
                last_id=last_id,
                protected=True
            )
        )

        if too_many:

            await client.send_message(
                user_id,
                (
                    "❌ <b>Batch too large.</b>\n\n"
                    f"Maximum allowed: "
                    f"<b>{MAX_BATCH_FILES}</b> files."
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
    /plink

    Works in Bot PM by replying to a forwarded
    Database-channel media message.

    Also works directly inside the Database channel.
    """

    if not message.reply_to_message:

        await message.reply_text(
            (
                "❌ <b>Reply to a media message "
                "with /plink.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    replied = message.reply_to_message

    original_chat_id = None
    original_message_id = None

    # ========================================================
    # DIRECT DATABASE CHANNEL
    # ========================================================

    if str(message.chat.id) == str(
        DATABASE_CHANNEL_ID
    ):

        original_chat_id = DATABASE_CHANNEL_ID
        original_message_id = replied.id

    # ========================================================
    # FORWARDED DATABASE MESSAGE IN BOT PM
    # ========================================================

    else:

        reference = (
            get_original_message_reference(
                replied
            )
        )

        if reference:

            (
                original_chat_id,
                original_message_id
            ) = reference

    # ========================================================
    # CHECK ORIGINAL MESSAGE
    # ========================================================

    if not original_message_id:

        await message.reply_text(
            (
                "❌ <b>Could not find the original "
                "Database message.</b>\n\n"
                "Forward a file from the Database channel "
                "and reply to it with <code>/plink</code>."
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # DATABASE CHANNEL CHECK
    # ========================================================

    if str(original_chat_id) != str(
        DATABASE_CHANNEL_ID
    ):

        await message.reply_text(
            (
                "❌ <b>This file is not from "
                "the Database channel.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # GET ORIGINAL MESSAGE
    # ========================================================

    database_message = (
        await get_database_message(
            client,
            original_message_id
        )
    )

    if not database_message:

        await message.reply_text(
            (
                "❌ <b>Original Database message "
                "was not found.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # MEDIA CHECK
    # ========================================================

    if not has_supported_media(
        database_message
    ):

        await message.reply_text(
            (
                "❌ <b>Reply to a supported media file.</b>\n\n"
                "Supported: Video, Document, Audio, Photo."
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # CREATE LINK
    # ========================================================

    token = make_single_token(
        original_message_id
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

    # ========================================================
    # SEND LINK
    # ========================================================

    await message.reply_text(
        (
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            "🔐 <b>Protected:</b> Yes\n"
            f"🆔 <b>File ID:</b> "
            f"{original_message_id}\n\n"
            f"🔗 <b>Link:</b>\n{link}"
        ),
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )


# ============================================================
# GET BATCH REFERENCE
# ============================================================

def get_batch_reply_reference(
    replied
):
    """
    Get the original Database message ID
    from a forwarded message.
    """

    if not replied:
        return None

    reference = (
        get_original_message_reference(
            replied
        )
    )

    if not reference:
        return None

    original_chat_id, original_message_id = (
        reference
    )

    if str(original_chat_id) != str(
        DATABASE_CHANNEL_ID
    ):
        return None

    return int(original_message_id)


# ============================================================
# GENERATE BATCH LINK
# ============================================================

async def generate_batch_link(
    client,
    message,
    protected=False
):
    """
    Supports Bot PM:

    /batch 100 120

    /pbatch 100 120

    /batch https://t.me/c/1234567890/100 https://t.me/c/1234567890/120

    /pbatch https://t.me/c/1234567890/100 https://t.me/c/1234567890/120

    OR:

    Reply to forwarded Database file with:

    /batch 120

    /pbatch 120

    The replied file becomes FIRST ID.
    The command argument becomes LAST ID.
    """

    text = (
        message.text
        or message.caption
        or ""
    )

    command_parts = text.split()

    # ========================================================
    # COMMAND NAME
    # ========================================================

    command_name = (
        "pbatch"
        if protected
        else "batch"
    )

    # ========================================================
    # REPLY TO FORWARDED FILE METHOD
    # ========================================================

    replied = message.reply_to_message

    if replied:

        first_id = (
            get_batch_reply_reference(
                replied
            )
        )

        # ----------------------------------------------------
        # If replied message is from DB
        # ----------------------------------------------------

        if first_id:

            # /batch <last>
            if len(command_parts) == 2:

                last_ref = (
                    parse_message_reference(
                        command_parts[1]
                    )
                )

                if not last_ref:

                    await message.reply_text(
                        (
                            "❌ <b>Invalid last message.</b>"
                        ),
                        parse_mode=enums.ParseMode.HTML
                    )

                    return

                last_chat, last_id = last_ref

                if str(last_chat) != str(
                    DATABASE_CHANNEL_ID
                ):

                    await message.reply_text(
                        (
                            "❌ <b>The last message "
                            "must be from the Database channel.</b>"
                        ),
                        parse_mode=enums.ParseMode.HTML
                    )

                    return

            else:

                await message.reply_text(
                    (
                        f"❌ <b>Reply to the first Database "
                        f"file and use:</b>\n\n"
                        f"<code>/{command_name} LAST_ID</code>\n\n"
                        f"<b>Example:</b>\n"
                        f"<code>/{command_name} 120</code>"
                    ),
                    parse_mode=enums.ParseMode.HTML
                )

                return

        else:

            first_id = None

    else:

        first_id = None

    # ========================================================
    # NORMAL TWO-REFERENCE METHOD
    # ========================================================

    if first_id is None:

        if len(command_parts) != 3:

            await message.reply_text(
                (
                    "❌ <b>Invalid format.</b>\n\n"
                    f"Use:\n"
                    f"<code>/{command_name} FIRST LAST</code>\n\n"
                    "Example:\n"
                    f"<code>/{command_name} 100 120</code>\n\n"
                    "Or use Telegram links:\n"
                    f"<code>/{command_name} "
                    "https://t.me/c/1234567890/100 "
                    "https://t.me/c/1234567890/120</code>"
                ),
                parse_mode=enums.ParseMode.HTML
            )

            return

        first_ref = (
            parse_message_reference(
                command_parts[1]
            )
        )

        last_ref = (
            parse_message_reference(
                command_parts[2]
            )
        )

        if not first_ref or not last_ref:

            await message.reply_text(
                "❌ <b>Invalid message references.</b>",
                parse_mode=enums.ParseMode.HTML
            )

            return

        first_chat, first_id = first_ref
        last_chat, last_id = last_ref

        # ----------------------------------------------------
        # Both must be database channel
        # ----------------------------------------------------

        if str(first_chat) != str(
            DATABASE_CHANNEL_ID
        ):

            await message.reply_text(
                (
                    "❌ <b>First message is not "
                    "from the Database channel.</b>"
                ),
                parse_mode=enums.ParseMode.HTML
            )

            return

        if str(last_chat) != str(
            DATABASE_CHANNEL_ID
        ):

            await message.reply_text(
                (
                    "❌ <b>Last message is not "
                    "from the Database channel.</b>"
                ),
                parse_mode=enums.ParseMode.HTML
            )

            return

    # ========================================================
    # VERIFY IDS
    # ========================================================

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

    # ========================================================
    # VERIFY FIRST MESSAGE
    # ========================================================

    first_message = (
        await get_database_message(
            client,
            first_id
        )
    )

    if not first_message:

        await message.reply_text(
            (
                "❌ <b>First Database message "
                "was not found.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # VERIFY LAST MESSAGE
    # ========================================================

    last_message = (
        await get_database_message(
            client,
            last_id
        )
    )

    if not last_message:

        await message.reply_text(
            (
                "❌ <b>Last Database message "
                "was not found.</b>"
            ),
            parse_mode=enums.ParseMode.HTML
        )

        return

    # ========================================================
    # CREATE TOKEN
    # ========================================================

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

    # ========================================================
    # SEND RESULT
    # ========================================================

    batch_type = (
        "Protected Batch"
        if protected
        else "Normal Batch"
    )

    await message.reply_text(
        (
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Bᴀᴛᴄʜ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            f"📦 <b>Type:</b> {batch_type}\n"
            f"📁 <b>Files:</b> {total}\n"
            f"🔢 <b>Range:</b> "
            f"{first_id} - {last_id}\n\n"
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
