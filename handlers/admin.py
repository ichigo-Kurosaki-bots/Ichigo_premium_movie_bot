# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

import logging
import asyncio
import os
import time
import psutil

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

from html import escape
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

from pyrogram import filters
from pyrogram.enums import ChatType
from config import OWNER_ID, ADMIN_IDS
from premium import get_plan_by_amount

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

from database import (
    get_user,
    get_all_user_ids,
    users_collection,
    count_users,
    count_premium_users,
    count_media,
    count_chats,
    get_stats,
    get_media_storage_stats,
    activate_premium,
    remove_premium,
    get_indexer_state,
    get_trending_searches
)

logger = logging.getLogger(__name__)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):
    return user_id == OWNER_ID or user_id in ADMIN_IDS


admin_only = filters.create(
    lambda _, __, message: (
        message.from_user is not None
        and is_admin(message.from_user.id)
    )
)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# REGISTER ADMIN HANDLERS
# ============================================================

def register_admin_handlers(app):

    # ========================================================
    # /alive
    # ========================================================

    @app.on_message(
        filters.command("alive")
    )
    async def alive_handler(
        client,
        message
    ):

        alive_image = os.getenv(
            "ALIVE_IMAGE",
            ""
        )

        text = (
            "Yᴏᴜ ᴀʀᴇ ᴠᴇʀʏ ʟᴜᴄᴋʏ 🤞 "
            "I ᴀᴍ ᴀʟɪᴠᴇ ❤️\n\n"

            "Pʀᴇss /start ᴛᴏ ᴜsᴇ ᴍᴇ!"
        )

        sent = None

        try:

            if alive_image:

                sent = await message.reply_photo(
                    photo=alive_image,
                    caption=text
                )

            else:

                sent = await message.reply_text(
                    text
                )

            # ------------------------------------------------
            # DELETE AFTER 30 SECONDS
            # ------------------------------------------------

            await asyncio.sleep(30)

            try:
                await sent.delete()
            except Exception:
                pass

        except Exception as e:

            logger.warning(
                "Alive command failed: %s",
                e
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /trendlist
    # ========================================================

    @app.on_message(
        filters.command("trendlist")
    )
    async def trendlist_handler(
        client,
        message
    ):

        try:

            trends = await get_trending_searches(
                limit=29
            )

            if not trends:

                await message.reply_text(
                    "📊 <b>Nᴏ Tʀᴇɴᴅɪɴɢ Sᴇᴀʀᴄʜᴇs Yᴇᴛ.</b>\n\n"
                    "Sᴇᴀʀᴄʜᴇs Wɪʟʟ Aᴘᴘᴇᴀʀ Hᴇʀᴇ Wʜᴇɴ U sᴇʀs Sᴇᴀʀᴄʜ."
                )

                return

            lines = []

            for index, item in enumerate(
                trends,
                start=1
            ):

                query = item[0]

                lines.append(
                    f"{index}. {query}"
                )

            text = (
                "Tᴏᴘ 29 Tʀᴀɴᴅɪɴɢ ᴏғ ᴛʜᴇ Dᴀʏ 👇:\n\n"
                + "\n".join(lines)
                + "\n\n"
                "⚡️ 𝑨𝒍𝒍 𝒕𝒉𝒆 𝒓𝒆𝒔𝒖𝒍𝒕𝒔 𝒂𝒃𝒐𝒗𝒆 𝒄𝒐𝒎𝒆 "
                "𝒇𝒓𝒐𝒎 𝒘𝒉𝒂𝒕 𝒖𝒔𝒆𝒓𝒔 𝒉𝒂𝒗𝒆 𝒔𝒆𝒂𝒓𝒄𝒉𝒆𝒅 𝒇𝒐𝒓. "
                "𝑻𝒉𝒆𝒚'𝒓𝒆 𝒔𝒉𝒐𝒘𝒏 𝒕𝒐 𝒚𝒐𝒖 𝒆𝒙𝒂𝒄𝒕𝒍𝒚 𝒂𝒔 𝒕𝒉𝒆𝒚 𝒘𝒆𝒓𝒆 "
                "𝒔𝒆𝒂𝒓𝒄𝒉𝒆𝒅, 𝒘𝒊𝒕𝒉𝒐𝒖𝒕 𝒂𝒏𝒚 𝒄𝒉𝒂𝒏𝒈𝒆𝒔 𝒃𝒚 𝒕𝒉𝒆 𝒐𝒘𝒏𝒆𝒓."
            )

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Cʟᴏsᴇ •",
                            callback_data="close_trendlist"
                        )
                    ]
                ]
            )

            await message.reply_text(
                text,
                reply_markup=buttons
            )

        except Exception as e:

            logger.exception(
                "Trendlist error: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Could not load trending searches.</b>"
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # CLOSE TRENDLIST
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^close_trendlist$")
    )
    async def close_trendlist_callback(
        client,
        callback
    ):

        try:

            await callback.message.delete()

        except Exception:

            try:
                await callback.answer(
                    "Unable to close this message.",
                    show_alert=True
                )
                return

            except Exception:
                pass

        await callback.answer()
        
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /stats
    # ========================================================

    @app.on_message(
        filters.command("stats")
        & admin_only
    )
    async def stats_handler(
        client,
        message
    ):

        try:

            # ----------------------------------------------------
            # DATABASE STATS
            # ----------------------------------------------------
            extracting_message = await message.reply_text(
                "⏳ <b>Exᴛʀᴀᴄᴛɪɴɢ Sᴛᴀᴛs...</b>"
            )
            stats = await get_stats()

            users = stats.get(
                "users",
                0
            )

            media = stats.get(
                "media",
                0
            )

            premium_users = stats.get(
                "premium_users",
                0
            )

            used_storage = stats.get(
                "used_storage_text",
                "0.00 MB"
            )

            # ----------------------------------------------------
            # CHAT COUNT
            # ----------------------------------------------------

            chats = stats.get(
                "chats",
                0
            )

            # ----------------------------------------------------
            # RAM
            # ----------------------------------------------------

            memory = psutil.virtual_memory()

            ram_percent = memory.percent

            # ----------------------------------------------------
            # CPU
            # ----------------------------------------------------

            cpu_percent = psutil.cpu_percent(
                interval=0.5
            )

            # ----------------------------------------------------
            # DISK
            # ----------------------------------------------------

            disk = psutil.disk_usage(
                "/"
            )

            disk_percent = disk.percent

            disk_used_gb = (
                disk.used
                / (1024 ** 3)
            )

            disk_free_gb = (
                disk.free
                / (1024 ** 3)
            )

            disk_total_gb = (
                disk.total
                / (1024 ** 3)
            )

            # ----------------------------------------------------
            # PROGRESS BAR
            # ----------------------------------------------------

            def progress_bar(
                percent,
                length=10
            ):

                filled = int(
                    percent / 100 * length
                )

                filled = max(
                    0,
                    min(
                        filled,
                        length
                    )
                )

                empty = length - filled

                return (
                    "■" * filled
                    + "□" * empty
                )

            # ----------------------------------------------------
            # STATS TEXT
            # ----------------------------------------------------

            text = (

                "⌬ <b>𝗕𝗢𝗧 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 :</b>\n\n"

                f"┎ <b>›› Tᴏᴛᴀʟ Uꜱᴇʀꜱ :</b> "
                f"<b>{users:,}</b>\n"
                f"┖ <b>›› Tᴏᴛᴀʟ Cʜᴀᴛꜱ :</b> "
                f"<b>{chats:,}</b>\n\n"

                "┎ <b>›› RAM ( MEMORY ):</b>\n"
                f"┖ [{progress_bar(ram_percent)}] "
                f"<b>›› {ram_percent:.1f}%</b>\n\n"

                "┎ <b>›› CPU ( USAGE ) :</b>\n"
                f"┖ [{progress_bar(cpu_percent)}] "
                f"<b>›› {cpu_percent:.1f}%</b>\n\n"

                "┎ <b>›› DISK :</b>\n"
                f"┃ [{progress_bar(disk_percent)}] "
                f"<b>›› {disk_percent:.1f}%</b>\n"
                f"┃ <b>›› Usᴇᴅ :</b> "
                f"<b>›› {disk_used_gb:.2f} GB</b>\n"
                f"┃ <b>›› Fʀᴇᴇ :</b> "
                f"<b>›› {disk_free_gb:.2f} GB</b>\n"
                f"┖ <b>›› Tᴏᴛᴀʟ :</b> "
                f"<b>›› {disk_total_gb:.2f} GB</b>\n\n"

                "┎ <b>𝗗𝗔𝗧𝗔𝗕𝗔𝗦𝗘 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 :</b>\n"
                f"┃ <b>›› Tᴏᴛᴀʟ Fɪʟᴇs :</b> "
                f"<b>›› {media:,}</b>\n"
                f"┖ <b>›› Tᴏᴛᴀʟ Sᴛᴏʀᴀɢᴇ Usᴇᴅ :</b> "
                f"<b>›› {used_storage}</b>\n\n"

                f"💎 <b>›› Pʀᴇᴍɪᴜᴍ Usᴇʀs :</b> "
                f"<b>›› {premium_users:,}</b>\n\n"

                "<b>›› Powered By: @Aero_Unity</b>"
            )

            await extracting_message.edit_text(
                text
            )
            await asyncio.sleep(30)

            try:
                await extracting_message.delete()
            except Exception:
                pass

        except Exception as e:

            logger.exception(
                "Stats error: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Could not get statistics.</b>\n\n"
                f"<code>{e}</code>"
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /premiumuser 
    # ========================================================
    @app.on_message(
        filters.command("premiumuser")
        & admin_only
    )
    async def premium_user_handler(
        client,
        message
    ):

        try:

            # ------------------------------------------------
            # GET ALL PREMIUM USERS
            # ------------------------------------------------

            import database

            cursor = database.users_collection.find(
                {
                    "premium": True
                }
            )

            premium_users = []

            async for user in cursor:
                premium_users.append(user)

            # ------------------------------------------------
            # NO PREMIUM USERS
            # ------------------------------------------------

            if not premium_users:

                await message.reply_text(
                    "<b>Pʀᴇᴍɪᴜᴍ Usᴇʀs</b>\n\n"
                    "Nᴏ Pʀᴇᴍɪᴜᴍ Usᴇʀs Fᴏᴜɴᴅ."
                )

                return

            # ------------------------------------------------
            # TOTAL PREMIUM USERS
            # ------------------------------------------------

            text = (
                " <b>Pʀᴇᴍɪᴜᴍ Usᴇʀs</b>\n\n"
                f"<b>›› Tᴏᴛᴀʟ Pʀᴇᴍɪᴜᴍ Usᴇʀs:</b> "
                f"<code>{len(premium_users)}</code>\n\n"
            )

            # ------------------------------------------------
            # USER LIST
            # ------------------------------------------------

            for index, user in enumerate(
                premium_users,
                start=1
            ):

                user_id = user.get(
                    "user_id",
                    "Unknown"
                )

                first_name = user.get(
                    "first_name",
                    "Unknown"
                )

                username = user.get(
                    "username",
                    ""
                )

                plan = user.get(
                    "plan"
                ) or "Premium"

                paid_amount = user.get(
                    "paid_amount",
                    0
                )

                premium_requests = user.get(
                    "premium_requests",
                    0
                )

                remaining = user.get(
                    "remaining_requests",
                    0
                )

                text += (
                    f"<b>{index}.</b> "
                    f"<b>›› {escape(str(first_name))}</b>\n"
                    f"<b>›› 🆔 <code>{user_id}</code></b>\n"
                )

                if username:
                    text += (
                        f"   🔹 @{escape(str(username))}\n"
                    )

                text += (
                    f"   ›› Pʟᴀɴ: <b>{escape(str(plan))}</b>\n"
                    f"   ›› Pᴀɪᴅ: <b>₹{paid_amount}</b>\n"
                    f"   ›› Pʟᴀɴ Rᴇǫᴜᴇsᴛs: "
                    f"<b>{premium_requests}</b>\n"
                    f"   ›› Rᴇᴍᴀɪɴɪɴɢ: "
                    f"<b>{remaining}</b>\n\n"
                )

                # ------------------------------------------------
                # TELEGRAM MESSAGE LIMIT
                # ------------------------------------------------

                if len(text) >= 3500:

                    await message.reply_text(
                        text
                    )

                    text = ""

            # ------------------------------------------------
            # SEND REMAINING TEXT
            # ------------------------------------------------

            if text.strip():

                await message.reply_text(
                    text
                )

        except Exception as e:

            logger.exception(
                "Premium user list error: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Could not load Premium users.</b>\n\n"
                f"<code>{escape(str(e))}</code>"
            )
            
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ------ Activate User ------- #

    @app.on_message(
        filters.command("activate")
        & admin_only
    )
    async def activate_handler(
        client,
        message
    ):

        if len(message.command) < 3:

            await message.reply_text(
                "<code>/activate USER_ID AMOUNT</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/activate 123456789 100</code>"
            )

            return

        try:

            user_id = int(
                message.command[1]
            )

            amount = int(
                message.command[2]
            )

        except ValueError:

            await message.reply_text(
                "❌ User ID and amount must "
                "be numbers."
            )

            return

        plan = get_plan_by_amount(
            amount
        )

        if not plan:

            await message.reply_text(
                "❌ Invalid Premium plan."
            )

            return

        user = await get_user(
            user_id
        )

        if not user:

            await message.reply_text(
                "❌ User does not exist in "
                "the database.\n\n"
                "Ask the user to start the bot first."
            )

            return

        success = await activate_premium(
            user_id=user_id,
            plan_name=plan.get(
                "name",
                "Premium"
            ),
            amount=amount,
            requests=plan.get(
                "requests",
                0
            )
        )

        if not success:

            await message.reply_text(
                "❌ Premium activation failed."
            )

            return

        await message.reply_text(
            "✅ <b>Pʀᴇᴍɪᴜᴍ Aᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"

            f"<b>›› Usᴇʀ: </b> "
            f"<code>{user_id}</code>\n"

            f"<b>›› Pʟᴀɴ: </b> "
            f"<b>{plan.get('name', 'Premium')}</b>\n"

            f"<b>›› Aᴍᴏᴜɴᴛ: </b> "
            f"<b>₹{amount}</b>\n"

            f"<b>›› Rᴇǫᴜᴇsᴛs: </b> "
            f"<b>{plan.get('requests', 0)}</b>"
        )

        try:

            await client.send_message(
                user_id,

                "🎉 <b>Yᴏᴜʀ Pʟᴀɴ Is Aᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"

                f"<b>›› Pʟᴀɴ: </b> "
                f"<b>{plan.get('name', 'Premium')}</b>\n"

                f"<b>›› Pᴀɪᴅ: </b> "
                f"<b>₹{amount}</b>\n"

                f"<b>›› Mᴏᴠɪᴇ requests: </b> "
                f"<b>{plan.get('requests', 0)}</b>\n\n"

                "<b><i>✨️ Yᴏᴜ Cᴀɴ Nᴏᴡ Sᴇᴀʀᴄʜ ᴀɴᴅ Rᴇǫᴜᴇsᴛ Mᴏᴠɪᴇs, Sᴇʀɪᴇs, Dʀᴀᴍᴀs, Aɴɪᴍᴇs, TV Sᴇʀɪᴀʟs...</i></b>"
            )

        except Exception as e:

            logger.warning(
                "Could not notify user %s: %s",
                user_id,
                e
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /deactivate USER_ID
    # ========================================================

    @app.on_message(
        filters.command("deactivate")
        & admin_only
    )
    async def deactivate_handler(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Usage:</b>\n"
                "<code>/deactivate USER_ID</code>"
            )

            return

        try:

            user_id = int(
                message.command[1]
            )

        except ValueError:

            await message.reply_text(
                "❌ Invalid User ID."
            )

            return

        user = await get_user(
            user_id
        )

        if not user:

            await message.reply_text(
                "❌ User not found."
            )

            return

        success = await remove_premium(
            user_id
        )

        if not success:

            await message.reply_text(
                "❌ Failed to deactivate Premium."
            )

            return

        await message.reply_text(
            "✅ <b>Pʀᴇᴍɪᴜᴍ Dᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"
            f"<b>›› Usᴇʀ: </b> <code>{user_id}</code>"
        )

        try:

            await client.send_message(
                user_id,

                "ℹ️ <b>Pʀᴇᴍɪᴜᴍ Dᴇᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"
                "<b>Sᴏʀʀʏ Tᴏ Sᴀʏ, Yᴏᴜʀ Pʀᴇᴍɪᴜᴍ Aᴄᴄᴇss Hᴀs Bᴇᴇɴ Rᴇᴍᴏᴠᴇᴅ</b>."
            )

        except Exception as e:

            logger.warning(
                "Could not notify user %s: %s",
                user_id,
                e
            )
            
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /indexstatus
    # ========================================================

    @app.on_message(
        filters.command("indexstatus")
        & admin_only
    )
    async def index_status_handler(
        client,
        message
    ):

        checking_message = None

        try:

            # ----------------------------------------------------
            # INDEX STATUS IMAGE
            # ----------------------------------------------------
   
            INDEX_STATUS_IMAGE_URL = "https://graph.org/file/ab9086afb983c6cfae7d7-2d89195fff84a26ce9.jpg"

            # ----------------------------------------------------
            # CHECKING MESSAGE WITH IMAGE
            # ----------------------------------------------------

            checking_message = await client.send_photo(
                chat_id=message.chat.id,
                photo=INDEX_STATUS_IMAGE_URL,
                caption=(
                    "🔎 <b>ᴄʜᴇᴄᴋɪɴɢ ɪɴᴅᴇx ғɪʟᴇs...</b>"
                )
            )

            # ----------------------------------------------------
            # GET INDEXER STATE
            # ----------------------------------------------------

            state = await get_indexer_state()

            last_message = state.get(
                "last_message_id",
                0
            )

            # ----------------------------------------------------
            # GET REAL MONGODB MEDIA STATISTICS
            # ----------------------------------------------------

            storage = await get_media_storage_stats()

            total_files = storage.get(
                "total_files",
                0
            )

            total_size = storage.get(
                "total_size",
                0
            )

            # ----------------------------------------------------
            # CONVERT BYTES
            # ----------------------------------------------------

            if total_size >= 1024 ** 3:

                size_text = (
                    f"{total_size / (1024 ** 3):.2f} GB"
                )

            elif total_size >= 1024 ** 2:
  
                size_text = (
                     f"{total_size / (1024 ** 2):.2f} MB"
                 )

            elif total_size >= 1024:

                size_text = (
                    f"{total_size / 1024:.2f} KB"
                )

            else:

                 size_text = (
                     f"{total_size} B"
                 )

            # ----------------------------------------------------
            # FINAL STATUS
            # ----------------------------------------------------

            await checking_message.edit_caption(

                caption=(
                    "📚 <b>Iɴᴅᴇxᴇʀ Sᴛᴀᴛᴜs</b>\n\n"

                    f"<b>›› Tᴏᴛᴀʟ Iɴᴅᴇxᴇᴅ Fɪʟᴇs:</b> "
                    f"<b>{total_files:,}</b>\n\n"

                    f"<b>›› Tᴏᴛᴀʟ Iɴᴅᴇxᴇᴅ Sᴛᴏʀᴀɢᴇ:</b> "
                    f"<b>{size_text}</b>\n\n"

                    f"<b>›› Lᴀsᴛ Mᴇssᴀɢᴇ ID:</b> "
                    f"<code>{last_message}</code>\n\n"

                    "<b>›› Pᴏᴡᴇʀᴇᴅ Bʏ : @Aero_Unity</b>"
                )
            )

            # ----------------------------------------------------
            # WAIT 30 SECONDS
            # ----------------------------------------------------

            await asyncio.sleep(30)

            # ----------------------------------------------------
            # DELETE STATUS MESSAGE
            # ----------------------------------------------------

            try:
                await checking_message.delete()
            except Exception:
                pass

            # ----------------------------------------------------
            # DELETE /indexstatus COMMAND
            # ----------------------------------------------------

            try:
                await message.delete()
            except Exception:
                pass

        except Exception as e:
            logger.exception(
                "Indexer status error: %s",
                e
            )

            # ----------------------------------------------------
            # ERROR MESSAGE
            # ----------------------------------------------------

            if checking_message:

                try:

                    await checking_message.edit_caption(
                        caption=(
                            "❌ <b>Could not get indexer status.</b>\n\n"
                            f"<code>{e}</code>"
                        )
                    )

                    await asyncio.sleep(30)

                    try:
                        await checking_message.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

            else:

                try:

                    error_message = await message.reply_text(
                        "❌ <b>Could not get indexer status.</b>\n\n"
                        f"<code>{e}</code>"
                    )

                    await asyncio.sleep(30)

                    try:
                        await error_message.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

        # ----------------------------------------------------
        # DELETE /indexstatus COMMAND
        # ----------------------------------------------------

        try:
            await message.delete()
        except Exception:
            pass
            
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /resetindex
    # ========================================================

    @app.on_message(
        filters.command("resetindex")
        & admin_only
    )
    async def reset_index_handler(
        client,
        message
    ):

        try:

            from database import (
                reset_indexer
            )

            await reset_indexer()

            await message.reply_text(
                "✅ <b>Iɴᴅᴇxᴇʀ Pᴏsɪᴛɪᴏɴ Rᴇsᴇᴛ.</b>\n\n"
                "<b>Tʜᴇ Nᴇxᴛ Iɴᴅᴇxɪɴɢ Rᴜɴ ᴡɪʟʟ Sᴛᴀʀᴛ "
                "Fʀᴏᴍ Tʜᴇ Bᴇɢɪɴɴɪɴɢ</b>"
            )

        except Exception as e:
            logger.exception(
                "Reset index error: %s",
                e
            )

            await message.reply_text(
                "❌ Failed to reset indexer."
            )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /id
    # ========================================================

    @app.on_message(
        filters.command("id")
    )
    async def id_handler(
        client,
        message
    ):

        user_id = message.from_user.id

        await message.reply_text(
            "<b>Your Telegram ID</b>\n\n"
            f"ID - <code>{user_id}</code>"
        )
        
# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ========================================================
    # /broadcast
    # ========================================================

    @app.on_message(
        filters.command("broadcast")
        & admin_only
    )
    async def broadcast_handler(
        client,
        message
    ):

        # ----------------------------------------------------
        # CHECK REPLY
        # ----------------------------------------------------

        if not message.reply_to_message:

            await message.reply_text(
                "❌ <b>Reply to the message you want to broadcast.</b>"
            )

            return

        source = message.reply_to_message

        # ----------------------------------------------------
        # STATUS MESSAGE
        # ----------------------------------------------------

        status = await message.reply_text(
            "<b>Bʀᴏᴀᴅᴄᴀsᴛ Sᴛᴀʀᴛᴇᴅ...</b>"
        )

        # ----------------------------------------------------
        # GET ALL USERS
        # ----------------------------------------------------

        try:

            user_ids = await get_all_user_ids()

        except Exception as e:

            logger.exception(
                "Failed to get users for broadcast: %s",
                e
            )

            await status.edit_text(
                "❌ <b>Broadcast Failed</b>\n\n"
                "Could not get users from the database."
            )

            return

        # ----------------------------------------------------
        # REMOVE INVALID / DUPLICATE IDS
        # ----------------------------------------------------

        clean_user_ids = []

        for user_id in user_ids:

            try:

                user_id = int(user_id)

                if user_id not in clean_user_ids:
                    clean_user_ids.append(user_id)

            except (TypeError, ValueError):

                continue

        user_ids = clean_user_ids

        total = len(user_ids)

        # ----------------------------------------------------
        # NO USERS
        # ----------------------------------------------------

        if total == 0:

            await status.edit_text(
                "❌ <b>No users found.</b>"
            )

            return

        # ----------------------------------------------------
        # COUNTERS
        # ----------------------------------------------------

        success = 0
        failed = 0

        # ----------------------------------------------------
        # BROADCAST LOOP
        # ----------------------------------------------------

        for user_id in user_ids:

            try:

                # ------------------------------------------------
                # TEXT MESSAGE
                # ------------------------------------------------

                if source.text:

                    text = source.text.strip()

                    if text:

                        formatted_text = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(text)}"
                            "</b>"
                            "</blockquote>"
                        )

                        await client.send_message(
                            chat_id=user_id,
                            text=formatted_text,
                            reply_markup=source.reply_markup
                        )

                # ------------------------------------------------
                # PHOTO
                # ------------------------------------------------

                elif source.photo:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_photo(
                        chat_id=user_id,
                        photo=source.photo.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # VIDEO
                # ------------------------------------------------

                elif source.video:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_video(
                        chat_id=user_id,
                        video=source.video.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # DOCUMENT
                # ------------------------------------------------

                elif source.document:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_document(
                        chat_id=user_id,
                        document=source.document.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # AUDIO
                # ------------------------------------------------

                elif source.audio:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_audio(
                        chat_id=user_id,
                        audio=source.audio.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # VOICE
                # ------------------------------------------------

                elif source.voice:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_voice(
                        chat_id=user_id,
                        voice=source.voice.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # ANIMATION / GIF
                # ------------------------------------------------

                elif source.animation:

                    caption = source.caption or ""

                    if caption:

                        caption = (
                            "<blockquote>"
                            "<b>"
                            f"{escape(caption)}"
                            "</b>"
                            "</blockquote>"
                        )

                    await client.send_animation(
                        chat_id=user_id,
                        animation=source.animation.file_id,
                        caption=caption or None,
                        parse_mode="html",
                        reply_markup=source.reply_markup
                    )

                # ------------------------------------------------
                # STICKER
                # ------------------------------------------------

                elif source.sticker:

                    await client.send_sticker(
                        chat_id=user_id,
                        sticker=source.sticker.file_id
                    )

                # ------------------------------------------------
                # OTHER MESSAGE TYPES
                # ------------------------------------------------

                else:

                    await client.copy_message(
                        chat_id=user_id,
                        from_chat_id=source.chat.id,
                        message_id=source.id
                    )

                success += 1

            except Exception as e:

                failed += 1

                logger.warning(
                    "Broadcast failed for user %s: %s",
                    user_id,
                    e
                )

            # ------------------------------------------------
            # SMALL DELAY
            # ------------------------------------------------

            await asyncio.sleep(0.05)

            # ------------------------------------------------
            # UPDATE STATUS
            # ------------------------------------------------

            processed = success + failed

            if processed % 25 == 0:

                try:

                    await status.edit_text(
                        "📢 <b>Bʀᴏᴀᴅᴄᴀsᴛɪɴɢ...</b>\n\n"

                        f"👥 <b>Tᴏᴛᴀʟ Usᴇʀs:</b> "
                        f"<code>{total}</code>\n\n"

                        f"✅ <b>Sᴇɴᴛ:</b> "
                        f"<code>{success}</code>\n"

                        f"❌ <b>Fᴀɪʟᴇᴅ:</b> "
                        f"<code>{failed}</code>\n\n"

                        f"📊 <b>Pʀᴏɢʀᴇss:</b> "
                        f"<code>{processed}/{total}</code>"
                    )

                except Exception:

                    pass

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        try:

            await status.edit_text(
                "📢 <b>Bʀᴏᴀᴅᴄᴀsᴛ Cᴏᴍᴘʟᴇᴛᴇᴅ!</b>\n\n"

                f"👥 <b>Tᴏᴛᴀʟ Usᴇʀs:</b> "
                f"<code>{total}</code>\n\n"

                f"✅ <b>Sᴜᴄᴄᴇssғᴜʟʟʏ Sᴇɴᴛ:</b> "
                f"<code>{success}</code>\n"

                f"❌ <b>Fᴀɪʟᴇᴅ:</b> "
                f"<code>{failed}</code>\n\n"

                f"📊 <b>Cᴏᴍᴘʟᴇᴛᴇᴅ:</b> "
                f"<code>{success + failed}/{total}</code>"
            )

        except Exception:
            pass

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ============================================================
    # /clearjunk
    # ============================================================

    @app.on_message(
        filters.command("clearjunk")
        & admin_only
    )
    async def clear_junk_handler(client, message):

        if message.chat.type != ChatType.PRIVATE:
            return await message.reply_text(
                "❌ <b>This command can only be used in Bot PM.</b>"
        )

        status = await message.reply_text(
            "🧹 <b>Cʟᴇᴀɴɪɴɢ Lᴀsᴛ 200 Mᴇssᴀɢᴇs...</b>"
        )

        deleted = 0

        try:
                
            start_id = max(1, message.id - 200)
            end_id = message.id

            message_ids = list(
                range(start_id, end_id + 1)
            )

            for i in range(0, len(message_ids), 100):

                batch = message_ids[i:i + 100]

                try:
                    result = await client.delete_messages(
                        chat_id=message.chat.id,
                        message_ids=batch
                    )

                    if isinstance(result, list):
                        deleted += len(result)
                    else:
                        deleted += len(batch)

                except Exception as e:
                    logger.warning(
                        f"Clear junk batch failed: {e}"
                    )
 
            try:
                await status.delete()
            except Exception:
                pass

            try:
                await message.reply_text(
                    "🧹 <b>Cʟᴇᴀɴᴜᴘ Cᴏᴍᴘʟᴇᴛᴇ</b>\n\n"
                    f"🗑 <b>Mᴇssᴀɢᴇs Dᴇʟᴇᴛᴇᴅ:</b> "
                    f"<code>{deleted}</code>"
                )
     
            except Exception as e:
                logger.warning(
                    f"Clear junk result message failed: {e}"
                )

        except Exception as e:
            logger.exception(
                f"Clear junk error: {e}"
            )

            try:
                await status.edit_text(
                    "❌ <b>Cʟᴇᴀɴᴜᴘ Fᴀɪʟᴇᴅ</b>\n\n"
                    f"<code>{str(e)}</code>"
                )
            except Exception:
                pass

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

    # ============================================================
    # /clearjunkgroup
    # ============================================================

    @app.on_message(
        filters.command("clearjunkgroup")
        & admin_only
    )
    async def clear_junk_group_handler(client, message):

        if message.chat.type not in [
            ChatType.GROUP,
            ChatType.SUPERGROUP
        ]:
            await message.reply_text(
                "❌ <b>This command can only be used in a group.</b>"
            )
            return

        status = await message.reply_text(
            "🧹 <b>Cʟᴇᴀɴɪɴɢ Lᴀsᴛ 500 Mᴇssᴀɢᴇs...</b>"
        )

        deleted = 0

        try:
        
            start_id = max(1, message.id - 500)
            end_id = message.id
    
            message_ids = list(
                range(start_id, end_id + 1)
            )

            # Delete in batches of 100.
            for i in range(0, len(message_ids), 100):

                batch = message_ids[i:i + 100]

                try:
                    result = await client.delete_messages(
                        chat_id=message.chat.id,
                        message_ids=batch
                    )

                    if isinstance(result, list):
                        deleted += len(result)
                    else:
                        deleted += len(batch)
  
                except Exception as e:
                    logger.warning(
                        f"Clear group batch failed: {e}"
                    )

            try:
                await status.delete()
            except Exception:
                pass

            try:
                await message.reply_text(
                    "🧹 <b>Gʀᴏᴜᴘ Cʟᴇᴀɴᴜᴘ Cᴏᴍᴘʟᴇᴛᴇ</b>\n\n"
                    f"🗑 <b>Mᴇssᴀɢᴇs Dᴇʟᴇᴛᴇᴅ:</b> "
                    f"<code>{deleted}</code>"
                )

            except Exception as e:
                logger.warning(
                    f"Clear group result message failed: {e}"
            )

        except Exception as e:
            logger.exception(
                f"Clear junk group error: {e}"
            )

            try:
                await status.edit_text(
                    "❌ <b>Gʀᴏᴜᴘ Cʟᴇᴀɴᴜᴘ Fᴀɪʟᴇᴅ</b>\n\n"
                    f"<code>{str(e)}</code>"
                )
            except Exception:
                pass

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #
