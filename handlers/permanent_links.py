# ============================================================
# permanent_links.py
# /plink  /batch  /pbatch
# ============================================================

import logging
import secrets
import string

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import (
    OWNER_ID,
    ADMIN_IDS,
    DATABASE_CHANNEL_ID
)

from database import db

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
# MONGODB
# ============================================================

permanent_links_collection = db[
    "permanent_links"
]


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
# TOKEN
# ============================================================

def generate_token(length=16):

    characters = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


# ============================================================
# CREATE SINGLE LINK
# ============================================================

async def create_single_link(
    message_id,
    created_by
):

    token = "pl_" + generate_token()

    while await permanent_links_collection.find_one(
        {
            "token": token
        }
    ):

        token = "pl_" + generate_token()

    await permanent_links_collection.insert_one(
        {
            "token": token,
            "type": "single",
            "message_ids": [
                int(message_id)
            ],
            "protected": False,
            "created_by": int(created_by)
        }
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
        int(message_id)
        for message_id in message_ids
    ]

    message_ids = list(
        dict.fromkeys(message_ids)
    )

    if not message_ids:
        return None

    if len(message_ids) > MAX_BATCH_FILES:

        raise ValueError(
            f"Maximum {MAX_BATCH_FILES} files are allowed."
        )

    prefix = "pb_" if protected else "ba_"

    token = (
        prefix
        + generate_token()
    )

    while await permanent_links_collection.find_one(
        {
            "token": token
        }
    ):

        token = (
            prefix
            + generate_token()
        )

    await permanent_links_collection.insert_one(
        {
            "token": token,
            "type": "batch",
            "message_ids": message_ids,
            "protected": bool(protected),
            "created_by": int(created_by)
        }
    )

    return token


# ============================================================
# BOT LINK
# ============================================================

async def build_link(
    client,
    token
):

    me = await client.get_me()

    if not me.username:

        raise RuntimeError(
            "Bot username is not available."
        )

    return (
        f"https://t.me/{me.username}"
        f"?start={token}"
    )


# ============================================================
# CHECK MEDIA MESSAGE
# ============================================================

def is_media_message(message):

    if not message:
        return False

    return bool(
        message.document
        or message.video
        or message.audio
        or message.photo
        or message.animation
        or message.voice
    )


# ============================================================
# /PLINK
#
# Reply to a database-channel media message:
#
# /plink
# ============================================================

