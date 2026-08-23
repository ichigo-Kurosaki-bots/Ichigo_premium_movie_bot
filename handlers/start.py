from pyrogram import filters

from config import FREE_REQUESTS

from database import (
    get_user,
    create_user,
    update_user
)

from premium import (
    get_user_plan_text,
    format_plans
)

from utils.buttons import (
    home_buttons,
    premium_buttons,
    account_buttons,
    help_buttons
)


def register_start_handlers(app):

    # ========================================================
    # START
    # ========================================================

    @app.on_message(
        filters.command("start")
    )
    async def start_handler(client, message):

        print(
            f"START RECEIVED from "
            f"{message.from_user.id}"
        )

        user_id = message.from_user.id

        first_name = (
            message.from_user.first_name
            or "User"
        )

        username = (
            message.from_user.username
            or ""
        )

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=first_name,
                username=username
            )

        else:

            await update_user(
                user_id=user_id,
                first_name=first_name,
                username=username
            )

            user = await get_user(
                user_id
            )

        remaining = user.get(
            "remaining_requests",
            FREE_REQUESTS
        )

        text = (
            f"👋 <b>Welcome, {first_name}!</b>\n\n"
            "🎬 <b>Premium Movie Bot</b>\n\n"
            "Send the name of a movie or series "
            "to search the database.\n\n"
            f"🆓 Free requests remaining: "
            f"<b>{remaining}</b>\n\n"
            "💎 After your free requests are finished, "
            "activate Premium to continue."
        )

        await message.reply_text(
            text,
            reply_markup=home_buttons()
        )


    # ========================================================
    # HOME
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^home$")
    )
    async def home_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    callback.from_user.first_name
                    or "User"
                ),
                username=(
                    callback.from_user.username
                    or ""
                )
            )

        remaining = user.get(
            "remaining_requests",
            FREE_REQUESTS
        )

        text = (
            "🏠 <b>Premium Movie Bot</b>\n\n"
            f"🎟 Requests remaining: "
            f"<b>{remaining}</b>\n\n"
            "🔎 Send a movie name to search."
        )

        await callback.message.edit_text(
            text,
            reply_markup=home_buttons()
        )

        await callback.answer()


    # ========================================================
    # ACCOUNT
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^my_account$")
    )
    async def account_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    callback.from_user.first_name
                    or "User"
                ),
                username=(
                    callback.from_user.username
                    or ""
                )
            )

        text = get_user_plan_text(
            user
        )

        await callback.message.edit_text(
            text,
            reply_markup=account_buttons()
        )

        await callback.answer()


    # ========================================================
    # PREMIUM PLANS
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^premium_plans$")
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
    # HELP
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^help$")
    )
    async def help_callback(
        client,
        callback
    ):

        text = (
            "📚 <b>How to use the bot</b>\n\n"
            "1️⃣ Send a movie or series name.\n\n"
            "2️⃣ The bot searches the database.\n\n"
            "3️⃣ Select the file you want.\n\n"
            f"🆓 Free users get "
            f"<b>{FREE_REQUESTS}</b> requests.\n\n"
            "💎 Activate Premium after the "
            "free requests are used."
        )

        await callback.message.edit_text(
            text,
            reply_markup=help_buttons()
        )

        await callback.answer()


    # ========================================================
    # SEARCH HELP
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^search_help$")
    )
    async def search_help_callback(
        client,
        callback
    ):

        text = (
            "🔎 <b>Search Movies</b>\n\n"
            "Send the name of the movie, series, "
            "anime, or other authorized media.\n\n"
            "<b>Example:</b>\n"
            "<code>Example Movie</code>"
        )

        await callback.message.edit_text(
            text,
            reply_markup=home_buttons()
        )

        await callback.answer()
