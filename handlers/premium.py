from pyrogram import filters

from config import (
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
    premium_buttons,
    main_buttons
)


def register_premium_handlers(app):

    # ========================================================
    # /PLANS AND /PREMIUM
    # ========================================================

    @app.on_message(
        filters.command(
            ["plans", "premium"]
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
        filters.command("myplan")
    )
    async def myplan_handler(
        client,
        message
    ):

        user_id = message.from_user.id

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
            get_user_plan_text(user)
        )


    # ========================================================
    # PREMIUM PLANS BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex("^premium_plans$")
    )
    async def premium_plans_callback(
        client,
        callback
    ):

        await callback.message.edit_text(
            format_plans(),
            reply_markup=premium_buttons()
        )

        await callback.answer()


    # ========================================================
    # PLAN SELECTION
    #
    # callback:
    # plan_10
    # plan_20
    # plan_50
    # etc.
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^plan_\d+$")
    )
    async def plan_callback(
        client,
        callback
    ):

        try:

            amount = int(
                callback.data.split("_")[1]
            )

        except (ValueError, IndexError):

            await callback.answer(
                "Invalid plan.",
                show_alert=True
            )

            return

        plan = get_plan_by_amount(
            amount
        )

        if not plan:

            await callback.answer(
                "Plan not found.",
                show_alert=True
            )

            return

        user_id = callback.from_user.id

        # Make sure user exists.
        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id,
                callback.from_user.first_name,
                callback.from_user.username
            )

        text = (
            "💎 <b>Premium Plan</b>\n\n"

            f"📦 Plan: <b>{plan['name']}</b>\n"
            f"💰 Price: <b>₹{amount}</b>\n"
            f"🎬 Requests: "
            f"<b>{plan['requests']}</b>\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "💳 <b>How to activate</b>\n\n"

            "1️⃣ Pay the owner.\n"
            "2️⃣ Send your Telegram ID to the owner.\n"
            "3️⃣ The owner will activate your plan.\n\n"

            f"🆔 Your Telegram ID:\n"
            f"<code>{user_id}</code>\n\n"

            "After activation, you'll receive a "
            "confirmation message automatically."
        )

        await callback.message.edit_text(
            text,
            reply_markup=main_buttons()
        )

        await callback.answer()


    # ========================================================
    # OWNER: ADD PREMIUM
    #
    # /addpremium USER_ID AMOUNT
    # ========================================================

    @app.on_message(
        filters.command("addpremium")
    )
    async def add_premium_handler(
        client,
        message
    ):

        if message.from_user.id not in ADMIN_IDS:

            await message.reply_text(
                "❌ <b>Access Denied</b>"
            )

            return

        if len(message.command) < 3:

            await message.reply_text(
                "❌ <b>Usage</b>\n\n"
                "<code>/addpremium USER_ID AMOUNT</code>\n\n"
                "Example:\n"
                "<code>/addpremium 123456789 20</code>"
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
                f"₹{amount}"
                for amount in PREMIUM_PLANS
            )

            await message.reply_text(
                "❌ Invalid plan.\n\n"
                f"Available: {available}"
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
                "❌ Premium activation failed."
            )

            return

        # Owner confirmation.
        await message.reply_text(
            "✅ <b>Premium Activated</b>\n\n"
            f"👤 User: <code>{user_id}</code>\n"
            f"📦 Plan: <b>{plan['name']}</b>\n"
            f"💰 Price: <b>₹{amount}</b>\n"
            f"🎬 Requests: "
            f"<b>{plan['requests']}</b>"
        )

        # Notify the user.
        try:

            await client.send_message(
                user_id,

                "🎉 <b>Premium Activated!</b>\n\n"
                f"💎 Plan: <b>{plan['name']}</b>\n"
                f"💰 Paid: <b>₹{amount}</b>\n"
                f"🎬 Movie requests: "
                f"<b>{plan['requests']}</b>\n\n"
                "✅ Your Premium plan is now "
                "active.\n\n"
                "Use /myplan to check your remaining "
                "requests."
            )

        except Exception as e:

            print(
                f"Premium notification failed "
                f"for {user_id}: {e}"
            )


    # ========================================================
    # OWNER: REMOVE PREMIUM
    #
    # /removepremium USER_ID
    # ========================================================

    @app.on_message(
        filters.command("removepremium")
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

        if len(message.command) < 2:

            await message.reply_text(
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
            f"User: <code>{user_id}</code>"
        )

        try:

            await client.send_message(
                user_id,
                "ℹ️ Your Premium plan has been "
                "removed by the administrator."
            )

        except Exception:
            pass


    # ========================================================
    # OWNER: PREMIUM INFO
    #
    # /premiuminfo USER_ID
    # ========================================================

    @app.on_message(
        filters.command("premiuminfo")
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

        if len(message.command) < 2:

            await message.reply_text(
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
            "👤 <b>Premium Information</b>\n\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"💎 Premium: "
            f"<b>{'Yes' if user.get('premium') else 'No'}</b>\n"
            f"📦 Plan: "
            f"<b>{user.get('plan') or 'Free'}</b>\n"
            f"💰 Paid: "
            f"<b>₹{user.get('paid_amount', 0)}</b>\n"
            f"🎬 Plan requests: "
            f"<b>{user.get('premium_requests', 0)}</b>\n"
            f"🎟 Remaining: "
            f"<b>{user.get('remaining_requests', 0)}</b>"
        )
