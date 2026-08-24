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
                    "🔎 Search Movies",
                    callback_data="search_help"
                )
            ],
            [
                InlineKeyboardButton(
                    "💎 Premium Plans",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "👤 My Account",
                    callback_data="my_account"
                ),
                InlineKeyboardButton(
                    "📚 Help",
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
                "⬅️ Back",
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
                    "💳 Payment Instructions",
                    callback_data=f"pay_{amount}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ All Plans",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Home",
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
                    "💎 Premium Plans",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Home",
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
                    "💎 Premium Plans",
                    callback_data="premium_plans"
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Home",
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

            title = title[:52] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    f"• {title}",
                    callback_data=f"file_{message_id}"
                )
            ]
        )

    # --------------------------------------------------------
    # SEND ALL + PREMIUM
    # --------------------------------------------------------

    if results:

        buttons.append(
            [
                InlineKeyboardButton(
                    "📤 SEND ALL",
                    callback_data=(
                        f"sendall_{session_id}_{page}"
                    )
                ),
                InlineKeyboardButton(
                    "💎 PREMIUM",
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
                "⬅️ Previous",
                callback_data=(
                    f"searchpage_{session_id}_{page - 1}"
                )
            )
        )

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"searchpage_{session_id}_{page + 1}"
                )
            )
        )

    if navigation:

        buttons.append(
            navigation
        )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# SENT FILE BUTTON
# ============================================================

def file_sent_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 UPDATES",
                    url="https://t.me/Anime_UpdatesAU"
                )
            ]
        ]
    )


# ============================================================
# FILE CONFIRMATION BUTTONS
# ============================================================

def file_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 UPDATES",
                    url="https://t.me/Anime_UpdatesAU"
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
                    "⬅️ Back",
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
                    "❌ Cancel",
                    callback_data="home"
                )
            ]
        ]
    )
