# ============================================================
# permanent_links.py
# Permanent Media / Batch Link System
# ============================================================

import logging
import secrets
import string

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ChatType

from config import (
    OWNER_ID,
    ADMIN_IDS,
    DATABASE_CHANNEL_ID,
)

from database import db

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

LINK_PREFIX = "pl_"
BATCH_PREFIX = "pb_"

MAX_BATCH_FILES = 50


# ============================================================
# MONGO COLLECTION
# ============================================================

permanent_links_collection = db["permanent_links"]


# ============================================================
# ADMIN CHECK
# ============================================================

def is_link_admin(user_id):

    if user_id == OWNER_ID:
        return True

    if user_id in ADMIN_IDS:
        return True

    return False


# ============================================================
# GENERATE RANDOM TOKEN
# ============================================================

def generate_token(length=16):

    chars = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(chars)
        for _ in range(length)
    )


# ============================================================
# GET BOT USERNAME
# ============================================================

async def get_bot_username(client):

    me = await client.get_me()

    if not me.username:
        raise RuntimeError(
            "Bot username is required for permanent links."
        )

    return me.username


# ============================================================
# CREATE SINGLE LINK
# ============================================================

async def create_single_link(
    message_id,
    created_by
):

    token = generate_token()

    while await permanent_links_collection.find_one(
        {"token": token}
    ):
        token = generate_token()

    document = {
        "token": token,
        "type": "single",
        "message_ids": [int(message_id)],
        "protected": False,
        "created_by": int(created_by),
    }

    await permanent_links_collection.insert_one(
        document
    )

    return token


# ============================================================
# CREATE BATCH LINK
# ============================================================

async def create_batch_link(
    message_ids,
    created_by,
    protected=False
):

    message_ids = [
        int(x)
        for x in message_ids
    ]

    # Remove duplicates while preserving order
    message_ids = list(
        dict.fromkeys(message_ids)
    )

    if not message_ids:
        return None

    if len(message_ids) > MAX_BATCH_FILES:
        raise ValueError(
            f"Maximum {MAX_BATCH_FILES} files are allowed."
        )

    token = generate_token()

    while await permanent_links_collection.find_one(
        {"token": token}
    ):
        token = generate_token()

    document = {
        "token": token,
        "type": "batch",
        "message_ids": message_ids,
        "protected": bool(protected),
        "created_by": int(created_by),
    }

    await permanent_links_collection.insert_one(
        document
    )

    return token


# ============================================================
# BUILD LINK
# ============================================================

async def build_link(
    client,
    token
):

    username = await get_bot_username(
        client
    )

    return (
        f"https://t.me/{username}"
        f"?start={token}"
    )


# ============================================================
# /PLINK
#
# Usage:
# Reply to a media message in DATABASE CHANNEL:
#
# /plink
# ============================================================

@app.on_message(
    filters.command("plink")
)
async def permanent_link_handler(
    client,
    message
):

    user = message.from_user

    if not user:
        return

    if not is_link_admin(user.id):
        return

    # --------------------------------------------------------
    # Must be used in database channel
    # --------------------------------------------------------

    if message.chat.id != DATABASE_CHANNEL_ID:

        await message.reply_text(
            "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
            "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
        )

        return

    # --------------------------------------------------------
    # Must reply to a media message
    # --------------------------------------------------------

    if not message.reply_to_message:

        await message.reply_text(
            "❌ <b>Rᴇᴘʟʏ Tᴏ A Mᴇᴅɪᴀ Mᴇssᴀɢᴇ Wɪᴛʜ:</b>\n\n"
            "<code>/plink</code>"
        )

        return

    replied = message.reply_to_message

    # --------------------------------------------------------
    # Check supported media
    # --------------------------------------------------------

    if not (
        replied.document
        or replied.video
        or replied.audio
        or replied.photo
        or replied.animation
        or replied.voice
    ):

        await message.reply_text(
            "❌ <b>Tʜᴇ Rᴇᴘʟɪᴇᴅ Mᴇssᴀɢᴇ Dᴏᴇs Nᴏᴛ Cᴏɴᴛᴀɪɴ Mᴇᴅɪᴀ.</b>"
        )

        return

    try:

        token = await create_single_link(
            replied.id,
            user.id
        )

        link = await build_link(
            client,
            token
        )

        await message.reply_text(
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            f"📁 <b>Fɪʟᴇ ID:</b> <code>{replied.id}</code>\n\n"
            f"🔗 <b>Lɪɴᴋ:</b>\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Oᴘᴇɴ Lɪɴᴋ •",
                            url=link
                        )
                    ]
                ]
            )
        )

    except Exception as e:

        logger.exception(
            "Permanent link error: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Gᴇɴᴇʀᴀᴛᴇ Lɪɴᴋ.</b>\n\n"
            f"<code>{str(e)}</code>"
        )


# ============================================================
# PARSE BATCH IDS
#
# Supported:
#
# /batch 100 101 102
#
# /batch 100-110
#
# /pbatch 100 101 102
#
# /pbatch 100-110
# ============================================================