def register_permanent_link_handlers(
    app
):

    # ========================================================
    # /PLINK
    # ========================================================

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

        if not is_link_admin(
            user.id
        ):

            return

        # ----------------------------------------------------
        # DATABASE CHANNEL ONLY
        # ----------------------------------------------------

        if message.chat.id != DATABASE_CHANNEL_ID:

            await message.reply_text(
                "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
                "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
            )

            return

        # ----------------------------------------------------
        # REPLY REQUIRED
        # ----------------------------------------------------

        if not message.reply_to_message:

            await message.reply_text(
                "❌ <b>Rᴇᴘʟʏ Tᴏ A Mᴇᴅɪᴀ Mᴇssᴀɢᴇ Wɪᴛʜ:</b>\n\n"
                "<code>/plink</code>"
            )

            return

        replied = (
            message.reply_to_message
        )

        # ----------------------------------------------------
        # MEDIA CHECK
        # ----------------------------------------------------

        if not is_media_message(
            replied
        ):

            await message.reply_text(
                "❌ <b>Tʜᴇ Rᴇᴘʟɪᴇᴅ Mᴇssᴀɢᴇ Dᴏᴇs Nᴏᴛ Cᴏɴᴛᴀɪɴ Mᴇᴅɪᴀ.</b>"
            )

            return

        try:

            token = await create_single_link(
                message_id=replied.id,
                created_by=user.id
            )

            link = await build_link(
                client,
                token
            )

            await message.reply_text(

                "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ Gᴇɴᴇʀᴀᴛᴇᴅ</b>\n\n"

                f"📁 <b>Fɪʟᴇ ID:</b> "
                f"<code>{replied.id}</code>\n\n"

                f"🔗 <b>Lɪɴᴋ:</b>\n"
                f"{link}",

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
                "PLINK ERROR: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Gᴇɴᴇʀᴀᴛᴇ Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ.</b>\n\n"
                f"<code>{e}</code>"
            )


    # ========================================================
    # PARSE IDS
    # ========================================================

    def parse_message_ids(
        arguments
    ):

        message_ids = []

        for argument in arguments:

            argument = argument.strip()

            if not argument:
                continue

            # ------------------------------------------------
            # RANGE
            # ------------------------------------------------

            if "-" in argument:

                parts = argument.split(
                    "-",
                    1
                )

                if len(parts) != 2:
                    continue

                try:

                    start = int(
                        parts[0]
                    )

                    end = int(
                        parts[1]
                    )

                except ValueError:

                    continue

                if start > end:

                    start, end = (
                        end,
                        start
                    )

                for message_id in range(
                    start,
                    end + 1
                ):

                    message_ids.append(
                        message_id
                    )

            # ------------------------------------------------
            # SINGLE ID
            # ------------------------------------------------

            else:

                try:

                    message_ids.append(
                        int(argument)
                    )

                except ValueError:

                    continue

        return list(
            dict.fromkeys(
                message_ids
            )
        )


    # ========================================================
    # GET VALID MEDIA IDS
    # ========================================================

    async def get_valid_media_ids(
        client,
        message_ids
    ):

        valid_ids = []

        for message_id in message_ids:

            try:

                media_message = (
                    await client.get_messages(
                        DATABASE_CHANNEL_ID,
                        message_id
                    )
                )

                if not media_message:
                    continue

                if not is_media_message(
                    media_message
                ):
                    continue

                valid_ids.append(
                    message_id
                )

            except Exception as e:

                logger.warning(
                    "MEDIA CHECK FAILED | id=%s | error=%s",
                    message_id,
                    e
                )

        return valid_ids


    # ========================================================
    # /BATCH
    #
    # /batch 153700 153701 153702
    #
    # /batch 153700-153710
    # ========================================================

    @app.on_message(
        filters.command("batch")
    )
    async def batch_handler(
        client,
        message
    ):

        user = message.from_user

        if not user:
            return

        if not is_link_admin(
            user.id
        ):

            return

        if message.chat.id != DATABASE_CHANNEL_ID:

            await message.reply_text(
                "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
                "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
            )

            return

        arguments = (
            message.command[1:]
        )

        message_ids = parse_message_ids(
            arguments
        )

        if not message_ids:

            await message.reply_text(
                "❌ <b>Pʟᴇᴀsᴇ Pʀᴏᴠɪᴅᴇ Mᴇssᴀɢᴇ IDs.</b>\n\n"

                "<b>Eхᴀᴍᴘʟᴇ:</b>\n"
                "<code>/batch 153700 153701 153702</code>\n\n"

                "<b>Rᴀɴɢᴇ:</b>\n"
                "<code>/batch 153700-153710</code>"
            )

            return

        if len(message_ids) > MAX_BATCH_FILES:

            await message.reply_text(
                f"❌ <b>Mᴀxɪᴍᴜᴍ "
                f"{MAX_BATCH_FILES} Fɪʟᴇs Pᴇʀ Bᴀᴛᴄʜ.</b>"
            )

            return

        status = await message.reply_text(
            "🔎 <b>Cʜᴇᴄᴋɪɴɢ Fɪʟᴇs...</b>"
        )

        try:

            valid_ids = (
                await get_valid_media_ids(
                    client,
                    message_ids
                )
            )

            if not valid_ids:

                await status.edit_text(
                    "❌ <b>Nᴏ Vᴀʟɪᴅ Mᴇᴅɪᴀ Fᴏᴜɴᴅ.</b>"
                )

                return

            token = await create_batch_link(
                message_ids=valid_ids,
                created_by=user.id,
                protected=False
            )

            link = await build_link(
                client,
                token
            )

            await status.edit_text(

                "🔗 <b>Pᴇʀᴍᴀɴᴇɴᴛ Bᴀᴛᴄʜ Lɪɴᴋ</b>\n\n"

                f"📁 <b>Fɪʟᴇs:</b> "
                f"<code>{len(valid_ids)}</code>\n\n"

                f"🔗 <b>Lɪɴᴋ:</b>\n"
                f"{link}",

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
                "BATCH ERROR: %s",
                e
            )

            try:

                await status.edit_text(
                    "❌ <b>Bᴀᴛᴄʜ Lɪɴᴋ Fᴀɪʟᴇᴅ.</b>\n\n"
                    f"<code>{e}</code>"
                )

            except Exception:
                pass


    # ========================================================
    # /PBATCH
    #
    # Protected batch
    #
    # /pbatch 153700-153710
    # ========================================================

    @app.on_message(
        filters.command("pbatch")
    )
    async def protected_batch_handler(
        client,
        message
    ):

        user = message.from_user

        if not user:
            return

        if not is_link_admin(
            user.id
        ):

            return

        if message.chat.id != DATABASE_CHANNEL_ID:

            await message.reply_text(
                "❌ <b>Uꜱᴇ Tʜɪꜱ Cᴏᴍᴍᴀɴᴅ Iɴ Tʜᴇ "
                "Dᴀᴛᴀʙᴀsᴇ Cʜᴀɴɴᴇʟ.</b>"
            )

            return

        arguments = (
            message.command[1:]
        )

        message_ids = parse_message_ids(
            arguments
        )

        if not message_ids:

            await message.reply_text(
                "❌ <b>Pʟᴇᴀsᴇ Pʀᴏᴠɪᴅᴇ Mᴇssᴀɢᴇ IDs.</b>\n\n"

                "<b>Eхᴀᴍᴘʟᴇ:</b>\n"
                "<code>/pbatch 153700 153701 153702</code>\n\n"

                "<b>Rᴀɴɢᴇ:</b>\n"
                "<code>/pbatch 153700-153710</code>"
            )

            return

        if len(message_ids) > MAX_BATCH_FILES:

            await message.reply_text(
                f"❌ <b>Mᴀxɪᴍᴜᴍ "
                f"{MAX_BATCH_FILES} Fɪʟᴇs Pᴇʀ Bᴀᴛᴄʜ.</b>"
            )

            return

        status = await message.reply_text(
            "🔎 <b>Cʜᴇᴄᴋɪɴɢ Fɪʟᴇs...</b>"
        )

        try:

            valid_ids = (
                await get_valid_media_ids(
                    client,
                    message_ids
                )
            )

            if not valid_ids:

                await status.edit_text(
                    "❌ <b>Nᴏ Vᴀʟɪᴅ Mᴇᴅɪᴀ Fᴏᴜɴᴅ.</b>"
                )

                return

            token = await create_batch_link(
                message_ids=valid_ids,
                created_by=user.id,
                protected=True
            )

            link = await build_link(
                client,
                token
            )

            await status.edit_text(

                "🔐 <b>Pᴇʀᴍᴀɴᴇɴᴛ Pʀᴏᴛᴇᴄᴛᴇᴅ Bᴀᴛᴄʜ</b>\n\n"

                f"📁 <b>Fɪʟᴇs:</b> "
                f"<code>{len(valid_ids)}</code>\n"

                "🛡 <b>Fᴏʀᴡᴀʀᴅ Pʀᴏᴛᴇᴄᴛɪᴏɴ:</b> "
                "Eɴᴀʙʟᴇᴅ\n\n"

                f"🔗 <b>Lɪɴᴋ:</b>\n"
                f"{link}",

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
                "PBATCH ERROR: %s",
                e
            )

            try:

                await status.edit_text(
                    "❌ <b>Pʀᴏᴛᴇᴄᴛᴇᴅ Bᴀᴛᴄʜ Fᴀɪʟᴇᴅ.</b>\n\n"
                    f"<code>{e}</code>"
                )

            except Exception:
                pass


    # ========================================================
    # PERMANENT LINK START HANDLER
    #
    # /start pl_xxxxx
    # /start ba_xxxxx
    # /start pb_xxxxx
    # ========================================================

    @app.on_message(
        filters.private
        & filters.command("start")
    )
    async def permanent_link_start_handler(
        client,
        message
    ):

        if not message.command:
            return

        if len(
            message.command
        ) < 2:

            return

        payload = (
            message.command[1]
            .strip()
        )

        if not (
            payload.startswith("pl_")
            or payload.startswith("ba_")
            or payload.startswith("pb_")
        ):

            return

        user_id = (
            message.from_user.id
            if message.from_user
            else None
        )

        if not user_id:
            return

        # ----------------------------------------------------
        # GET LINK
        # ----------------------------------------------------

        link_data = (
            await permanent_links_collection.find_one(
                {
                    "token": payload
                }
            )
        )

        if not link_data:

            await message.reply_text(
                "❌ <b>Tʜɪs Pᴇʀᴍᴀɴᴇɴᴛ Lɪɴᴋ Iѕ Iɴᴠᴀʟɪᴅ Oʀ Eхᴘɪʀᴇᴅ.</b>"
            )

            return

        message_ids = (
            link_data.get(
                "message_ids",
                []
            )
        )

        protected = bool(
            link_data.get(
                "protected",
                False
            )
        )

        if not message_ids:

            await message.reply_text(
                "❌ <b>Nᴏ Fɪʟᴇs Fᴏᴜɴᴅ Fᴏʀ Tʜɪs Lɪɴᴋ.</b>"
            )

            return

        # ----------------------------------------------------
        # FORCE SUB
        # ----------------------------------------------------

        not_joined = (
            await check_all_fsubs(
                client,
                user_id
            )
        )

        if not_joined:

            await send_fsub_message(
                client,
                message,
                not_joined,
                deep_link=payload
            )

            return

        # ----------------------------------------------------
        # SEND FILES
        # ----------------------------------------------------

        sent_count = 0

        for message_id in message_ids:

            try:

                await client.copy_message(

                    chat_id=user_id,

                    from_chat_id=DATABASE_CHANNEL_ID,

                    message_id=int(
                        message_id
                    ),

                    protect_content=protected
                )

                sent_count += 1

            except Exception as e:

                logger.warning(
                    "PERMANENT FILE FAILED | "
                    "user=%s | message_id=%s | error=%s",
                    user_id,
                    message_id,
                    e
                )

        if sent_count == 0:

            await message.reply_text(
                "❌ <b>Fᴀɪʟᴇᴅ Tᴏ Sᴇɴᴅ Tʜᴇ Fɪʟᴇs.</b>"
            )

            return

        logger.info(
            "PERMANENT LINK SENT | "
            "user=%s | token=%s | files=%s",
            user_id,
            payload,
            sent_count
        )
