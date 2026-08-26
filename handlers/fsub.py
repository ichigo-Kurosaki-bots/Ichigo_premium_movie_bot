import logging
import os

from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from pyrogram.handlers import MessageHandler
from pyrogram import StopPropagation

from config import OWNER_ID, ADMIN_IDS
from database import (
    get_fsub_channels,
    add_fsub_channel,
    remove_fsub_channel
)


logger = logging.getLogger(__name__)


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):
    return (
        user_id == OWNER_ID
        or user_id in ADMIN_IDS
    )


admin_only = filters.create(
    lambda _, __, message: (
        message.from_user is not None
        and is_admin(message.from_user.id)
    )
)


# ============================================================
# CHECK USER JOIN STATUS
# ============================================================

async def check_user_joined(
    client,
    user_id,
    channel
):

    try:

        member = await client.get_chat_member(
            channel["chat_id"],
            user_id
        )

        status = member.status

        if status in [
            enums.ChatMemberStatus.OWNER,
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.MEMBER
        ]:
            return True

        if (
            status == enums.ChatMemberStatus.RESTRICTED
            and getattr(member, "is_member", False)
        ):
            return True

        return False

    except Exception as e:

        logger.warning(
            "FSub check failed | user=%s | channel=%s | error=%s",
            user_id,
            channel.get("chat_id"),
            e
        )

        return False


# ============================================================
# CHECK ALL FSUB CHANNELS
# ============================================================

async def check_all_fsubs(
    client,
    user_id
):

    channels = await get_fsub_channels()

    not_joined = []

    for channel in channels:

        joined = await check_user_joined(
            client,
            user_id,
            channel
        )

        if not joined:
            not_joined.append(channel)

    return not_joined


# ============================================================
# FSUB KEYBOARD
# ============================================================

def build_fsub_keyboard(channels):

    buttons = []

    for channel in channels:

        title = channel.get(
            "title",
            "Join Channel"
        )

        invite_link = channel.get(
            "invite_link"
        )

        username = channel.get(
            "username"
        )

        if invite_link:

            link = invite_link

        elif username:

            username = username.lstrip("@")

            link = f"https://t.me/{username}"

        else:

            continue

        buttons.append([
            InlineKeyboardButton(
                f"• Join {title} •",
                url=link
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "• Check Again •",
            callback_data="fsub_check"
        )
    ])

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# FSUB MESSAGE
# ============================================================

async def send_fsub_message(
    client,
    message,
    channels
):

    user = message.from_user

    first_name = (
        user.first_name
        if user
        else "User"
    )

    text = (
        f"HEY <b>{first_name}</b> ♡\n\n"

        "» ‼️ <b>LOOKS LIKE YOU HAVEN'T "
        "JOINED TO OUR CHANNELS YET, "
        "SUBSCRIBE NOW...</b>\n\n"

        "» ‼️ <b>JOIN ALL CHANNELS BELOW 👇</b>"
    )

    keyboard = build_fsub_keyboard(
        channels
    )

    image = os.getenv(
        "FSUB_IMAGE_URL",
        ""
    ).strip()

    if image:

        return await message.reply_photo(
            photo=image,
            caption=text,
            reply_markup=keyboard
        )

    return await message.reply_text(
        text,
        reply_markup=keyboard
    )


# ============================================================
# /START FORCE SUBSCRIBE CHECK
# ============================================================

def register_fsub_start_handler(app):

    @app.on_message(
        filters.command("start"),
        group=-1
    )
    async def fsub_start_handler(
        client,
        message
    ):

        if not message.from_user:
            return

        user_id = message.from_user.id

        channels = await get_fsub_channels()

        # ----------------------------------------------------
        # NO FSUB CHANNELS
        # ----------------------------------------------------

        if not channels:
            return

        # ----------------------------------------------------
        # CHECK USER
        # ----------------------------------------------------

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

        # ----------------------------------------------------
        # USER JOINED EVERYTHING
        #
        # DO NOT STOP /START
        # The normal start handler will continue.
        # ----------------------------------------------------

        if not not_joined:
            return

        # ----------------------------------------------------
        # USER HAS NOT JOINED
        # ----------------------------------------------------

        await send_fsub_message(
            client,
            message,
            not_joined
        )

        # ----------------------------------------------------
        # STOP NORMAL /START HANDLER
        # ----------------------------------------------------

        raise StopPropagation


