import os

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

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
# START IMAGE URL
# ============================================================
#
# Add START_IMAGE in Render Environment Variables.
#
# Example:
# START_IMAGE=https://example.com/naruto.jpg
#
# ============================================================

START_IMAGE = os.getenv(
    "START_IMAGE",
    ""
)


# ============================================================
# UPDATES CHANNEL
# ============================================================

UPDATES_URL = os.getenv(
    "UPDATES_URL",
    "https://t.me/Aero_Unity"
)


# ============================================================
# START BUTTONS
# ONLY THESE 3 BUTTONS
# ============================================================

def start_buttons(bot_username):

    add_group_url = (
        f"https://t.me/{bot_username}"
        f"?startgroup=true"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ •",
                    url=add_group_url
                )
            ],
            [
                InlineKeyboardButton(
                    "• ᴀʙᴏᴜᴛ •",
                    callback_data="start_about"
                ),
                InlineKeyboardButton(
                    "• ᴜᴘᴅᴀᴛᴇs •",
                    url=UPDATES_URL
                )
            ]
        ]
    )


# ============================================================
# START TEXT
# ============================================================

def build_start_text(
    first_name,
    remaining
):

    return (
        f"👋 <b>Hey {first_name.upper()}</b>\n\n"

        "<b>MY NAME IS PREMIUM MOVIE BOT 🎬</b>\n\n"

        "<b>I AM A POWERFUL MOVIE SEARCH BOT.</b> "
        "<b>YOU CAN USE ME IN YOUR GROUP TO </b>"
        "<b>SEARCH MOVIES, SERIES AND MORE. 🤩</b>\n\n"

        f"🆓 <b>FREE REQUESTS REMAINING:</b> "
        f"<b>{remaining}</b>\n\n"

        "<b> ACTIVATE PREMIUM AFTER YOUR</b> "
        "<b>FREE REQUESTS ARE FINISHED.</b>\n\n"

        "🌿<b>Mᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ: @Mr_Mohammed_29</b>"
    )

# ============================================================
# REGISTER START HANDLERS
# ============================================================

def register_start_handlers(app):

    # ========================================================
    # START
    # ========================================================

    @app.on_message(
        filters.command("start")
    )
    async def start_handler(
        client,
        message
    ):

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

        # ----------------------------------------------------
        # GET / CREATE USER
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

            await update_user(
                user_id=user_id,
                first_name=first_name,
                username=username
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # REQUEST BALANCE
        # ----------------------------------------------------

        remaining = user.get(
            "remaining_requests",
            FREE_REQUESTS
        )

        # ----------------------------------------------------
        # GET BOT USERNAME
        # ----------------------------------------------------

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        # ----------------------------------------------------
        # START TEXT
        # ----------------------------------------------------

        text = build_start_text(
            first_name=first_name,
            remaining=remaining
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        reply_markup = start_buttons(
            bot_username=bot_username
        )

        # ----------------------------------------------------
        # SEND IMAGE + TEXT
        # ----------------------------------------------------

        if START_IMAGE:

            try:

                await message.reply_photo(
                    photo=START_IMAGE,
                    caption=text,
                    reply_markup=reply_markup
                )

                return

            except Exception as e:

                print(
                    f"START IMAGE SEND FAILED: {e}"
                )

        # ----------------------------------------------------
        # FALLBACK IF IMAGE URL IS MISSING/BROKEN
        # ----------------------------------------------------

        await message.reply_text(
            text,
            reply_markup=reply_markup
        )


    # ========================================================
    # ABOUT
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^start_about$")
    )
    async def start_about_callback(
        client,
        callback
    ):

        text = (
            "ℹ️ <b>ABOUT PREMIUM MOVIE BOT</b>\n\n"

            "🎬 <b>Premium Movie Bot</b>\n\n"

            "🔎 Search for movies and series "
            "from our database.\n\n"

            "📦 Select the file you want "
            "from the search results.\n\n"

            "💎 Premium plans are available "
            "for additional requests.\n\n"

            "⚡ Fast Search • Easy To Use • "
            "Powerful Database\n\n"

            "🌿 <b>Powered by @Aero_Unity</b>"
        )

        try:

            await callback.message.edit_caption(
                caption=text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "⬅️ Back",
                                callback_data="start_back"
                            )
                        ]
                    ]
                )
            )

        except Exception as e:

            print(
                f"ABOUT EDIT FAILED: {e}"
            )

        await callback.answer()


    # ========================================================
    # BACK FROM ABOUT
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^start_back$")
    )
    async def start_back_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        first_name = (
            callback.from_user.first_name
            or "User"
        )

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GET BOT USERNAME
        # ----------------------------------------------------

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        # ----------------------------------------------------
        # START TEXT
        # ----------------------------------------------------

        text = build_start_text(
            first_name=first_name,
            remaining=remaining
        )

        # ----------------------------------------------------
        # RESTORE START SCREEN
        # ----------------------------------------------------

        try:

            await callback.message.edit_caption(
                caption=text,
                reply_markup=start_buttons(
                    bot_username=bot_username
                )
            )

        except Exception as e:

            print(
                f"START BACK FAILED: {e}"
            )

        await callback.answer()


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
            "<b>Pʀᴇᴍɪᴜᴍ Mᴏᴠɪᴇ Bᴏᴛ</b>\n\n"
            f"🎟 ғʀᴇᴇ ʀᴇǫᴜᴇsᴛs ʀᴇᴍᴀɪɴɪɴɢ: "
            f"<b>{remaining}</b>\n\n"
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
