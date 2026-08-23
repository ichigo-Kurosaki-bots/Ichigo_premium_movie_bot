from pyrogram import (
    filters
)

from database import (
    get_user
)

from premium import (
    get_plan_text,
    get_user_plan_text
)

from utils.buttons import (
    premium_buttons,
    back_button
)


def register_premium_handlers(app):

    @app.on_message(
        filters.command(
            "plans"
        )
    )
    async def plans_handler(
        client,
        message
    ):

        await message.reply_text(
            get_plan_text(),
            reply_markup=premium_buttons()
        )


    @app.on_message(
        filters.command(
            "premium"
        )
    )
    async def premium_handler(
        client,
        message
    ):

        await message.reply_text(
            get_plan_text(),
            reply_markup=premium_buttons()
        )


    @app.on_message(
        filters.command(
            "myplan"
        )
    )
    async def myplan_handler(
        client,
        message
    ):

        user = await get_user(
            message.from_user.id
        )

        await message.reply_text(
            get_user_plan_text(user),
            reply_markup=back_button()
        )


    @app.on_callback_query(
        filters.regex(
            r"^premium$"
        )
    )
    async def premium_callback(
        client,
        callback
    ):

        await callback.message.edit_text(
            get_plan_text(),
            reply_markup=premium_buttons()
        )

        await callback.answer()


    @app.on_callback_query(
        filters.regex(
            r"^myplan$"
        )
    )
    async def myplan_callback(
        client,
        callback
    ):

        user = await get_user(
            callback.from_user.id
        )

        await callback.message.edit_text(
            get_user_plan_text(user),
            reply_markup=back_button()
        )

        await callback.answer()


    @app.on_callback_query(
        filters.regex(
            r"^plan_\d+$"
        )
    )
    async def plan_callback(
        client,
        callback
    ):

        amount = int(
            callback.data.split("_")[1]
        )

        text = (
            "💎 <b>Premium Plan Selected</b>\n\n"
            f"💰 Amount: ₹{amount}\n\n"
            "Please complete the payment and "
            "contact the bot owner with your "
            "Telegram ID.\n\n"
            f"🆔 Your ID: "
            f"<code>{callback.from_user.id}</code>"
        )

        await callback.message.edit_text(
            text,
            reply_markup=back_button()
        )

        await callback.answer()
