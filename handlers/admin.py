import logging
import asyncio
import os
import time
import psutil
from html import escape
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from pyrogram import filters
from config import OWNER_ID, ADMIN_IDS

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

from premium import get_plan_by_amount


logger = logging.getLogger(__name__)


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

                f"┎ <b>Tᴏᴛᴀʟ Uꜱᴇʀꜱ :</b> "
                f"<b>{users:,}</b>\n"
                f"┖ <b>Tᴏᴛᴀʟ Cʜᴀᴛꜱ :</b> "
                f"<b>{chats:,}</b>\n\n"

                "┎ <b>RAM ( MEMORY ):</b>\n"
                f"┖ [{progress_bar(ram_percent)}] "
                f"<b>{ram_percent:.1f}%</b>\n\n"

                "┎ <b>CPU ( USAGE ) :</b>\n"
                f"┖ [{progress_bar(cpu_percent)}] "
                f"<b>{cpu_percent:.1f}%</b>\n\n"

                "┎ <b>DISK :</b>\n"
                f"┃ [{progress_bar(disk_percent)}] "
                f"<b>{disk_percent:.1f}%</b>\n"
                f"┃ <b>Usᴇᴅ :</b> "
                f"<b>{disk_used_gb:.2f} GB</b>\n"
                f"┃ <b>Fʀᴇᴇ :</b> "
                f"<b>{disk_free_gb:.2f} GB</b>\n"
                f"┖ <b>Tᴏᴛᴀʟ :</b> "
                f"<b>{disk_total_gb:.2f} GB</b>\n\n"

                "┎ <b>𝗗𝗔𝗧𝗔𝗕𝗔𝗦𝗘 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 :</b>\n"
                f"┃ <b>Tᴏᴛᴀʟ Fɪʟᴇs :</b> "
                f"<b>{media:,}</b>\n"
                f"┖ <b>Tᴏᴛᴀʟ Sᴛᴏʀᴀɢᴇ Usᴇᴅ :</b> "
                f"<b>{used_storage}</b>\n\n"

                f"💎 <b>Pʀᴇᴍɪᴜᴍ Usᴇʀs :</b> "
                f"<b>{premium_users:,}</b>\n\n"

                "<b>Powered By: @Aero_Unity</b>"
            )

            await message.reply_text(
                text
            )

        except Exception as e:

            logger.exception(
                "Stats error: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Could not get statistics.</b>\n\n"
                f"<code>{e}</code>"
            )


    # ========================================================
    # /user USER_ID
    # ========================================================

    @app.on_message(
        filters.command("user")
        & admin_only
    )
    async def user_handler(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Usage:</b>\n\n"
                "<code>/user USER_ID</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/user 123456789</code>"
            )

            return

        try:

            user_id = int(
                message.command[1]
            )

        except ValueError:

            await message.reply_text(
                "❌ User ID must be a number."
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

        username = user.get(
            "username",
            ""
        )

        first_name = user.get(
            "first_name",
            ""
        )

        premium = user.get(
            "premium",
            False
        )

        plan = user.get(
            "plan"
        ) or "Free"

        paid_amount = user.get(
            "paid_amount",
            0
        )

        remaining = user.get(
            "remaining_requests",
            0
        )

        used = user.get(
            "total_requests_used",
            0
        )

        text = (
            "👤 <b>User Information</b>\n\n"

            f"🆔 ID: <code>{user_id}</code>\n"
            f"👤 Name: <b>{first_name}</b>\n"
            f"🔹 Username: "
            f"<b>@{username}</b>\n"
            if username
            else
            "👤 <b>User Information</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👤 Name: <b>{first_name}</b>\n"
        )

        text += (
            f"💎 Premium: "
            f"<b>{'Yes' if premium else 'No'}</b>\n"
            f"📦 Plan: <b>{plan}</b>\n"
            f"💰 Paid: <b>₹{paid_amount}</b>\n"
            f"🎟 Remaining: <b>{remaining}</b>\n"
            f"📊 Used: <b>{used}</b>"
        )

        await message.reply_text(
            text
        )

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
                    "💎 <b>PREMIUM USERS</b>\n\n"
                    "❌ No Premium users found."
                )

                return

            # ------------------------------------------------
            # TOTAL PREMIUM USERS
            # ------------------------------------------------

            text = (
                "💎 <b>PREMIUM USERS</b>\n\n"
                f"👥 <b>Total Premium Users:</b> "
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
                    f"👤 <b>{escape(str(first_name))}</b>\n"
                    f"   🆔 <code>{user_id}</code>\n"
                )

                if username:
                    text += (
                        f"   🔹 @{escape(str(username))}\n"
                    )

                text += (
                    f"   📦 Plan: <b>{escape(str(plan))}</b>\n"
                    f"   💰 Paid: <b>₹{paid_amount}</b>\n"
                    f"   🎬 Plan Requests: "
                    f"<b>{premium_requests}</b>\n"
                    f"   🎟 Remaining: "
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
                "❌ <b>Usage:</b>\n\n"
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
            "✅ <b>Premium Activated</b>\n\n"

            f"🆔 User: "
            f"<code>{user_id}</code>\n"

            f"📦 Plan: "
            f"<b>{plan.get('name', 'Premium')}</b>\n"

            f"💰 Amount: "
            f"<b>₹{amount}</b>\n"

            f"🎬 Requests: "
            f"<b>{plan.get('requests', 0)}</b>"
        )

        try:

            await client.send_message(
                user_id,

                "🎉 <b>Your Premium is Activated!</b>\n\n"

                f"📦 Plan: "
                f"<b>{plan.get('name', 'Premium')}</b>\n"

                f"💰 Paid: "
                f"<b>₹{amount}</b>\n"

                f"🎬 Movie requests: "
                f"<b>{plan.get('requests', 0)}</b>\n\n"

                "✅ You can now search and request movies."
            )

        except Exception as e:

            logger.warning(
                "Could not notify user %s: %s",
                user_id,
                e
            )


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
            "✅ <b>Premium Deactivated</b>\n\n"
            f"🆔 User: <code>{user_id}</code>"
        )

        try:

            await client.send_message(
                user_id,

                "ℹ️ <b>Premium Deactivated</b>\n\n"
                "Your Premium access has been removed."
            )

        except Exception as e:

            logger.warning(
                "Could not notify user %s: %s",
                user_id,
                e
            )

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

        try:

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
            # RESPONSE
            # ----------------------------------------------------

            await message.reply_text(

                "📚 <b>INDEXER STATUS</b>\n\n"

                f"🎬 <b>Total Indexed Files:</b> "
                f"<b>{total_files:,}</b>\n\n"

                f"💾 <b>Total Indexed Storage:</b> "
                f"<b>{size_text}</b>\n\n"

                f"🆔 <b>Last Message ID:</b> "
                f"<code>{last_message}</code>\n\n"

                "✅ <b>Database: MongoDB</b>"
            )

        except Exception as e:

            logger.exception(
                "Indexer status error: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Could not get indexer status.</b>\n\n"
                f"<code>{e}</code>"
            )


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
                "✅ <b>Indexer position reset.</b>\n\n"
                "The next indexing run will start "
                "from the beginning."
            )

        except Exception as e:

            logger.exception(
                "Reset index error: %s",
                e
            )

            await message.reply_text(
                "❌ Failed to reset indexer."
            )


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

    # /broadcast

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
            "📢 <b>Broadcast Started...</b>\n\n"
            "⏳ Preparing broadcast..."
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
                            text=formatted_text
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
                        parse_mode="html"
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
                        parse_mode="html"
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
                        parse_mode="html"
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
                        parse_mode="html"
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
                        parse_mode="html"
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
                        parse_mode="html"
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
                        "📢 <b>Broadcasting...</b>\n\n"

                        f"👥 <b>Total Users:</b> "
                        f"<code>{total}</code>\n\n"

                        f"✅ <b>Sent:</b> "
                        f"<code>{success}</code>\n"

                        f"❌ <b>Failed:</b> "
                        f"<code>{failed}</code>\n\n"

                        f"📊 <b>Progress:</b> "
                        f"<code>{processed}/{total}</code>"
                    )

                except Exception:

                    pass

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        try:

            await status.edit_text(
                "📢 <b>Broadcast Completed!</b>\n\n"

                f"👥 <b>Total Users:</b> "
                f"<code>{total}</code>\n\n"

                f"✅ <b>Successfully Sent:</b> "
                f"<code>{success}</code>\n"

                f"❌ <b>Failed:</b> "
                f"<code>{failed}</code>\n\n"

                f"📊 <b>Completed:</b> "
                f"<code>{success + failed}/{total}</code>"
            )

        except Exception:

            pass
