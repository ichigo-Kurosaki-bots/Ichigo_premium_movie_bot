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
    get_plan_by_amount,
    get_user_plan_text,
    format_plans
)

from utils.buttons import (
    premium_buttons,
    plan_confirm_buttons,
    account_buttons,
    home_buttons
)


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):

    if user_id == OWNER_ID:
        return True

    return user_id in ADMIN_IDS


# ============================================================
# REGISTER PREMIUM HANDLERS
# ============================================================

def register_premium_handlers(app):

    # ========================================================
    # /premium
    # ========================================================

    @app.on_message(
        filters.command(
            [
                "premium",
                "plans"
            ]
        )
    )
    async def premium_command(
        client,
        message
    ):

        await message.reply_text(
            format_plans(),
            reply_markup=premium_buttons()
        )


    # ========================================================
    # /myplan
    # ========================================================

    @app.on_message(
        filters.command(
            "myplan"
        )
    )
    async def myplan_command(
        client,
        message
    ):

        user_id = message.from_user.id

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    message.from_user.first_name
                    or "User"
                ),
                username=(
                    message.from_user.username
                    or ""
                )
            )

        await message.reply_text(
            get_user_plan_text(user),
            reply_markup=account_buttons()
        )


    # ========================================================
    # PREMIUM PLAN SELECTION
    #
    # callback:
    # plan_10
    # plan_20
    # plan_50
    # etc.
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^plan_\d+$"
        )
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
                "This plan does not exist.",
                show_alert=True
            )

            return

        name = plan.get(
            "name",
            "Premium"
        )

        requests = plan.get(
            "requests",
            0
        )

        text = (
            "💎 <b>Premium Plan</b>\n\n"

            f"📦 Plan: <b>{name}</b>\n"
            f"💰 Price: <b>₹{amount}</b>\n"
            f"🎬 Requests: <b>{requests}</b>\n\n"

            "After payment, send your "
            "<b>Telegram User ID</b> to the owner.\n\n"

            "The owner will verify the payment "
            "and activate your plan."
        )

        await callback.message.edit_text(
            text,
            reply_markup=plan_confirm_buttons(
                amount
            )
        )

        await callback.answer()


    # ========================================================
    # PAYMENT INSTRUCTIONS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^pay_\d+$"
        )
    )
    async def payment_callback(
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
                "Invalid Premium plan.",
                show_alert=True
            )

            return

        name = plan.get(
            "name",
            "Premium"
        )

        requests = plan.get(
            "requests",
            0
        )

        user_id = callback.from_user.id

        text = (
            "💳 <b>Payment Instructions</b>\n\n"

            f"📦 Plan: <b>{name}</b>\n"
            f"💰 Amount: <b>₹{amount}</b>\n"
            f"🎬 Requests: <b>{requests}</b>\n\n"

            "━━━━━━━━━━━━━━━━━━\n\n"

            "👤 <b>Contact the bot owner to pay.</b>\n\n"

            "After completing the payment, "
            "send the following information to "
            "the owner:\n\n"

            f"🆔 Your Telegram ID:\n"
            f"<code>{user_id}</code>\n\n"

            f"💰 Paid amount:\n"
            f"<code>₹{amount}</code>\n\n"

            "The owner will verify your payment "
            "and activate the Premium plan."
        )

        await callback.message.edit_text(
            text,
            reply_markup=home_buttons()
        )

        await callback.answer()


    # ========================================================
    # OWNER: /addpremium
    #
    # Usage:
    #
    # /addpremium USER_ID AMOUNT
    #
    # Example:
    #
    # /addpremium 123456789 20
    # ========================================================

    @app.on_message(
        filters.command(
            "addpremium"
        )
    )
    async def addpremium_command(
        client,
        message
    ):

        admin_id = message.from_user.id

        if not is_admin(admin_id):

            await message.reply_text(
                "🚫 <b>Access denied.</b>"
            )

            return

        if len(message.command) < 3:

            await message.reply_text(
                "❌ <b>Invalid format.</b>\n\n"

                "<b>Usage:</b>\n"
                "<code>/addpremium USER_ID AMOUNT</code>\n\n"

                "<b>Example:</b>\n"
                "<code>/addpremium 123456789 20</code>"
            )

            return

        try:

            target_user_id = int(
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
                f"Available plans:\n"
                f"{available}"
            )

            return

        # ----------------------------------------------------
        # MAKE SURE USER EXISTS
        # ----------------------------------------------------

        user = await get_user(
            target_user_id
        )

        if not user:

            user = await create_user(
                user_id=target_user_id
            )

        # ----------------------------------------------------
        # ACTIVATE PLAN
        # ----------------------------------------------------

        success = await activate_premium(
            user_id=target_user_id,

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
                "❌ Failed to activate Premium."
            )

            return

        # ----------------------------------------------------
        # OWNER CONFIRMATION
        # ----------------------------------------------------

        await message.reply_text(
            "✅ <b>Premium activated!</b>\n\n"

            f"👤 User ID: "
            f"<code>{target_user_id}</code>\n"

            f"📦 Plan: "
            f"<b>{plan.get('name', 'Premium')}</b>\n"

            f"💰 Amount: "
            f"<b>₹{amount}</b>\n"

            f"🎬 Requests: "
            f"<b>{plan.get('requests', 0)}</b>"
        )

        # ----------------------------------------------------
        # USER NOTIFICATION
        # ----------------------------------------------------

        try:

            await client.send_message(
                target_user_id,

                "🎉 <b>Premium Activated!</b>\n\n"

                f"📦 Plan: "
                f"<b>{plan.get('name', 'Premium')}</b>\n"

                f"💰 Amount: "
                f"<b>₹{amount}</b>\n"

                f"🎬 Requests: "
                f"<b>{plan.get('requests', 0)}</b>\n\n"

                "✅ Your Premium plan is now active.\n"
                "You can search for movies and request files."
            )

        except Exception as e:

            print(
                f"Premium notification error: {e}"
            )


    # ========================================================
    # OWNER: /removepremium
    #
    # Usage:
    #
    # /removepremium USER_ID
    # ========================================================

    @app.on_message(
        filters.command(
            "removepremium"
        )
    )
    async def removepremium_command(
        client,
        message
    ):

        admin_id = message.from_user.id

        if not is_admin(admin_id):

            await message.reply_text(
                "🚫 <b>Access denied.</b>"
            )

            return

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Invalid format.</b>\n\n"

                "<b>Usage:</b>\n"
                "<code>/removepremium USER_ID</code>\n\n"

                "<b>Example:</b>\n"
                "<code>/removepremium 123456789</code>"
            )

            return

        try:

            target_user_id = int(
                message.command[1]
            )

        except ValueError:

            await message.reply_text(
                "❌ USER_ID must be a number."
            )

            return

        user = await get_user(
            target_user_id
        )

        if not user:

            await message.reply_text(
                "❌ User not found."
            )

            return

        success = await remove_premium(
            target_user_id
        )

        if not success:

            await message.reply_text(
                "❌ Failed to remove Premium."
            )

            return

        await message.reply_text(
            "✅ <b>Premium removed.</b>\n\n"
            f"👤 User ID: "
            f"<code>{target_user_id}</code>"
        )

        try:

            await client.send_message(
                target_user_id,

                "ℹ️ <b>Premium Removed</b>\n\n"
                "Your Premium plan has been removed "
                "by the administrator."
            )

        except Exception as e:

            print(
                f"Premium removal notification error: {e}"
        )
