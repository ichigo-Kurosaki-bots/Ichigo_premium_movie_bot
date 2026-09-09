import re

from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import PREMIUM_PLANS


# ============================================================
# HOME BUTTONS
# ============================================================

def home_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• Sᴇᴀʀᴄʜ Mᴏᴠɪᴇs •",
                    callback_data="search_help"
                )
            ],
            [
                InlineKeyboardButton(
                    "• Pʀᴇᴍɪᴜᴍ Pʟᴀɴs •",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "• Mʏ Aᴄᴄᴏᴜɴᴛ •",
                    callback_data="my_account"
                ),
                InlineKeyboardButton(
                    "• ʜᴇʟᴘ •",
                    callback_data="help"
                )
            ]
        ]
    )


# ============================================================
# START BUTTONS
# ============================================================

def start_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ᴀᴅᴅ ᴍᴇ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ •",
                    url="https://t.me/PremiumMovieBot?startgroup=true"
                )
            ],
            [
                InlineKeyboardButton(
                    "• ᴀʙᴏᴜᴛ •",
                    callback_data="about"
                ),
                InlineKeyboardButton(
                    "• ᴜᴘᴅᴀᴛᴇs •",
                    url="https://t.me/Aero_Unity"
                )
            ]
        ]
    )


# ============================================================
# PREMIUM BUTTONS
# ============================================================

def premium_buttons():

    buttons = []
    row = []

    for amount, plan in PREMIUM_PLANS.items():

        requests = plan.get(
            "requests",
            0
        )

        row.append(
            InlineKeyboardButton(
                f"₹{amount} • {requests} 🎬",
                callback_data=f"plan_{amount}"
            )
        )

        if len(row) == 2:

            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                "• ʙᴀᴄᴋ •",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# PLAN CONFIRMATION
# ============================================================

def plan_confirm_buttons(amount):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• Pᴀʏᴍᴇɴᴛ Iɴsᴛʀᴜᴄᴛɪᴏɴs •",
                    callback_data=f"pay_{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    "• Aʟʟ Pʟᴀɴs •",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "• ʜᴏᴍᴇ •",
                    callback_data="home"
                )
            ]
        ]
    )


# ============================================================
# ACCOUNT
# ============================================================

def account_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• Pʀᴇᴍɪᴜᴍ Pʟᴀɴs •",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "• ʜᴏᴍᴇ •",
                    callback_data="home"
                )
            ]
        ]
    )


# ============================================================
# HELP
# ============================================================

def help_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• Pʀᴇᴍɪᴜᴍ Pʟᴀɴs •",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "• ʜᴏᴍᴇ •",
                    callback_data="home"
                )
            ]
        ]
    )

def extract_episode_info(text):
    if not text:
        return None

    match = re.search(
        r'\bS(\d{1,3})E(\d{1,4})\b',
        str(text),
        re.IGNORECASE
    )

    if match:
        return (
            f"S{int(match.group(1)):02d}"
            f"E{int(match.group(2)):02d}"
        )

    match = re.search(
        r'\b(?:EP|EPISODE|E)[\s._-]*(\d{1,4})\b',
        str(text),
        re.IGNORECASE
    )

    if match:
        return f"EP {int(match.group(1))}"

    return None

# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    session_id,
    page=0,
    has_next=False,
    bot_username=None
):

    buttons = []

    # --------------------------------------------------------
    # FILE BUTTONS
    # --------------------------------------------------------

    for item in results:

        message_id = item.get(
            "message_id"
        )

        if not message_id:
            continue

        title = (
            item.get("title")
            or item.get("file_name")
            or "Unknown File"
        )

        title = str(title)

        if len(title) > 55:
            title = title[:52] + "..."

        # ----------------------------------------------------
        # OPEN BOT IN PM
        # ----------------------------------------------------

        if bot_username:

            file_url = (
                f"https://t.me/{bot_username}"
                f"?start=file_{message_id}"
            )

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"›› {title}",
                        url=file_url
                    )
                ]
            )

        else:

            # Fallback
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"›› {title}",
                        callback_data=f"file_{message_id}"
                    )
                ]
            )

    # --------------------------------------------------------
    # SEND ALL + PREMIUM
    # --------------------------------------------------------

    if results:

        if bot_username:

            send_all_url = (
                f"https://t.me/{bot_username}"
                f"?start=sendall_{session_id}_{page}"
            )

            send_all_button = InlineKeyboardButton(
                "• sᴇɴᴅ ᴀʟʟ •",
                url=send_all_url
            )

        else:

            send_all_button = InlineKeyboardButton(
                "• sᴇɴᴅ ᴀʟʟ •",
                callback_data=(
                    f"sendall_{session_id}_{page}"
                )
            )

        buttons.append(
            [
                send_all_button,
                InlineKeyboardButton(
                    "• Pʀᴇᴍɪᴜᴍ Pʟᴀɴs •",
                    callback_data="premium_plans"
                )
            ]
        )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "• ʙᴀᴄᴋ •",
                callback_data=(
                    f"searchpage_{session_id}_{page - 1}"
                )
            )
        )

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "• ɴᴇxᴛ •",
                callback_data=(
                    f"searchpage_{session_id}_{page + 1}"
                )
            )
        )

    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# SENT FILE BUTTONS
# ============================================================

def file_sent_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ᴜᴘᴅᴀᴛᴇs •",
                    url="https://t.me/Aero_Unity"
                )
            ]
        ]
    )


# ============================================================
# FILE BUTTONS
# ============================================================

def file_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ᴜᴘᴅᴀᴛᴇs •",
                    url="https://t.me/Aero_Unity"
                )
            ]
        ]
    )


# ============================================================
# BACK
# ============================================================

def back_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ʙᴀᴄᴋ •",
                    callback_data="home"
                )
            ]
        ]
    )


# ============================================================
# CANCEL
# ============================================================

def cancel_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• ᴄᴀɴᴄᴇʟ •",
                    callback_data="home"
                )
            ]
        ]
    )
