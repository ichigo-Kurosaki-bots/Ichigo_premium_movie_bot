import os
import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import (
    FREE_REQUESTS
)

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

    # Your Movies Group Telegram link
    MOVIES_GROUP_URL = os.getenv(
        "MOVIES_GROUP_URL",
        "https://t.me/+YaRuf7dVB6RlZWJl"
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
                    "• ғᴇᴀᴛᴜʀᴇs •",
                    callback_data="features"
                ),
                InlineKeyboardButton(
                    "• ʜᴇʟᴘ •",
                    callback_data="help"
                )
            ],
            [
                InlineKeyboardButton(
                    "• ᴍᴏᴠɪᴇs ɢʀᴏᴜᴘ •",
                    url=MOVIES_GROUP_URL
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
        f"👋 <b>Hey {first_name.upper()} Mʏ Nᴀᴍᴇ Is Pʀᴇᴍɪᴜᴍ Mᴏᴠɪᴇ Bᴏᴛ</b>\n\n"

        "<b>I ᴀᴍ A Pᴏᴡᴇʀғᴜʟ Mᴏᴠɪᴇ Sᴇᴀʀᴄʜ Bᴏᴛ.</b> "
        "<b>ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ</b>"
        "<b>ɪ ᴡɪʟʟ ɢɪᴠᴇ ᴍᴏᴠɪᴇs ᴏʀ sᴇʀɪᴇs ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ ᴀɴᴅ ᴘᴍ !! 😍.</b>\n\n"

        f"🆓 <b>ғʀᴇᴇ ʀᴇǫᴜᴇsᴛs ʀᴇᴍᴀɪɴɪɴɢ:</b> "
        f"<b>{remaining}</b>\n\n"
        "<b>Aᴄᴛɪᴠᴀᴛᴇ Pʀᴇᴍɪᴜᴍ Aғᴛᴇʀ Yᴏᴜʀ</b> "
        "<b>ғʀᴇᴇ ʀᴇǫᴜᴇsᴛs ᴀʀᴇ ғɪɴɪsʜᴇᴅ.</b>\n\n"

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

        user = await get_user(user_id)

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

            user = await get_user(user_id)

        # ----------------------------------------------------
        # START ANIMATION
        # ----------------------------------------------------

        try:

            animation = await client.send_message(
                chat_id=user_id,
                text="⚡️"
            )

            await asyncio.sleep(0.6)

            await animation.edit_text(
                "卍解 Bᴀɴᴋᴀɪ"
            )

            await asyncio.sleep(0.6)

            await animation.edit_text(
                "Tᴇɴsᴀ Zᴀɴɢᴇᴛsᴜ"
            )

            await asyncio.sleep(0.6)

            await animation.edit_text(
                "Iᴄʜɪɢᴏ Kᴜʀᴏsᴀᴋɪ..."
            )

            await asyncio.sleep(0.6)

            await animation.delete()

        except Exception as e:

            print(
                f"START ANIMATION ERROR: {e}"
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
    # FEATURES
    # ========================================================

    @app.on_callback_query(
        filters.regex(r"^features$")
    )
    async def features_callback(
        client,
        callback
    ):

        text = (
            "⚡️ <b>Fᴇᴀᴛᴜʀᴇs</b>\n\n"

            "🎬 <b>Mᴏᴠɪᴇ Sᴇᴀʀᴄʜ</b>\n"
            "Sᴇᴀʀᴄʜ ғᴏʀ ᴍᴏᴠɪᴇs ᴀɴᴅ sᴇʀɪᴇs "
            "ғʀᴏᴍ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ.\n\n"

            "🔎 <b>Fᴀsᴛ Sᴇᴀʀᴄʜ</b>\n"
            "Fᴀsᴛ ᴀɴᴅ ᴇᴀsʏ ᴍᴇᴅɪᴀ sᴇᴀʀᴄʜ.\n\n"

            "👥 <b>Gʀᴏᴜᴘ Sᴜᴘᴘᴏʀᴛ</b>\n"
            "Uѕᴇ ᴛʜᴇ ʙᴏᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ.\n\n"

            "💎 <b>Pʀᴇᴍɪᴜᴍ</b>\n"
            "Gᴇᴛ ᴀᴅᴅɪᴛɪᴏɴᴀʟ ᴍᴏᴠɪᴇ ʀᴇǫᴜᴇsᴛs.\n\n"

            "🔥 <b>Tʀᴇɴᴅɪɴɢ</b>\n"
            "Sᴇᴇ ᴡʜᴀᴛ ᴜsᴇʀs ᴀʀᴇ sᴇᴀʀᴄʜɪɴɢ ғᴏʀ.\n\n"

            "📢 <b>Uᴘᴅᴀᴛᴇs</b>\n"
            "Sᴛᴀʏ ᴜᴘᴅᴀᴛᴇᴅ ᴡɪᴛʜ ᴛʜᴇ ʟᴀᴛᴇsᴛ ᴄᴏɴᴛᴇɴᴛ.\n\n"

            "⚡️ <b>Pᴏᴡᴇʀғᴜʟ ᴀɴᴅ ғᴀsᴛ Mᴏᴠɪᴇ Bᴏᴛ</b>"

            "🌿<b>Mᴀɪɴᴛᴀɪɴᴇᴅ ʙʏ: @Mr_Mohammed_29</b>"
        )

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "• ʜᴏᴍᴇ •",
                        callback_data="start_back"
                    )
                ]
            ]
        )

        try:

            await callback.message.edit_caption(
                caption=text,
                reply_markup=buttons
            )

        except Exception:

            try:

                await callback.message.edit_text(
                    text,
                    reply_markup=buttons
                )

            except Exception as e:

                print(
                    f"FEATURES EDIT FAILED: {e}"
                )

        await callback.answer()


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

            "<b>⍟───[ MY ᴅᴇᴛᴀɪʟꜱ ]───⍟</b>\n\n"

            "• <b>Pʀᴏɢʀᴀᴍᴇʀ: "
            "<a href=\"https://t.me/Mr_Mohammed_29\">ᴍᴏʜᴀᴍᴍᴇᴅ</a></b>\n"

            "• <b>ꜰᴏᴜɴᴅᴇʀ ᴏꜰ: "
            "<a href=\"https://t.me/Aero_Unity\">ᴀᴇʀᴏ ᴜɴɪᴛʏ</a></b>\n"

            "• <b>Lɪʙʀᴀʀʏ:</b> Pyʀᴏɢʀᴀᴍ 2.0\n"

            "• <b>Lᴀɴɢᴜᴀɢᴇ:</b> Pʏᴛʜᴏɴ 𝟹\n"

            "• <b>Dᴀᴛᴀʙᴀsᴇ:</b> ᴍᴏɴɢᴏ ᴅʙ\n"

            "• <b>ᴄʜᴀɴɴᴇʟ: "
            "<a href=\"https://t.me/Aero_Unity\">ᴀᴇʀᴏ ᴜɴɪᴛʏ</a></b>\n"

            "• <b>ᴍʏ ꜱᴇʀᴠᴇʀ:"
            "<a href=\"https://t.me/Mr_Mohammed_29\">ꜱᴇʀᴠᴇʀ</a></b>\n"
   
            "• <b>ʙᴜɪʟᴅ sᴛᴀᴛᴜs:</b> "
            "ᴠ3 [sᴛᴀʙʟᴇ]\n\n"
        )

        try:

            await callback.message.edit_caption(

                caption=text,

                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "• ʜᴏᴍᴇ •",
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
            "📚 <b>Hᴇʟᴘ & Mᴏᴠɪᴇ Rᴜʟᴇs</b>\n\n"

            "🎬 <b>Hᴏᴡ Tᴏ Sᴇᴀʀᴄʜ:</b>\n\n"

            "➤ Sᴇɴᴅ Tʜᴇ Mᴏᴠɪᴇ Oʀ Sᴇʀɪᴇs Nᴀᴍᴇ.\n\n"

            "➤ Tʜᴇ Bᴏᴛ Wɪʟʟ Sᴇᴀʀᴄʜ Mʏ Dᴀᴛᴀʙᴀsᴇ.\n\n"

            "➤ Sᴇʟᴇᴄᴛ Tʜᴇ Rᴇǫᴜɪʀᴇᴅ Fɪʟᴇ Fʀᴏᴍ Tʜᴇ Rᴇsᴜʟᴛs.\n\n"

            "⚠️ <b>Mᴏᴠɪᴇ Sᴇᴀʀᴄʜ Rᴜʟᴇs:</b>\n\n"

            "• Dᴏ Nᴏᴛ Sᴇɴᴅ Pʜᴏᴛᴏs.\n"
            "• Dᴏ Nᴏᴛ Sᴇɴᴅ Vɪᴅᴇᴏs.\n"
            "• Dᴏ Nᴏᴛ Sᴇɴᴅ Dᴏᴄᴜᴍᴇɴᴛs.\n"
            "• Dᴏ Nᴏᴛ Sᴇɴᴅ Uʀʟs.\n\n"

            "🔎 <b>Sᴇᴀʀᴄ Exᴀᴍᴘʟᴇ:</b>\n"
            "<code>Avengers Endgame</code>\n\n"

            f"🆓 Fʀᴇᴇ Rᴇǫᴜᴇsᴛs: "
            f"<b>{FREE_REQUESTS}</b>\n\n"

            "💎 Aᴄᴛɪᴠᴀᴛᴇ Pʀᴇᴍɪᴜᴍ Aғᴛᴇʀ Yᴏᴜʀ Fʀᴇᴇ Rᴇǫᴜᴇsᴛs Aʀᴇ Fɪɴɪsʜᴇᴅ."
        )

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• ʜᴏᴍᴇ •",
                            callback_data="home"
                        )
                    ]
                ]
            )
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