# ============================================================
# CHECK AGAIN BUTTON
# ============================================================

def register_fsub_callback_handler(app):

    @app.on_callback_query(
        filters.regex("^fsub_check$")
    )
    async def fsub_check_callback(
        client,
        callback_query
    ):

        user_id = callback_query.from_user.id

        channels = await get_fsub_channels()

        if not channels:

            await callback_query.answer(
                "✅ No Force Subscribe channels configured.",
                show_alert=True
            )

            return

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

        # ----------------------------------------------------
        # EVERYTHING JOINED
        # ----------------------------------------------------

        if not not_joined:

            await callback_query.answer(
                "✅ Subscription verified!",
                show_alert=True
            )

            try:

                await callback_query.message.delete()

            except Exception:
                pass

            # Tell user to start again so the normal
            # start handler can process the command.

            await client.send_message(
                user_id,
                "/start"
            )

            return

        # ----------------------------------------------------
        # STILL NOT JOINED
        # ----------------------------------------------------

        await callback_query.answer(
            "❌ You haven't joined all required channels.",
            show_alert=True
        )

        keyboard = build_fsub_keyboard(
            not_joined
        )

        try:

            await callback_query.message.edit_reply_markup(
                reply_markup=keyboard
            )

        except Exception:
            pass

def register_fsub_admin_handlers(app):

    @app.on_message(
        filters.command("addfsub")
        & admin_only
    )
    async def addfsub_handler(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Usage:</b>\n\n"
                "<code>/addfsub @channel</code>\n\n"
                "<b>Private channel:</b>\n"
                "<code>/addfsub -1001234567890 "
                "https://t.me/+invite</code>"
            )

            return

        target = message.command[1]

        invite_link = None

        if len(message.command) >= 3:

            invite_link = message.command[2]

        try:

            chat = await client.get_chat(
                target
            )

        except Exception as e:

            await message.reply_text(
                "❌ <b>Could not find this channel.</b>\n\n"
                "Make sure the bot is inside the channel "
                "and has the required permissions.\n\n"
                f"<code>{e}</code>"
            )

            return

        # ----------------------------------------------------
        # CHANNEL CHECK
        # ----------------------------------------------------

        if chat.type not in [
            enums.ChatType.CHANNEL,
            enums.ChatType.SUPERGROUP
        ]:

            await message.reply_text(
                "❌ Please provide a channel or group."
            )

            return

        # ----------------------------------------------------
        # PUBLIC USERNAME
        # ----------------------------------------------------

        username = getattr(
            chat,
            "username",
            None
        )

        # ----------------------------------------------------
        # INVITE LINK
        # ----------------------------------------------------

        if not invite_link and username:

            invite_link = (
                f"https://t.me/{username}"
            )

        # ----------------------------------------------------
        # PRIVATE CHANNEL
        # ----------------------------------------------------

        if not invite_link:

            try:

                invite_link = (
                    await client.export_chat_invite_link(
                        chat.id
                    )
                )

            except Exception as e:

                await message.reply_text(
                    "❌ <b>Could not create an invite link.</b>\n\n"
                    "For a private channel, send the invite link "
                    "with the command:\n\n"
                    "<code>/addfsub -1001234567890 "
                    "https://t.me/+xxxx</code>\n\n"
                    f"<code>{e}</code>"
                )

                return

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        channel_data = {

            "chat_id": chat.id,

            "title": (
                chat.title
                or "Join Channel"
            ),

            "username": username,

            "invite_link": invite_link
        }

        success = await add_fsub_channel(
            channel_data
        )

        if not success:

            await message.reply_text(
                "⚠️ This channel is already "
                "in the FSub list."
            )

            return

        await message.reply_text(
            "✅ <b>Force Subscribe Added</b>\n\n"

            f"📢 <b>Channel:</b> "
            f"{chat.title}\n"

            f"🆔 <b>ID:</b> "
            f"<code>{chat.id}</code>\n\n"

            f"🔗 <b>Link:</b> "
            f"{invite_link}"
        )


