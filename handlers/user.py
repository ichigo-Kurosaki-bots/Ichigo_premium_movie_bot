from pyrogram import filters

from database import (
    create_user,
    get_user,
    count_users,
    count_media,
    count_premium_users
)

from premium import (
    get_user_plan_text,
    get_plan_text
)

from utils.buttons import (
    main_buttons,
    premium_buttons
)


def register_user_handlers(app):

    # ========================================================
    # HELP
    # ========================================================

    @app.on_message(
        filters.command("help")
    )
    async def help_handler(
        client,
        message
    ):

        text = (
            "📚 <b>Help</b>\n\n"
            "🔎 <b>Search</b>\n"
            "Send a movie or series name.\n\n"
            "💎 <b>Premium</b>\n"
            "/plans - View Premium plans\n"
            "/premium - View Premium plans\n"
            "/myplan - View your account\n\n"
            "ℹ️ <b>Other</b>\n"
            "/id - Show your Telegram ID\n"
            "/about - About this bot\n"
            "/stats - Your request statistics"
        )

        await message.reply_text(
            text,
            reply_markup=main_buttons()
        )


    # ========================================================
    # ID
    # ========================================================

    @app.on_message(
        filters.command("id")
    )
    async def id_handler(
        client,
        message
    ):

        user = message.from_user

        await message.reply_text(
            "🆔 <b>Your Telegram ID</b>\n\n"
            f"<code>{user.id}</code>"
        )


    # ========================================================
    # ABOUT
    # ========================================================

    @app.on_message(
        filters.command("about")
    )
    async def about_handler(
        client,
        message
    ):

        await message.reply_text(
            "🎬 <b>Premium Movie Bot</b>\n\n"
            "A Telegram media search bot "
            "for an authorized media library.\n\n"
            "🔎 Search\n"
            "💎 Premium plans\n"
            "📊 Request tracking\n"
            "⚡ Fast Telegram delivery"
        )


    # ========================================================
    # USER STATS
    # ========================================================

    @app.on_message(
        filters.command("stats")
    )
    async def user_stats_handler(
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
            "📊 <b>Your Statistics</b>\n\n"
            f"🎬 Total requests: "
            f"<b>{user.get('total_requests', 0)}</b>\n"
            f"🎟 Used: "
            f"<b>{user.get('used_requests', 0)}</b>\n"
            f"🎬 Remaining: "
            f"<b>{user.get('remaining_requests', 0)}</b>\n"
            f"💎 Premium: "
            f"<b>{'Yes' if user.get('premium') else 'No'}</b>"
        )


    # ========================================================
    # HOME CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex("^home$")
    )
    async def home_callback(
        client,
        callback
    ):

        await callback.message.edit_text(
            "🏠 <b>Premium Movie Bot</b>\n\n"
            "🔎 Search for a movie or series.\n"
            "💎 Upgrade to Premium when needed.",
            reply_markup=main_buttons()
        )

        await callback.answer()


    # ========================================================
    # HELP CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex("^help$")
    )
    async def help_callback(
        client,
        callback
    ):

        await callback.message.edit_text(
            "📚 <b>Help</b>\n\n"
            "Send a movie or series name "
            "to search the database.\n\n"
            "💎 Use Premium to increase "
            "your request limit.",
            reply_markup=main_buttons()
        )

        await callback.answer()
