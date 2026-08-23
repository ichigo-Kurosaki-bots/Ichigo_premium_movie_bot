import logging
import asyncio

from pyrogram import filters

from config import OWNER_ID, ADMIN_IDS

from database import (
    get_user,
    get_all_user_ids,
    count_users,
    count_premium_users,
    count_media,
    get_stats,
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

            premium_users = stats.get(
                "premium_users",
                0
            )

            media = stats.get(
                "media",
                0
            )

            await message.reply_text(
                "📊 <b>Bot Statistics</b>\n\n"

                f"👥 Total users: "
                f"<b>{users}</b>\n"

                f"💎 Premium users: "
                f"<b>{premium_users}</b>\n"

                f"🎬 Indexed files: "
                f"<b>{media}</b>"
            )

        except Exception as e:

            logger.exception(
                "Stats error: %s",
                e
            )

            await message.reply_text(
                "❌ Failed to get statistics."
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

            from database import (
                get_indexer_state
            )

            state = await get_indexer_state()

            last_message = state.get(
                "last_message_id",
                0
            )

            indexed = state.get(
                "indexed_count",
                0
            )

            await message.reply_text(
                "📚 <b>Indexer Status</b>\n\n"

                f"🆔 Last message ID: "
                f"<code>{last_message}</code>\n"

                f"🎬 Indexed files: "
                f"<b>{indexed}</b>"
            )

        except Exception as e:

            logger.exception(
                "Indexer status error: %s",
                e
            )

            await message.reply_text(
                "❌ Could not get indexer status."
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

        if len(message.command) < 2:

            await message.reply_text(
                "📢 <b>Broadcast</b>\n\n"
                "Usage:\n"
                "<code>/broadcast Your message here</code>"
            )

            return

        broadcast_text = message.text.split(
            None,
            1
        )[1]

        try:

            users = await get_all_user_ids()

        except Exception as e:

            logger.exception(
                "Could not get users for broadcast: %s",
                e
            )

            await message.reply_text(
                "❌ Failed to get users from database."
            )

            return

        if not users:

            await message.reply_text(
                "❌ No users found."
            )

            return

        status = await message.reply_text(
            "📢 <b>Broadcast Started</b>\n\n"
            f"👥 Total users: <b>{len(users)}</b>\n"
            "⏳ Sending..."
        )

        success = 0
        failed = 0

        for user_id in users:

            try:

                await client.send_message(
                    user_id,
                    broadcast_text
                )

                success += 1

            except Exception as e:

                failed += 1

                logger.warning(
                    "Broadcast failed for %s: %s",
                    user_id,
                    e
                )

            await asyncio.sleep(0.05)

        await status.edit_text(
            "✅ <b>Broadcast Completed</b>\n\n"

            f"👥 Total users: "
            f"<b>{len(users)}</b>\n"

            f"✅ Successfully sent: "
            f"<b>{success}</b>\n"

            f"❌ Failed: "
            f"<b>{failed}</b>"
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
