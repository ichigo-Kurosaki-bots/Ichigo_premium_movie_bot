import logging
import asyncio

from pyrogram import filters
from indexer import start_indexer
from config import OWNER_ID, ADMIN_IDS

from database import (
    get_user,
    get_all_user_ids,
    count_users,
    count_premium_users,
    count_media,
    count_chats,
    get_stats,
    get_media_storage_stats,
    activate_premium,
    remove_premium
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

            stats = await get_stats()

            users = stats.get(
                "users",
                0
            )

            chats = stats.get(
                "chats",
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

            free_storage = stats.get(
                "free_storage_text",
                "0.00 MB"
            )

            text = (
                f"🎬 <b>Tᴏᴛᴀʟ Fɪʟᴇs Fʀᴏᴍ Bᴏᴛʜ DBs:</b> "
                f"<b>{media:,}</b>\n\n"

               "<b>⍟─────[ Bᴏᴛ Usᴇʀs ᴀɴᴅ Cʜᴀᴛs Cᴏᴜɴᴛ ]─────⍟</b>\n\n"

               f"★ <b>Tᴏᴛᴀʟ Usᴇʀs:</b> "
               f"<b>{users:,}</b>\n"

               f"★ <b>Tᴏᴛᴀʟ Cʜᴀᴛs:</b> "
               f"<b>{chats:,}</b>\n\n"

               "<b>⍟─────[ Pʀɪᴍᴀʀʏ Dᴀᴛᴀʙᴀsᴇ Sᴛᴀᴛɪsᴛɪᴄs ]─────⍟</b>\n\n"

               f"★ <b>Tᴏᴛᴀʟ Fɪʟᴇs:</b> "
               f"<b>{media:,}</b>\n"

               f"★ <b>Usᴇᴅ Sᴛᴏʀᴀɢᴇ:</b> "
               f"<b>{used_storage}</b>\n"

               f"★ <b>Fʀᴇᴇ Sᴛᴏʀᴀɢᴇ:</b> "
               f"<b>{free_storage}</b>\n\n"

               f"💎 <b>Pʀᴇᴍɪᴜᴍ Usᴇʀs:</b> "
               f"<b>{premium_users:,}</b>\n\n"

               "<b>Powered By: @Aero_Unity</b>\n\n"

               "<b>⍟─────[ ʙᴏᴛ sᴛᴀᴛᴜ𝗌 ]─────⟟</b>"

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


    # ========================================================
    # /premiumuser USER_ID
    #
    # Same purpose as /user, but convenient for checking
    # a user's Premium status.
    # ========================================================

    @app.on_message(
        filters.command("premiumuser")
        & admin_only
    )
    async def premium_user_handler(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Usage:</b>\n"
                "<code>/premiumuser USER_ID</code>"
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

        premium = user.get(
            "premium",
            False
        )

        if not premium:

            await message.reply_text(
                "❌ This user does not currently "
                "have Premium."
            )

            return

        await message.reply_text(
            "💎 <b>Premium User</b>\n\n"

            f"🆔 ID: <code>{user_id}</code>\n"

            f"📦 Plan: "
            f"<b>{user.get('plan', 'Premium')}</b>\n"

            f"💰 Paid: "
            f"<b>₹{user.get('paid_amount', 0)}</b>\n"

            f"🎬 Total plan requests: "
            f"<b>{user.get('premium_requests', 0)}</b>\n"

            f"🎟 Remaining: "
            f"<b>{user.get('remaining_requests', 0)}</b>"
        )


    # ========================================================
    # /activate USER_ID AMOUNT
    #
    # Example:
    #
    # /activate 123456789 100
    # ========================================================

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
    # /index
    # ========================================================

    @app.on_message(
        filters.command("index")
        & admin_only
    )
    async def index_handler(
        client,
        message
    ):

        status = await message.reply_text(
            "📚 <b>Starting database indexing...</b>\n\n"
            "⏳ Please wait."
        )

        try:
            result = await start_indexer(
                client,
                force=False
            )

            if result.get("success"):

                await status.edit_text(
                    "✅ <b>Indexing Completed</b>\n\n"

                    f"📥 Scanned: "
                    f"<b>{result.get('scanned', 0)}</b>\n"

                    f"🎬 Indexed: "
                    f"<b>{result.get('indexed', 0)}</b>"
                )

            else:
  
                await status.edit_text(
                    "❌ <b>Indexing Failed</b>\n\n"

                    f"{result.get('message', 'Unknown error')}"
                )

        except Exception as e:

            logger.exception(
                "Index command error: %s",
                e
            )

            await status.edit_text(
                "❌ <b>Indexer Error</b>\n\n"
                f"<code>{e}</code>"
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
            "🆔 <b>Your Telegram ID</b>\n\n"
            f"<code>{user_id}</code>"
            )

    # ========================================================
    # /broadcast
    #
    # Usage:
    #
    # Reply to any message:
    # /broadcast
    #
    # The bot will copy that message to all users.
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
        # BROADCAST MUST BE USED AS A REPLY
        # ----------------------------------------------------

        if not message.reply_to_message:

            await message.reply_text(
                "❌ <b>Reply to a message to broadcast it.</b>\n\n"

                "Example:\n"
                "1️⃣ Send your broadcast message\n"
                "2️⃣ Reply to that message\n"
                "3️⃣ Send <code>/broadcast</code>"
            )

            return

        status = await message.reply_text(
            "📢 <b>Broadcast started...</b>\n\n"
            "⏳ Please wait."
        )

        try:

            user_ids = await get_all_user_ids()

        except Exception as e:

            logger.exception(
                "Could not get users for broadcast: %s",
                e
            )

            await status.edit_text(
                "❌ Failed to get users from database."
            )

            return

        total = len(user_ids)

        if total == 0:

            await status.edit_text(
                "❌ No users found in database."
            )

            return

        success = 0
        failed = 0

        # ----------------------------------------------------
        # SEND BROADCAST
        # ----------------------------------------------------

        for user_id in user_ids:

            try:

                await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.reply_to_message.id
                )

                success += 1

            except Exception as e:

                failed += 1

                logger.warning(
                    "Broadcast failed for %s: %s",
                    user_id,
                    e
                )

            # Small delay to reduce Telegram flood pressure.
            await asyncio.sleep(0.05)

            # Update status every 50 users.
            if (success + failed) % 50 == 0:

                try:

                    await status.edit_text(
                        "📢 <b>Broadcasting...</b>\n\n"

                        f"👥 Total users: <b>{total}</b>\n"
                        f"✅ Sent: <b>{success}</b>\n"
                        f"❌ Failed: <b>{failed}</b>\n"
                        f"📊 Progress: "
                        f"<b>{success + failed}/{total}</b>"
                    )

                except Exception:
                    pass

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        await status.edit_text(
            "📢 <b>Broadcast Completed</b>\n\n"

            f"👥 Total users: <b>{total}</b>\n"
            f"✅ Successfully sent: <b>{success}</b>\n"
            f"❌ Failed: <b>{failed}</b>"
        )
