from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import UPDATES_CHANNEL


# ============================================================
# GROUP WELCOME HANDLER
# ============================================================

def register_group_welcome_handlers(app):

    @app.on_message(
        filters.new_chat_members
    )
    async def bot_added_to_group(
        client,
        message
    ):

        try:

            # ------------------------------------------------
            # CHECK WHETHER THE BOT WAS ADDED
            # ------------------------------------------------

            me = await client.get_me()

            bot_added = False

            for member in message.new_chat_members:

                if member.id == me.id:

                    bot_added = True
                    break

            if not bot_added:
                return

            # ------------------------------------------------
            # GROUP INFORMATION
            # ------------------------------------------------

            chat = message.chat

            group_name = (
                chat.title
                or "this group"
            )

            # ------------------------------------------------
            # SUPPORT / UPDATES LINKS
            # ------------------------------------------------

            support_url = "https://t.me/Aero_Unity"
            updates_url = "https://t.me/Anime_UpdatesAU"

            # If UPDATES_CHANNEL is configured,
            # use it automatically.
            if UPDATES_CHANNEL:

                updates_username = (
                    UPDATES_CHANNEL
                    .replace("https://t.me/", "")
                    .replace("@", "")
                    .strip("/")
                )

                if updates_username:

                    updates_url = (
                        f"https://t.me/{updates_username}"
                    )

            # ------------------------------------------------
            # WELCOME TEXT
            # ------------------------------------------------

            text = (
                f"Thankyou For Adding Me In "
                f"{group_name} ❣️\n\n"
                "If you have any questions & doubts\n"
                "about using me contact support."
            )

            # ------------------------------------------------
            # BUTTONS
            # ------------------------------------------------

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↗ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ",
                            url=support_url
                        ),
                        InlineKeyboardButton(
                            "↗ Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ",
                            url=updates_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "↗ Bᴏᴛ Oᴡɴᴇʀ",
                            url="https://t.me/Mr_Mohammed_29"
                        )
                    ]
                ]
            )

            # ------------------------------------------------
            # SEND WELCOME
            # ------------------------------------------------

            await message.reply_text(
                text,
                reply_markup=buttons
            )

        except Exception as e:

            print(
                f"GROUP WELCOME ERROR: {e}"
            )
