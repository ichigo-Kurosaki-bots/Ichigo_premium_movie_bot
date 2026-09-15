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

        # ----------------------------------------------------
        # Direct Telegraph upload API
        # This avoids the telegraph Python package issue
        # ----------------------------------------------------

        with open(file_path, "rb") as f:

            response = await asyncio.to_thread(
                requests.post,
                "https://telegra.ph/upload",
                files={
                    "file": f
                },
                timeout=120
            )

        if response.status_code != 200:

            logging.error(
                "Telegraph HTTP %s: %s",
                response.status_code,
                response.text[:1000]
            )

            return None

        # ----------------------------------------------------
        # Parse JSON response
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception:

            logging.error(
                "Telegraph returned invalid JSON: %s",
                response.text[:1000]
            )

            return None

        # ----------------------------------------------------
        # Telegraph normally returns:
        #
        # [
        #     {
        #         "src": "/file/example.jpg"
        #     }
        # ]
        # ----------------------------------------------------

        if isinstance(data, list) and data:

            item = data[0]

            if isinstance(item, dict):

                src = item.get("src")

                if src:

                    if src.startswith("/"):

                        return (
                            "https://telegra.ph"
                            + src
                        )

                    if (
                        src.startswith("https://")
                        or
                        src.startswith("http://")
                    ):

                        return src

            elif isinstance(item, str):

                if item.startswith("/"):

                    return (
                        "https://telegra.ph"
                        + item
                    )

                if (
                    item.startswith("https://")
                    or
                    item.startswith("http://")
                ):

                    return item

        # ----------------------------------------------------
        # Unexpected response
        # ----------------------------------------------------

        logging.error(
            "Unexpected Telegraph response: %s",
            data
        )

    except Exception as e:

        logging.exception(
            "Telegraph upload error: %s",
            e
        )

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

        if (
            result.startswith("https://")
            or
            result.startswith("http://")
        ):

            return result

    except Exception as e:

        logging.exception(
            "Catbox upload error: %s",
            e
        )

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

        logging.error(
            "IMGUR_CLIENT_ID is not configured."
        )

        return None

    try:

        with open(file_path, "rb") as f:

            response = await asyncio.to_thread(
                requests.post,
                "https://api.imgur.com/3/image",
                headers={
                    "Authorization": (
                        "Client-ID "
                        f"{IMGUR_CLIENT_ID.strip()}"
                    )
                },
                files={
                    "image": f
                },
                timeout=120
            )

        # ----------------------------------------------------
        # HTTP ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            logging.error(
                "Imgur HTTP %s: %s",
                response.status_code,
                response.text[:2000]
            )

            return None

        # ----------------------------------------------------
        # JSON RESPONSE
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception:

            logging.error(
                "Imgur returned invalid JSON: %s",
                response.text[:2000]
            )

            return None

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        if data.get("success"):

            image_data = data.get(
                "data",
                {}
            )

            link = image_data.get(
                "link"
            )

            if link:

                return link

            logging.error(
                "Imgur success response has no link: %s",
                data
            )

            return None

        # ----------------------------------------------------
        # IMGUR API ERROR
        # ----------------------------------------------------

        logging.error(
            "Imgur API error: %s",
            data
        )

    except Exception as e:

        logging.exception(
            "Imgur upload error: %s",
            e
        )

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

        return await upload_to_telegraph(
            file_path
        )

    if service == "catbox":

        return await upload_to_catbox(
            file_path
        )

    if service == "imgur":

        return await upload_to_imgur(
            file_path
        )

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

    # ========================================================
    # /TELEGRAPH COMMAND
    # ========================================================

    @app.on_message(
        filters.command("telegraph") & filters.reply
    )
    async def telegraph_handler(
        client,
        message
    ):

        replied = message.reply_to_message

        if not replied or not replied.photo:

            await message.reply_text(
                "❌ <b>Reply to an image.</b>"
            )

            return

        # ----------------------------------------------------
        # DOWNLOAD STATUS
        # ----------------------------------------------------

        status = await message.reply_text(
            "📥 <b>Preparing image...</b>\n\n"
            "Please wait..."
        )

        try:

            os.makedirs(
                "downloads",
                exist_ok=True
            )

            # ------------------------------------------------
            # DOWNLOAD IMAGE FIRST
            # ------------------------------------------------

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
            # CREATE SESSION STORAGE
            # ------------------------------------------------

            if not hasattr(
                client,
                "_telegraph_files"
            ):

                client._telegraph_files = {}

            user_id = (
                message.from_user.id
                if message.from_user
                else message.chat.id
            )

            # ------------------------------------------------
            # STORE ONLY AFTER DOWNLOAD COMPLETES
            # ------------------------------------------------

            client._telegraph_files[
                status.id
            ] = {

                "file_path": file_path,

                "user_id": user_id,

                "created_at": (
                    asyncio.get_running_loop().time()
                )

            }

            # ------------------------------------------------
            # SHOW BUTTONS ONLY NOW
            # ------------------------------------------------

            keyboard = InlineKeyboardMarkup(
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

            await status.edit_text(
                "📸 <b>Image ready.</b>\n\n"
                "Choose a service from the buttons below.",
                reply_markup=keyboard
            )

        except Exception as e:

            logging.exception(
                "Telegraph image preparation error: %s",
                e
            )

            await status.edit_text(
                "❌ <b>Failed to prepare image.</b>"
            )

    # ========================================================
    # BUTTON CALLBACK
    # ========================================================

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

        files = getattr(
            client,
            "_telegraph_files",
            {}
        )

        session = files.get(
            status.id
        )

        # ----------------------------------------------------
        # SESSION CHECK
        # ----------------------------------------------------

        if not session:

            await callback_query.answer(
                "❌ Image session expired.",
                show_alert=True
            )

            try:

                await status.edit_text(
                    "❌ <b>Image session expired.</b>\n\n"
                    "Use <code>/telegraph</code> again."
                )

            except Exception:

                pass

            return

        # ----------------------------------------------------
        # USER CHECK
        # ----------------------------------------------------

        if (
            callback_query.from_user.id
            != session.get("user_id")
        ):

            await callback_query.answer(
                "❌ This image belongs to another user.",
                show_alert=True
            )

            return

        file_path = session.get(
            "file_path"
        )

        # ----------------------------------------------------
        # FILE CHECK
        # ----------------------------------------------------

        if (
            not file_path
            or
            not os.path.exists(file_path)
        ):

            files.pop(
                status.id,
                None
            )

            await callback_query.answer(
                "❌ Image file no longer exists.",
                show_alert=True
            )

            try:

                await status.edit_text(
                    "❌ <b>Image file no longer exists.</b>\n\n"
                    "Use <code>/telegraph</code> again."
                )

            except Exception:

                pass

            return

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------

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

        await callback_query.answer(
            f"Uploading to {service_name}..."
        )

        try:

            await status.edit_text(
                f"⏳ <b>Uploading to {service_name}...</b>"
            )

            # ------------------------------------------------
            # UPLOAD
            # ------------------------------------------------

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

            try:

                await status.edit_text(
                    f"❌ <b>{service_name} upload failed.</b>\n\n"
                    "Please try another service."
                )

            except Exception:

                pass

        finally:

            # ------------------------------------------------
            # CLEANUP AFTER UPLOAD ATTEMPT
            # ------------------------------------------------

            try:

                if os.path.exists(file_path):

                    os.remove(
                        file_path
                    )

            except Exception as e:

                logging.warning(
                    "Failed to remove telegraph file: %s",
                    e
                )

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
