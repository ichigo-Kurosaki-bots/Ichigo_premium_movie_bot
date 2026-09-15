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
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telegraph import Telegraph

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

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# SMALL CAPS
# ============================================================

SMALL_CAPS = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

def smallcaps(text):
    return text.translate(SMALL_CAPS)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# TELEGRAPH
# ============================================================

async def upload_to_telegraph(file_path):

    try:
        tg = Telegraph()

        await asyncio.to_thread(
            tg.create_account,
            short_name="PremiumMovieBot"
        )

        result = await asyncio.to_thread(
            tg.upload_file,
            file_path
        )

        if isinstance(result, list) and result:
            return "https://telegra.ph" + result[0]

    except Exception as e:
        logging.exception("Telegraph upload error: %s", e)

    return None
    
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# CATBOX
# ============================================================

async def upload_to_catbox(file_path):

    try:

        with open(file_path, "rb") as f:

            response = await asyncio.to_thread(
                requests.post,
                "https://catbox.moe/user/api.php",
                data={
                    "reqtype": "fileupload"
                },
                files={
                    "fileToUpload": f
                },
                timeout=120
            )

        if response.status_code != 200:
            logging.error(
                "Catbox HTTP %s: %s",
                response.status_code,
                response.text[:500]
            )
            return None

        result = response.text.strip()

        if result.startswith("https://") or result.startswith("http://"):
            return result

    except Exception as e:
        logging.exception("Catbox upload error: %s", e)

    return None

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# IMGUR
# ============================================================

async def upload_to_imgur(file_path):

    if not IMGUR_CLIENT_ID:
        logging.warning("IMGUR_CLIENT_ID is not configured.")
        return None

    try:

        with open(file_path, "rb") as f:

            response = await asyncio.to_thread(
                requests.post,
                "https://api.imgur.com/3/image",
                headers={
                    "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
                },
                files={
                    "image": f
                },
                timeout=120
            )

        if response.status_code != 200:
            logging.error(
                "Imgur HTTP %s: %s",
                response.status_code,
                response.text[:500]
            )
            return None

        data = response.json()

        if data.get("success"):

            return data.get(
                "data",
                {}
            ).get("link")

    except Exception as e:
        logging.exception("Imgur upload error: %s", e)

    return None

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# UPLOAD SELECTED SERVICE
# ============================================================

async def run_upload(service, file_path):

    if service == "tg":
        return await upload_to_telegraph(file_path)

    if service == "catbox":
        return await upload_to_catbox(file_path)

    if service == "imgur":
        return await upload_to_imgur(file_path)

    return None
    
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# REGISTER HANDLERS
# ============================================================

def register_telegraph_handlers(app):

    # --------------------------------------------------------
    # /telegraph
    # --------------------------------------------------------

    @app.on_message(
        filters.command("telegraph") & filters.reply
    )
    async def telegraph_handler(client, message):

        replied = message.reply_to_message

        if not replied or not replied.photo:
            await message.reply_text(
                "❌ <b>Reply to an image.</b>"
            )
            return

        status = await message.reply_text(
            "📸 <b>Image ready.</b>\n\n"
            "Choose a service from the buttons below.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Tᴇʟᴇɢʀᴀᴘʜ",
                            callback_data="tg_upload"
                        ),
                        InlineKeyboardButton(
                            "Cᴀᴛʙᴏx",
                            callback_data="catbox_upload"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Iᴍɢᴜʀ",
                            callback_data="imgur_upload"
                        )
                    ]
                ]
            )
        )

        try:

            os.makedirs(
                "downloads",
                exist_ok=True
            )

            file_path = await client.download_media(
                replied.photo,
                file_name=(
                    f"downloads/"
                    f"telegraph_"
                    f"{message.chat.id}_"
                    f"{message.id}.jpg"
                )
            )

            if not file_path:

                await status.edit_text(
                    "❌ <b>Failed to download image.</b>"
                )
                return

            # ------------------------------------------------
            # Store session
            # ------------------------------------------------

            if not hasattr(
                client,
                "_telegraph_files"
            ):
                client._telegraph_files = {}

            client._telegraph_files[
                status.id
            ] = file_path

        except Exception as e:

            logging.exception(
                "Telegraph image download error: %s",
                e
            )

            await status.edit_text(
                "❌ <b>Failed to prepare image.</b>"
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # --------------------------------------------------------
    # BUTTON CALLBACK
    # --------------------------------------------------------

    @app.on_callback_query(
        filters.regex(
            r"^(tg|catbox|imgur)_upload$"
        )
    )
    async def telegraph_callback(
        client,
        callback_query
    ):

        status = callback_query.message

        await callback_query.answer()

        files = getattr(
            client,
            "_telegraph_files",
            {}
        )

        file_path = files.get(
            status.id
        )

        if not file_path:

            await status.edit_text(
                "❌ <b>Image session expired.</b>\n\n"
                "Use <code>/telegraph</code> again."
            )
            return

        if not os.path.exists(file_path):

            files.pop(
                status.id,
                None
            )

            await status.edit_text(
                "❌ <b>Image file no longer exists.</b>\n\n"
                "Use <code>/telegraph</code> again."
            )
            return

        service = callback_query.data.split(
            "_",
            1
        )[0]

        service_names = {
            "tg": "Telegraph",
            "catbox": "Catbox",
            "imgur": "Imgur"
        }

        service_name = service_names.get(
            service,
            "Service"
        )

        await status.edit_text(
            f"⏳ <b>Uploading to {service_name}...</b>"
        )

        try:

            url = await run_upload(
                service,
                file_path
            )

            if url:

                await status.edit_text(
                    "✅ <b>LINK GENERATED</b>\n\n"
                    f"🔗 <code>{url}</code>",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔗 Open Link",
                                    url=url
                                )
                            ]
                        ]
                    )
                )

            else:

                await status.edit_text(
                    f"❌ <b>{service_name} upload failed.</b>\n\n"
                    "Please try another service."
                )

        except Exception as e:

            logging.exception(
                "%s callback upload error: %s",
                service_name,
                e
            )

            await status.edit_text(
                f"❌ <b>{service_name} upload failed.</b>"
            )

        finally:

            try:
                os.remove(file_path)
            except Exception:
                pass

            files.pop(
                status.id,
                None
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

