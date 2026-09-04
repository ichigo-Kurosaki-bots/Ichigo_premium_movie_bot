from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import UPDATES_CHANNEL
from database import register_chat


# ============================================================
# GROUP WELCOME HANDLER
# ============================================================

def register_group_welcome_handlers(app):

    @app.on_message(filters.new_chat_members)
    async def bot_added_to_group(client, message):

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

            chat_id = chat.id
            group_name = chat.title or "this group"

            # IMPORTANT:
            # Convert Pyrogram ChatType enum to a normal string
            chat_type = str(chat.type.value)

            # ------------------------------------------------
            # SAVE GROUP TO MONGODB
            # ------------------------------------------------

            await register_chat(
                chat_id=chat_id,
                chat_type=chat_type,
                title=group_name
            )

            print(
                f"GROUP REGISTERED | "
                f"TITLE={group_name} | "
                f"ID={chat_id} | "
                f"TYPE={chat_type}"
            )

            # ------------------------------------------------
            # SUPPORT / UPDATES LINKS
            # ------------------------------------------------

            support_url = "https://t.me/Coders_Grp"
            updates_url = "https://t.me/Aero_Unity"

            if UPDATES_CHANNEL:

                updates_username = (
                    str(UPDATES_CHANNEL)
                    .replace("https://t.me/", "")
                    .replace("http://t.me/", "")
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
                f"<b>Thankyou For Adding Me In "
                f"{group_name}</b> ❣️\n\n"
                "<b>If you have any questions & doubts</b>\n"
                "<b>about using me contact support.</b>"
            )

            # ------------------------------------------------
            # BUTTONS
            # ------------------------------------------------

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ •",
                            url=support_url
                        ),
                        InlineKeyboardButton(
                            "• Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ •",
                            url=updates_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "• Bᴏᴛ Oᴡɴᴇʀ •",
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