def parse_message_ids(arguments):

    message_ids = []

    for argument in arguments:

        argument = argument.strip()

        if not argument:
            continue

        # ----------------------------------------------------
        # Range
        # ----------------------------------------------------

        if "-" in argument:

            parts = argument.split("-", 1)

            if len(parts) != 2:
                continue

            try:

                start = int(parts[0])
                end = int(parts[1])

            except ValueError:
                continue

            if start > end:
                start, end = end, start

            for message_id in range(
                start,
                end + 1
            ):

                message_ids.append(
                    message_id
                )

        else:

            try:

                message_ids.append(
                    int(argument)
                )

            except ValueError:
                continue

    return list(
        dict.fromkeys(message_ids)
    )


# ============================================================
# /BATCH
#
# Example:
#
# /batch 153700 153701 153702
#
# OR:
#
# /batch 153700-153702
# ============================================================

@app.on_message(
    filters.command("batch")
)
async def batch_link_handler(
    client,
    message
):

    user = message.from_user

    if not user:
        return

    if not is_link_admin(user.id):
        return

    # --------------------------------------------------------
    # Only database channel
    # --------------------------------------------------------

    if message.chat.id != DATABASE_CHANNEL_ID:

        await message.reply_text(
            "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
            "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
        )

        return

    # --------------------------------------------------------
    # Parse IDs
    # --------------------------------------------------------

    arguments = message.command[1:]

    message_ids = parse_message_ids(
        arguments
    )

    if not message_ids:

        await message.reply_text(
            "❌ <b>Pʟᴇᴀsᴇ Pʀᴏᴠɪᴅᴇ Mᴇssᴀɢᴇ IDs.</b>\n\n"
            "<b>Eхᴀᴍᴘʟᴇ:</b>\n"
            "<code>/batch 153700 153701 153702</code>\n\n"
            "<b>Oʀ Rᴀɴɢᴇ:</b>\n"
            "<code>/batch 153700-153710</code>"
        )

        return

    if len(message_ids) > MAX_BATCH_FILES:

        await message.reply_text(
            f"❌ <b>Mᴀxɪᴍᴜᴍ {MAX_BATCH_FILES} Fɪʟᴇs Pᴇʀ Bᴀᴛᴄʜ.</b>"
        )

        return

    # --------------------------------------------------------
    # Verify messages exist
    # --------------------------------------------------------

    valid_ids = []

    for message_id in message_ids:

        try:

            media_message = await client.get_messages(
                DATABASE_CHANNEL_ID,
                message_id
            )

            if not media_message:
                continue

            if not (
                media_message.document
                or media_message.video
                or media_message.audio
                or media_message.photo
                or media_message.animation
                or media_message.voice
            ):
                continue

            valid_ids.append(
                message_id
            )

        except Exception as e:

            logger.warning(
                "Batch message check failed %s: %s",
                message_id,
                e
            )

    if not valid_ids:

        await message.reply_text(
            "❌ <b>Nᴏ Vᴀʟɪᴅ Mᴇᴅɪᴀ Fᴏᴜɴᴅ.</b>"
        )

        return

    # --------------------------------------------------------
    # Create link
    # --------------------------------------------------------

    try:

        token = await create_batch_link(
            valid_ids,
            user.id,
            protected=False
        )

        link = await build_link(
            client,
            token
        )

        await message.reply_text(
            "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Bᴀᴛᴄʜ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"
            f"📁 <b>Fɪʟᴇs:</b> <code>{len(valid_ids)}</code>\n"
            f"🆔 <b>IDs:</b> <code>{', '.join(map(str, valid_ids))}</code>\n\n"
            f"🔗 <b>Lɪɴᴋ:</b>\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Oᴘᴇɴ Bᴀᴛᴄʜ Lɪɴᴋ •",
                            url=link
                        )
                    ]
                ]
            )
        )

    except Exception as e:

        logger.exception(
            "Batch link error: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Cʀᴇᴀᴛᴇ Bᴀᴛᴄʜ Lɪɴᴋ.</b>\n\n"
            f"<code>{str(e)}</code>"
        )


# ============================================================
# /PBATCH
#
# Protected permanent batch link
#
# Example:
#
# /pbatch 153700-153710
# ============================================================

