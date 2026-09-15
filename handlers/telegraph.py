# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

import os
import asyncio
import logging
import requests

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from LucyBot.Bot import Codeflix
from telegraph import Telegraph

logger = logging.getLogger(__name__)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# CONFIG
# ============================================================

IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID", "")

ENVS_UPLOAD_URL = "https://envs.sh"

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #


# ============================================================
# SMALL CAPS
# ============================================================

def smallcaps(text: str) -> str:

    normal = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
    )

    small = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    )

    # Correct mapping
    mapping = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    )

    return text.translate(mapping)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD TO TELEGRAPH
# ============================================================

def upload_telegraph(file_path):

    telegraph = Telegraph()

    telegraph.create_account(
        short_name="AeroBot"
    )

    with open(file_path, "rb") as photo:

        response = telegraph.upload_file(
            photo
        )

    if not response:
        return None

    return (
        "https://telegra.ph"
        + response[0]
    )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD TO ENVS.SH
# ============================================================

def upload_envs(file_path):

    with open(file_path, "rb") as file:

        response = requests.post(
            ENVS_UPLOAD_URL,
            files={
                "file": file
            },
            timeout=60
        )

    if response.status_code != 200:
        return None

    result = response.text.strip()

    if not result:
        return None

    if result.startswith("http://") or result.startswith("https://"):
        return result

    return result

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD TO CATBOX
# ============================================================

def upload_catbox(file_path):

    with open(file_path, "rb") as file:

        response = requests.post(
            "https://catbox.moe/user/api.php",
            data={
                "reqtype": "fileupload"
            },
            files={
                "fileToUpload": file
            },
            timeout=120
        )

    if response.status_code != 200:
        return None

    result = response.text.strip()

    if not result:
        return None

    if result.startswith("http://") or result.startswith("https://"):
        return result

    return None

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD TO IMGUR
# ============================================================

def upload_imgur(file_path):

    if not IMGUR_CLIENT_ID:
        return None

    headers = {
        "Authorization": (
            f"Client-ID {IMGUR_CLIENT_ID}"
        )
    }

    with open(file_path, "rb") as file:

        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            files={
                "image": file
            },
            timeout=120
        )

    if response.status_code != 200:
        return None

    data = response.json()

    if not data.get("success"):
        return None

    return data.get("data", {}).get("link")

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD WORKER
# ============================================================

async def upload_image(
    service,
    file_path
):

    loop = asyncio.get_running_loop()

    try:

        if service == "telegraph":

            return await loop.run_in_executor(
                None,
                upload_telegraph,
                file_path
            )

        if service == "envs":

            return await loop.run_in_executor(
                None,
                upload_envs,
                file_path
            )

        if service == "catbox":

            return await loop.run_in_executor(
                None,
                upload_catbox,
                file_path
            )

        if service == "imgur":

            return await loop.run_in_executor(
                None,
                upload_imgur,
                file_path
            )

    except Exception as e:

        logger.exception(
            f"{service} upload failed: {e}"
        )

    return None

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# HANDLER
# ============================================================

@Codeflix.on_message(
    filters.command("telegraph")
)
async def telegraph_handler(
    client,
    message
):

    if not message.reply_to_message:

        return await message.reply_text(
            smallcaps(
                "❌ Reply to an image with /telegraph."
            )
        )

    reply = message.reply_to_message

    if not reply.photo:

        return await message.reply_text(
            smallcaps(
                "❌ Please reply to an image/photo."
            )
        )

    status = await message.reply_text(
        smallcaps(
            "⏳ Choose an upload service:"
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        smallcaps("ᴛᴇʟᴇɢʀᴀᴘʜ"),
                        callback_data="tg_upload"
                    ),
                    InlineKeyboardButton(
                        smallcaps("ᴇɴᴠs.ѕʜ"),
                        callback_data="envs_upload"
                    )
                ],
                [
                    InlineKeyboardButton(
                        smallcaps("ᴄᴀᴛʙᴏx.ᴍᴏᴇ"),
                        callback_data="catbox_upload"
                    ),
                    InlineKeyboardButton(
                        smallcaps("ɪᴍɢᴜʀ"),
                        callback_data="imgur_upload"
                    )
                ]
            ]
        )
    )

    file_path = None

    try:

        file_path = await reply.download()

        if not file_path:

            return await status.edit_text(
                smallcaps(
                    "❌ Failed to download the image."
                )
            )

        # Store temporary path on message object
        # for the callback.
        await client.send_message(
            message.chat.id,
            smallcaps(
                "📸 Image ready. "
                "Choose a service from the buttons above."
            ),
            reply_to_message_id=status.id
        )

        # Save path in memory for callback
        if not hasattr(client, "_telegraph_files"):
            client._telegraph_files = {}

        client._telegraph_files[
            status.id
        ] = file_path

    except Exception as e:

        logger.exception(
            f"Telegraph preparation failed: {e}"
        )

        if file_path and os.path.exists(file_path):

            try:
                os.remove(file_path)
            except Exception:
                pass

        await status.edit_text(
            smallcaps(
                "❌ Failed to prepare the image."
            )
        )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# CALLBACK
# ============================================================

@Codeflix.on_callback_query(
    filters.regex(
        r"^(tg|envs|catbox|imgur)_upload$"
    )
)
async def telegraph_upload_callback(
    client,
    callback_query
):

    await callback_query.answer()

    status = callback_query.message

    if not hasattr(client, "_telegraph_files"):

        return await status.edit_text(
            smallcaps(
                "❌ Upload session expired."
            )
        )

    file_path = client._telegraph_files.get(
        status.id
    )

    if not file_path or not os.path.exists(file_path):

        return await status.edit_text(
            smallcaps(
                "❌ Image file is no longer available."
            )
        )

    service = callback_query.data.replace(
        "_upload",
        ""
    )

    service_names = {
        "tg": "ᴛᴇʟᴇɢʀᴀᴘʜ",
        "envs": "ᴇɴᴠs.ѕʜ",
        "catbox": "ᴄᴀᴛʙᴏx.ᴍᴏᴇ",
        "imgur": "ɪᴍɢᴜʀ"
    }

    service_name = service_names.get(
        service,
        "ᴜᴘʟᴏᴀᴅ"
    )

    # Imgur requires Client ID
    if service == "imgur" and not IMGUR_CLIENT_ID:

        return await status.edit_text(
            smallcaps(
                "❌ ɪᴍɢᴜʀ ᴄʟɪᴇɴᴛ ɪᴅ ɪs ɴᴏᴛ ᴄᴏɴꜰɪɢᴜʀᴇᴅ."
            )
        )

    try:

        await status.edit_text(
            smallcaps(
                f"⏳ Uploading to {service_name}..."
            )
        )

        link = await upload_image(
            service,
            file_path
        )

        if not link:

            return await status.edit_text(
                smallcaps(
                    f"❌ {service_name} upload failed."
                )
            )

        await status.edit_text(
            smallcaps(
                "✅ ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ\n\n"
                f"🔗 {link}"
            )
        )

    except Exception as e:

        logger.exception(
            f"Upload callback error: {e}"
        )

        await status.edit_text(
            smallcaps(
                f"❌ ᴇʀʀᴏʀ: {str(e)[:300]}"
            )
        )

    finally:

        if file_path and os.path.exists(file_path):

            try:
                os.remove(file_path)
            except Exception:
                pass

        try:
            del client._telegraph_files[
                status.id
            ]
        except Exception:
            pass

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #
