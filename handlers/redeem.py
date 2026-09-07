import logging

from pyrogram import filters

from database import (
    create_user,
    get_redeem_code,
    redeem_code,
    activate_premium,
)

from premium import get_plan_by_amount

logger = logging.getLogger(__name__)


def register_redeem_handlers(app):

    @app.on_message(filters.command("redeem"))
    async def redeem_handler(client, message):

        # ---------------------------------------------
        # CHECK CODE PROVIDED
        # ---------------------------------------------

        if len(message.command) < 2:

            await message.reply_text(
                "🎟️ <b>Redeem Premium Code</b>\n\n"
                "Use:\n"
                "<code>/redeem CODE</code>\n\n"
                "Example:\n"
                "<code>/redeem PMB-AB12-CD34</code>"
            )

            return

        code = message.command[1].strip().upper()

        user_id = message.from_user.id

        # ---------------------------------------------
        # GET CODE
        # ---------------------------------------------

        code_data = await get_redeem_code(code)

        if not code_data:

            await message.reply_text(
                "❌ <b>Invalid Redeem Code</b>\n\n"
                "This code does not exist."
            )

            return

        # ---------------------------------------------
        # CHECK IF USED
        # ---------------------------------------------

        if code_data.get("used"):

            await message.reply_text(
                "❌ <b>Code Already Used</b>\n\n"
                "This code has already been redeemed."
            )

            return

        # ---------------------------------------------
        # GET AMOUNT
        # ---------------------------------------------

        try:

            amount = int(
                code_data.get("amount")
            )

        except (TypeError, ValueError):

            await message.reply_text(
                "❌ <b>Invalid Code</b>\n\n"
                "The amount linked to this code is invalid."
            )

            return

        # ---------------------------------------------
        # FIND PLAN
        # ---------------------------------------------

        plan = get_plan_by_amount(
            amount
        )

        if not plan:

            await message.reply_text(
                "❌ <b>Plan Not Found</b>\n\n"
                f"This code is worth ₹{amount}, "
                "but no Premium plan exists for this amount.\n\n"
                "Please contact the owner."
            )

            return

        plan_name = plan.get(
            "name",
            "Premium"
        )

        try:

            requests = int(
                plan.get(
                    "requests",
                    0
                )
            )

        except (TypeError, ValueError):

            requests = 0

        if requests <= 0:

            await message.reply_text(
                "❌ <b>Invalid Premium Plan</b>\n\n"
                "This plan has no valid movie requests."
            )

            return

        # ---------------------------------------------
        # CREATE USER IF NEEDED
        # ---------------------------------------------

        try:

            await create_user(
                user_id
            )

        except Exception as e:

            logger.warning(
                "create_user failed for %s: %s",
                user_id,
                e
            )

        # ---------------------------------------------
        # ACTIVATE PREMIUM
        # ---------------------------------------------

        try:

            activated = await activate_premium(
                user_id=user_id,
                plan_name=plan_name,
                amount=amount,
                requests=requests
            )

        except Exception as e:

            logger.error(
                "Premium activation failed: %s",
                e
            )

            await message.reply_text(
                "❌ <b>Activation Failed</b>\n\n"
                "Your code was not used.\n"
                "Please contact the owner."
            )

            return

        if not activated:

            await message.reply_text(
                "❌ <b>Activation Failed</b>\n\n"
                "Your code was not used.\n"
                "Please contact the owner."
            )

            return

        # ---------------------------------------------
        # MARK CODE AS USED
        # ---------------------------------------------

        result = await redeem_code(
            code=code,
            user_id=user_id
        )

        if not result.get("success"):

            logger.error(
                "Premium activated but code could not "
                "be marked as used: %s",
                code
            )

            await message.reply_text(
                "⚠️ <b>Premium Activated</b>\n\n"
                f"📦 Plan: <b>{plan_name}</b>\n"
                f"🎬 Requests: <b>{requests}</b>\n\n"
                "Your Premium access is active.\n"
                "Please contact the owner about the code."
            )

            return

        # ---------------------------------------------
        # SUCCESS
        # ---------------------------------------------

        await message.reply_text(
            "🎉 <b>Premium Activated!</b>\n\n"
            f"📦 Plan: <b>{plan_name}</b>\n"
            f"💰 Amount: <b>₹{amount}</b>\n"
            f"🎬 Requests: <b>{requests}</b>\n"
            f"🎟️ Code: <code>{code}</code>\n\n"
            "✅ Your Premium plan is now active.\n"
            "🍿 Enjoy the bot!"
        )