@app.on_message(
    filters.command("pbatch")
)
async def protected_batch_link_handler(
    client,
    message
):

    user = message.from_user

    if not user:
        return

    if not is_link_admin(user.id):
        return

    if message.chat.id != DATABASE_CHANNEL_ID:

        await message.reply_text(
            "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
            "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
        )

        return

    arguments = message.command[1:]

    message_ids = parse_message_ids(
        arguments
    )

    if not message_ids:

        await message.reply_text(
            "❌ <b>Pʟᴇᴀsᴇ Pʀᴏᴠɪᴅᴇ Mᴇssᴀɢᴇ IDs.</b>\n\n"
            "<b>Eхᴀᴍᴘʟᴇ:</b>\n"
            "<code>/pbatch 153700 153701 153702</code>\n\n"
            "<b>Oʀ Rᴀɴɢᴇ:</b>\n"
            "<code>/pbatch 153700-153710</code>"
        )

        return

    if len(message_ids) > MAX_BATCH_FILES:

        await message.reply_text(
            f"❌ <b>Mᴀxɪᴍᴜᴍ {MAX_BATCH_FILES} Fɪʟᴇs Pᴇʀ Bᴀᴛᴄʜ.</b>"
        )

        return

    # --------------------------------------------------------
    # Verify media
    # --------------------------------------------------------

    valid_ids = []

    for message_id in message_ids:

        try:

            media_message = await client.get_messages(
                DATABASE_CHANNEL_ID,
                message_id
            )

            if not media_message:
                continue

            if not (
                media_message.document
                or media_message.video
                or media_message.audio
                or media_message.photo
                or media_message.animation
                or media_message.voice
            ):
                continue

            valid_ids.append(
                message_id
            )

        except Exception as e:

            logger.warning(
                "Protected batch check failed %s: %s",
                message_id,
                e
            )

    if not valid_ids:

        await message.reply_text(
            "❌ <b>Nᴏ Vᴀʟɪᴅ Mᴇᴅɪᴀ Fᴏᴜɴᴅ.</b>"
        )

        return

    try:

        token = await create_batch_link(
            valid_ids,
            user.id,
            protected=True
        )

        link = await build_link(
            client,
            token
        )

        await message.reply_text(
            "🔐 <b>Pᴇʀᴍᴀɴᴇɴᴛ Pʀᴏᴛᴇᴄᴛᴇᴅ Bᴀᴛᴄʜ Lɪɴᴋ</b>\n\n"
            f"📁 <b>Fɪʟᴇs:</b> <code>{len(valid_ids)}</code>\n"
            "🛡 <b>Fᴏʀᴡᴀʀᴅ Pʀᴏᴛᴇᴄᴛɪᴏɴ:</b> Eɴᴀʙʟᴇᴅ\n\n"
            f"🔗 <b>Lɪɴᴋ:</b>\n{link}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Oᴘᴇɴ Pʀᴏᴛᴇᴄᴛᴇᴅ Lɪɴᴋ •",
                            url=link
                        )
                    ]
                ]
            )
        )

    except Exception as e:

        logger.exception(
            "Protected batch link error: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Cʀᴇᴀᴛᴇ Pʀᴏᴛᴇᴄᴛᴇᴅ Lɪɴᴋ.</b>\n\n"
            f"<code>{str(e)}</code>"
        )


# ============================================================
# PERMANENT LINK DELIVERY
#
# This function should be called from your existing /start
# payload handler.
# ============================================================

async def handle_permanent_link(
    client,
    message,
    token,
    user_id=None
):

    if user_id is None:

        if not message.from_user:
            return

        user_id = message.from_user.id

    # --------------------------------------------------------
    # Get link
    # --------------------------------------------------------

    link_data = await permanent_links_collection.find_one(
        {
            "token": token
        }
    )

    if not link_data:

        await client.send_message(
            user_id,
            "❌ <b>Tʜɪs Lɪɴᴋ Iѕ Iɴᴠᴀʟɪᴅ Oʀ Nᴏ Lᴏɴɢᴇʀ Eхɪѕᴛs.</b>"
        )

        return

    message_ids = link_data.get(
        "message_ids",
        []
    )

    protected = bool(
        link_data.get(
            "protected",
            False
        )
    )

    if not message_ids:

        await client.send_message(
            user_id,
            "❌ <b>Nᴏ Fɪʟᴇs Aʀᴇ Aᴠᴀɪʟᴀʙʟᴇ Fᴏʀ Tʜɪs Lɪɴᴋ.</b>"
        )

        return

    # --------------------------------------------------------
    # FORCE SUBSCRIBE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SEND FILES
    # --------------------------------------------------------

    sent = 0

    try:

        for message_id in message_ids:

            try:

                await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=DATABASE_CHANNEL_ID,
                    message_id=message_id,
                    protect_content=protected
                )

                sent += 1

            except Exception as e:

                logger.warning(
                    "Permanent link file failed %s: %s",
                    message_id,
                    e
                )

        if sent == 0:

            await client.send_message(
                user_id,
                "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Sᴇɴᴅ Tʜᴇ Fɪʟᴇ.</b>"
            )

            return

        logger.info(
            "PERMANENT LINK SENT | user=%s | token=%s | files=%s",
            user_id,
            token,
            sent
        )

    except Exception as e:

        logger.exception(
            "Permanent link delivery error: %s",
            e
        )

        await client.send_message(
            user_id,
            "❌ <b>Aɴ Eʀʀᴏʀ Oᴄᴄᴜʀʀᴇᴅ Wʜɪʟᴇ Sᴇɴᴅɪɴɢ Tʜᴇ Fɪʟᴇ.</b>"
      )
