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
# PREMIUM PLAN BUTTONS
# ============================================================

def premium_buttons():

    buttons = []

    row = []

    for amount, plan in PREMIUM_PLANS.items():

        plan_name = plan.get(
            "name",
            "Premium"
        )

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
# SELECTED PREMIUM PLAN
# ============================================================

def plan_confirm_buttons(amount):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "• 💳 Pᴀʏᴍᴇɴᴛ Iɴsᴛʀᴜᴄᴛɪᴏɴs •",
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
# ACCOUNT BUTTONS
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
# HELP BUTTONS
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


# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    session_id,
    page=0,
    has_next=False
):

    buttons = []

    # --------------------------------------------------------
    # FILE RESULTS
    # --------------------------------------------------------

    for item in results:

        message_id = item.get(
            "message_id"
        )

        title = (
            item.get("title")
            or item.get("file_name")
            or "Unknown File"
        )

        if len(title) > 55:

            title = (
                title[:52]
                + "..."
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"• {title}",
                    callback_data=(
                        f"file_{message_id}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # SEND ALL
    # --------------------------------------------------------

    if results:

        buttons.append(
            [
                InlineKeyboardButton(
                    "• sᴇɴᴅ ᴀʟʟ •",
                    callback_data=(
                        f"sendall_"
                        f"{session_id}_"
                        f"{page}"
                    )
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
                    f"searchpage_"
                    f"{session_id}_"
                    f"{page - 1}"
                )
            )
        )

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "• ɴᴇxᴛ •",
                callback_data=(
                    f"searchpage_"
                    f"{session_id}_"
                    f"{page + 1}"
                )
            )
        )

    if navigation:

        buttons.append(
            navigation
        )

    # --------------------------------------------------------
    # PREMIUM
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "• Pʀᴇᴍɪᴜᴍ Pʟᴀɴs •",
                callback_data="premium_plans"
            )
        ]
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "• ʜᴏᴍᴇ •",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# FILE CONFIRMATION BUTTONS
# ============================================================

def file_buttons():

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
# BACK BUTTON
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
# CANCEL BUTTON
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
