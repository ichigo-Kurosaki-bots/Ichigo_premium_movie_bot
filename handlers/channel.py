from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup

from config import ADMIN_IDS
from database import chats_collection


# ============================================================
# REGISTER CHANNEL HANDLER
# ============================================================

def register_channel_handlers(app):

    # ========================================================
    # /channel
    # GET LIST OF TOTAL CONNECTED GROUPS
    # ========================================================

    @app.on_message(
        filters.command("channel")
        & filters.user(list(ADMIN_IDS))
    )
    async def channel_command(
        client,
        message
    ):

        try:

            # ------------------------------------------------
            # GET CONNECTED GROUPS FROM DATABASE
            # ------------------------------------------------

            groups = []

            async for chat in chats_collection.find({}):

                chat_id = chat.get("chat_id")

                if not chat_id:
                    continue

                chat_type = str(
                    chat.get("type", "")
                ).lower()

                # Accept group / supergroup
                if chat_type in (
                    "group",
                    "supergroup"
                ):
                    groups.append(chat)

            # ------------------------------------------------
            # NO GROUPS
            # ------------------------------------------------

            if not groups:

                await message.reply_text(
                    "📋 <b>TOTAL CONNECTED GROUPS</b>\n\n"
                    "📊 <b>Total:</b> 0\n\n"
                    "❌ No connected groups found."
                )

                return

            # ------------------------------------------------
            # SORT GROUPS
            # ------------------------------------------------

            groups.sort(
                key=lambda x: str(
                    x.get("title")
                    or x.get("name")
                    or ""
                ).lower()
            )

            # ------------------------------------------------
            # BUILD LIST
            # ------------------------------------------------

            text = (
                "📋 <b>TOTAL CONNECTED GROUPS</b>\n\n"
                f"📊 <b>Total:</b> {len(groups)}\n\n"
            )

            for number, chat in enumerate(
                groups,
                start=1
            ):

                chat_id = chat.get(
                    "chat_id"
                )

                title = (
                    chat.get("title")
                    or chat.get("name")
                    or "Unknown Group"
                )

                username = chat.get(
                    "username"
                )

                if username:

                    text += (
                        f"<b>{number}. {title}</b>\n"
                        f"👤 @{username}\n"
                        f"🆔 <code>{chat_id}</code>\n\n"
                    )

                else:

                    text += (
                        f"<b>{number}. {title}</b>\n"
                        f"🆔 <code>{chat_id}</code>\n\n"
                    )

            # ------------------------------------------------
            # TELEGRAM MESSAGE LIMIT
            # ------------------------------------------------

            chunks = []

            while len(text) > 4000:

                split_at = text.rfind(
                    "\n\n",
                    0,
                    4000
                )

                if split_at == -1:
                    split_at = 4000

                chunks.append(
                    text[:split_at]
                )

                text = text[
                    split_at:
                ].lstrip()

            if text:
                chunks.append(text)

            # ------------------------------------------------
            # SEND GROUP LIST
            # ------------------------------------------------

            for chunk in chunks:

                await message.reply_text(
                    chunk
                )

        except Exception as e:

            await message.reply_text(
                "❌ <b>Failed to get connected groups.</b>\n\n"
                f"<code>{e}</code>"
            )
