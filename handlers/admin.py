from pyrogram import filters

from database import (
    get_user,
    activate_premium,
    remove_premium,
    count_users,
    count_media,
    count_premium_users
)

from premium import (
    get_plan_by_amount
)

from config import (
    OWNER_ID,
    ADMIN_IDS
)

from indexer import index_channel

def is_admin(user_id):

    return user_id in ADMIN_IDS


def register_admin_handlers(app):

    # ========================================================
    # ADD PREMIUM
    # ========================================================

    @app.on_message(
        filters.command(
            "addpremium"
        )
    )
    async def add_premium_handler(
        client,
        message
    ):

        if not is_admin(
            message.from_user.id
        ):

            await message.reply_text(
                "❌ You are not authorized."
            )

            return

        if len(
            message.command
        ) != 3:

            await message.reply_text(
                "Usage:\n"
                "<code>/addpremium USER_ID AMOUNT</code>\n\n"
                "Example:\n"
                "<code>/addpremium 123456789 100</code>"
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
                "❌ USER_ID and AMOUNT "
                "must be numbers."
            )

            return

        plan = get_plan_by_amount(
            amount
        )

        if not plan:

            await message.reply_text(
                "❌ Invalid premium amount.\n\n"
                "Available plans:\n"
                "₹10\n"
                "₹20\n"
                "₹50\n"
                "₹100\n"
                "₹200\n"
                "₹500\n"
                "₹1000"
            )

            return

        user = await get_user(
            user_id
        )

        if not user:

            await message.reply_text(
                "❌ User not found.\n\n"
                "Ask the user to start the bot "
                "first using /start."
            )

            return

        activated = await activate_premium(
            user_id=user_id,
            plan_name=plan["name"],
            amount=amount,
            requests=plan["requests"]
        )

        if not activated:

            await message.reply_text(
                "❌ Premium activation failed."
            )

            return

        await message.reply_text(
            "✅ <b>Premium Activated</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📦 Plan: <b>{plan['name']}</b>\n"
            f"💰 Amount: ₹{amount}\n"
            f"🎬 Requests: "
            f"<b>{plan['requests']}</b>"
        )

        # Notify user.
        try:

            await client.send_message(
                user_id,
                "🎉 <b>Premium Activated!</b>\n\n"
                f"📦 Plan: <b>{plan['name']}</b>\n"
                f"💰 Paid: ₹{amount}\n"
                f"🎬 Movie requests: "
                f"<b>{plan['requests']}</b>\n\n"
                "Your Premium plan is now active.\n"
                "You can start searching movies! 🍿"
            )

        except Exception as e:

            print(
                f"Could not notify user "
                f"{user_id}: {e}"
            )

    # ========================================================
    # INDEX DATABASE CHANNEL
    # ========================================================

    @app.on_message(
        filters.command("index")
    )
    async def index_handler(
        client,
        message
    ):

        if message.from_user.id not in ADMIN_IDS:

            await message.reply_text(
                "❌ You are not authorized."
            )

            return

        status = await message.reply_text(
            "🔄 <b>Indexing started...</b>\n\n"
            "Please wait while the bot scans "
            "the database channel."
        )

        try:

            count = await index_channel(
                client
            )

            await status.edit_text(
                "✅ <b>Indexing Completed</b>\n\n"
                f"🎬 Files indexed: <b>{count}</b>\n\n"
                "You can now search the database."
            )

        except Exception as e:

            print(
                f"Indexing error: {e}"
            )

            await status.edit_text(
                "❌ <b>Indexing Failed</b>\n\n"
                f"<code>{str(e)[:1000]}</code>"
            )


    # ========================================================
    # REMOVE PREMIUM
    # ========================================================

    @app.on_message(
        filters.command(
            "removepremium"
        )
    )
    async def remove_premium_handler(
        client,
        message
    ):

        if not is_admin(
            message.from_user.id
        ):

            return

        if len(
            message.command
        ) != 2:

            await message.reply_text(
                "Usage:\n"
                "<code>/removepremium USER_ID</code>"
            )

            return

        try:

            user_id = int(
                message.command[1]
            )

        except ValueError:

            await message.reply_text(
                "❌ Invalid user ID."
            )

            return

        success = await remove_premium(
            user_id
        )

        if success:

            await message.reply_text(
                "✅ Premium removed from "
                f"<code>{user_id}</code>."
            )

            try:

                await client.send_message(
                    user_id,
                    "⚠️ Your Premium plan "
                    "has been deactivated."
                )

            except Exception:
                pass

        else:

            await message.reply_text(
                "❌ User not found."
            )


    # ========================================================
    # USER PLAN CHECK
    # ========================================================

    @app.on_message(
        filters.command(
            "premiuminfo"
        )
    )
    async def premium_info_handler(
        client,
        message
    ):

        if not is_admin(
            message.from_user.id
        ):

            return

        if len(
            message.command
        ) != 2:

            await message.reply_text(
                "Usage:\n"
                "<code>/premiuminfo USER_ID</code>"
            )

            return

        try:

            user_id = int(
                message.command[1]
            )

        except ValueError:

            await message.reply_text(
                "❌ Invalid user ID."
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

        await message.reply_text(
            "👤 <b>User Information</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"👤 Name: "
            f"{user.get('first_name', '')}\n"
            f"📦 Premium: "
            f"{user.get('premium', False)}\n"
            f"💎 Plan: "
            f"{user.get('plan', 'None')}\n"
            f"💰 Paid: "
            f"₹{user.get('paid_amount', 0)}\n"
            f"🎬 Remaining: "
            f"{user.get('remaining_requests', 0)}\n"
            f"📊 Used: "
            f"{user.get('used_requests', 0)}"
        )


    # ========================================================
    # BOT STATS
    # ========================================================

    @app.on_message(
        filters.command(
            "stats"
        )
    )
    async def stats_handler(
        client,
        message
    ):

        if not is_admin(
            message.from_user.id
        ):

            return

        users = await count_users()

        media = await count_media()

        premium_users = (
            await count_premium_users()
        )

        await message.reply_text(
            "📊 <b>Bot Statistics</b>\n\n"
            f"👥 Users: <b>{users}</b>\n"
            f"💎 Premium Users: "
            f"<b>{premium_users}</b>\n"
            f"🎬 Indexed Files: "
            f"<b>{media}</b>"
        )
