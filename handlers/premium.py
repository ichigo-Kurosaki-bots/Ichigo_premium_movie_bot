from pyrogram import filters

from config import (
    OWNER_ID,
    ADMIN_IDS,
    PREMIUM_PLANS
)

from database import (
    get_user,
    create_user,
    activate_premium,
    remove_premium
)

from premium import (
    format_plans,
    get_plan_by_amount,
    get_user_plan_text
)

from utils.buttons import (
    premium_buttons
)


# ============================================================
# REGISTER PREMIUM HANDLERS
# ============================================================

def register_premium_handlers(app):

    # ========================================================
    # /PLANS
    # ========================================================

    @app.on_message(
        filters.command(
            [
                "plans",
                "premium"
            ]
        )
    )
    async def plans_handler(
        client,
        message
    ):

        await message.reply_text(
            format_plans(),
            reply_markup=premium_buttons()
        )


    # ========================================================
    # /MYPLAN
    # ========================================================

    @app.on_message(
        filters.command(
            "myplan"
        )
    )
    async def myplan_handler(
        client,
        message
    ):

        user_id = (
            message.from_user.id
        )

        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id,
                message.from_user.first_name,
                message.from_user.username
            )

            user = await get_user(
                user_id
            )

        await message.reply_text(
            get_user_plan_text(
                user
            )
        )


    # ========================================================
    # PREMIUM BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            "^premium_plans$"
        )
    )
    async def premium_callback(
        client,
        callback
    ):

        await callback.message.edit_text(
            format_plans(),
            reply_markup=premium_buttons()
        )

        await callback.answer()


    # ========================================================
    # OWNER: ADD PREMIUM
    #
    # Usage:
    #
    # /addpremium USER_ID AMOUNT
    #
    # Example:
    #
    # /addpremium 123456789 100
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

        if message.from_user.id not in ADMIN_IDS:

            await message.reply_text(
                "❌ <b>Access Denied</b>\n\n"
                "Only the owner/admin can activate "
                "Premium plans."
            )

            return

        if len(
            message.command
        ) < 3:

            await message.reply_text(
                "❌ <b>Invalid usage</b>\n\n"
                "Use:\n"
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

            available = ", ".join(
                f"₹{x}"
                for x in PREMIUM_PLANS.keys()
            )

            await message.reply_text(
                "❌ <b>Invalid Premium amount.</b>\n\n"
                f"Available plans:\n{available}"
            )

            return

        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id
            )

        success = await activate_premium(
            user_id=user_id,
            plan_name=plan["name"],
            amount=amount,
            requests=plan["requests"]
        )

        if not success:

            await message.reply_text(
                "❌ Failed to activate Premium."
            )

            return

        # ----------------------------------------------------
        # OWNER CONFIRMATION
        # ----------------------------------------------------

        await message.reply_text(
            "✅ <b>Premium Activated</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"📦 Plan: <b>{plan['name']}</b>\n"
            f"💰 Amount: <b>₹{amount}</b>\n"
            f"🎬 Requests: "
            f"<b>{plan['requests']}</b>"
        )

        # ----------------------------------------------------
        # NOTIFY USER
        # ----------------------------------------------------

        try:

            await client.send_message(
                user_id,

                "🎉 <b>Premium Activated!</b>\n\n"
                f"💎 Plan: <b>{plan['name']}</b>\n"
                f"💰 Amount: <b>₹{amount}</b>\n"
                f"🎬 Movie requests: "
                f"<b>{plan['requests']}</b>\n\n"
                "✅ Your Premium plan has been "
                "activated for you.\n\n"
                "You can now search for movies "
                "and request files."
            )

        except Exception as e:

            print(
                f"Could not notify user "
                f"{user_id}: {e}"
            )


    # ========================================================
    # REMOVE PREMIUM
    #
    # /removepremium USER_ID
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

        if message.from_user.id not in ADMIN_IDS:

            await message.reply_text(
                "❌ Access denied."
            )

            return

        if len(
            message.command
        ) < 2:

            await message.reply_text(
                "Use:\n"
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

        if not success:

            await message.reply_text(
                "❌ Could not remove Premium."
            )

            return

        await message.reply_text(
            "✅ <b>Premium Removed</b>\n\n"
            f"👤 User ID: "
            f"<code>{user_id}</code>"
        )

        try:

            await client.send_message(
                user_id,

                "ℹ️ <b>Premium Update</b>\n\n"
                "Your Premium plan has been "
                "removed by the administrator."
            )

        except Exception:
            pass


    # ========================================================
    # PREMIUM INFO
    #
    # /premiuminfo USER_ID
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

        if message.from_user.id not in ADMIN_IDS:

            await message.reply_text(
                "❌ Access denied."
            )

            return

        if len(
            message.command
        ) < 2:

            await message.reply_text(
                "Use:\n"
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
            "👤 <b>User Premium Information</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💎 Premium: "
            f"<b>{'Yes' if user.get('premium') else 'No'}</b>\n"
            f"📦 Plan: "
            f"<b>{user.get('plan') or 'Free'}</b>\n"
            f"💰 Paid: "
            f"<b>₹{user.get('paid_amount', 0)}</b>\n"
            f"🎬 Total plan requests: "
            f"<b>{user.get('premium_requests', 0)}</b>\n"
            f"🎟 Remaining: "
            f"<b>{user.get('remaining_requests', 0)}</b>"
        )
