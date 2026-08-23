from pyrogram import filters

from database import (
    create_user,
    update_user_info
)

from utils.buttons import main_buttons

from config import FREE_REQUESTS


def register_start_handlers(app):

    @app.on_message(
        filters.command(
            "start"
        )
    )
    async def start_handler(
        client,
        message
    ):

        user = message.from_user

        if not user:
            return

        await create_user(
            user.id,
            user.first_name,
            user.username
        )

        await update_user_info(
            user.id,
            user.first_name,
            user.username
        )

        text = (
            f"👋 <b>Hello {user.first_name}!</b>\n\n"
            "🎬 Welcome to the Premium Movie Bot.\n\n"
            "🔎 Send me the name of a movie "
            "or series to search.\n\n"
            f"🆓 Free requests: "
            f"<b>{FREE_REQUESTS}</b>\n\n"
            "💎 After your free requests are "
            "finished, choose a Premium plan."
        )

        await message.reply_text(
            text,
            reply_markup=main_buttons()
        )
