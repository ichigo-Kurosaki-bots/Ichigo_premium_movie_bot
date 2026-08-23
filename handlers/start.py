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


# ============================================================
# START HANDLER
# ============================================================

def register_start_handlers(app):

    @app.on_message(
        filters.command("start")
    )
    async def start_handler(
        client,
        message
    ):

        user_id = message.from_user.id

        first_name = (
            message.from_user.first_name
            or "User"
        )

        username = (
            message.from_user.username
            or ""
        )

        # ----------------------------------------------------
        # CREATE USER IF NEW
        # ----------------------------------------------------

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

            # Keep Telegram profile information updated.
            await update_user(
                user_id=user_id,
                first_name=first_name,
                username=username
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # WELCOME MESSAGE
        # ----------------------------------------------------

        remaining = user.get(
            "remaining_requests",
            FREE_REQUESTS
        )

        text = (
            f"👋 <b>Welcome, "
            f"{first_name}!</b>\n\n"

            "🎬 <b>Premium Movie Bot</b>\n\n"

            "Search for a movie, series, anime, "
            "or other media available in our database.\n\n"

            f"🆓 Free requests remaining: "
            f"<b>{remaining}</b>\n\n"

            "🔎 <b>How to use:</b>\n"
            "Simply send the movie or series name "
            "you want to search for.\n\n"

            "💎 After your free requests are finished, "
            "you can activate Premium."
        )

        await message.reply_text(
            text,
            reply_markup=home_buttons()
        )


    # ========================================================
    # HOME CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^home$"
        )
    )
    async def home_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        first_name = (
            callback.from_user.first_name
            or "User"
        )

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=first_name,
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
            f"🏠 <b>Premium Movie Bot</b>\n\n"

            f"👤 Hello, "
            f"<b>{first_name}</b>!\n\n"

            f"🎟 Requests remaining: "
            f"<b>{remaining}</b>\n\n"

            "🔎 Send a movie or series name "
            "to search."
        )

        await callback.message.edit_text(
            text,
            reply_markup=home_buttons()
        )

        await callback.answer()


    # ========================================================
    # MY ACCOUNT
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^my_account$"
        )
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
        filters.regex(
            r"^premium_plans$"
        )
    )
    async def premium_plans_callback(
        client,
        callback
    ):

        text = format_plans()

        await callback.message.edit_text(
            text,
            reply_markup=premium_buttons()
        )

        await callback.answer()


    # ========================================================
    # HELP
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^help$"
        )
    )
    async def help_callback(
        client,
        callback
    ):

        text = (
            "📚 <b>How to use the bot</b>\n\n"

            "1️⃣ Press <b>Search Movies</b> "
            "or simply send a movie name.\n\n"

            "2️⃣ The bot searches the movie database.\n\n"

            "3️⃣ Select the file you want.\n\n"

            "4️⃣ Your request is counted when "
            "the file is delivered.\n\n"

            f"🆓 Free users get "
            f"<b>{FREE_REQUESTS}</b> requests.\n\n"

            "💎 After that, activate a Premium plan "
            "to continue using the bot.\n\n"

            "💳 Premium plans are activated by "
            "the bot owner after payment."
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
        filters.regex(
            r"^search_help$"
        )
    )
    async def search_help_callback(
        client,
        callback
    ):

        text = (
            "🔎 <b>Search Movies</b>\n\n"

            "Just send the name of the movie, "
            "series, anime, or other media.\n\n"

            "<b>Example:</b>\n"
            "<code>Avengers Endgame</code>\n\n"

            "The bot will show matching files "
            "from the database."
        )

        await callback.message.edit_text(
            text,
            reply_markup=home_buttons()
        )

        await callback.answer()


# ============================================================
# END
# ============================================================