# ============================================================
# /DELFSUB
#
# /delfsub @channel
# /delfsub -1001234567890
# ============================================================

def register_fsub_delete_handler(app):

    @app.on_message(
        filters.command("delfsub")
        & admin_only
    )
    async def delfsub_handler(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Usage:</b>\n\n"
                "<code>/delfsub @channel</code>\n\n"
                "or\n\n"
                "<code>/delfsub -1001234567890</code>"
            )

            return

        target = message.command[1]

        try:

            chat = await client.get_chat(
                target
            )

            chat_id = chat.id

        except Exception:

            try:

                chat_id = int(target)

            except ValueError:

                await message.reply_text(
                    "❌ Invalid channel."
                )

                return

        removed = await remove_fsub_channel(
            chat_id
        )

        if not removed:

            await message.reply_text(
                "❌ This channel is not "
                "in the FSub list."
            )

            return

        await message.reply_text(
            "✅ <b>Force Subscribe Removed</b>\n\n"
            f"🆔 Channel ID: "
            f"<code>{chat_id}</code>"
        )


# ============================================================
# /FSUBLIST
# ============================================================

def register_fsub_list_handler(app):

    @app.on_message(
        filters.command("fsublist")
        & admin_only
    )
    async def fsublist_handler(
        client,
        message
    ):

        channels = await get_fsub_channels()

        if not channels:

            await message.reply_text(
                "📢 <b>Force Subscribe List</b>\n\n"
                "❌ No FSub channels added."
            )

            return

        text = (
            "📢 <b>FORCE SUBSCRIBE CHANNELS</b>\n\n"
        )

        for index, channel in enumerate(
            channels,
            start=1
        ):

            title = channel.get(
                "title",
                "Unknown"
            )

            username = channel.get(
                "username"
            )

            chat_id = channel.get(
                "chat_id"
            )

            text += (
                f"┎ <b>{index}. {title}</b>\n"
            )

            if username:

                text += (
                    f"┃ Username: "
                    f"@{username.lstrip('@')}\n"
                )

            text += (
                f"┖ ID: <code>{chat_id}</code>\n\n"
            )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "• ᴄʟᴏsᴇ •",
                    callback_data="fsub_close"
                )
            ]
        ])

        import os

        image = os.getenv(
            "FSUB_IMAGE_URL",
            ""
        ).strip()

        if image:

            await message.reply_photo(
                photo=image,
                caption=text,
                reply_markup=keyboard
            )

        else:

            await message.reply_text(
                text,
                reply_markup=keyboard
            )


# ============================================================
# CLOSE BUTTON
# ============================================================

def register_fsub_close_handler(app):

    @app.on_callback_query(
        filters.regex("^fsub_close$")
    )
    async def fsub_close_callback(
        client,
        callback_query
    ):

        # Only the person who used /fsublist
        # should normally close it.

        await callback_query.answer()

        try:

            await callback_query.message.delete()

        except Exception:
            pass


# ============================================================
# REGISTER EVERYTHING
# ============================================================

def register_fsub_handlers(app):

    register_fsub_start_handler(app)

    register_fsub_callback_handler(app)

    register_fsub_admin_handlers(app)

    register_fsub_delete_handler(app)

    register_fsub_list_handler(app)

    register_fsub_close_handler(app)
