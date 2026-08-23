from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import (
    PREMIUM_PLANS,
    RESULTS_PER_PAGE
)


# ============================================================
# MAIN MENU
# ============================================================

def main_buttons():

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
                    "📚 Help",
                    callback_data="help"
                ),
                InlineKeyboardButton(
                    "🏠 Home",
                    callback_data="home"
                )
            ]
        ]
    )


# ============================================================
# PREMIUM PLANS
# ============================================================

def premium_buttons():

    buttons = []

    row = []

    for amount, plan in PREMIUM_PLANS.items():

        row.append(
            InlineKeyboardButton(
                f"₹{amount} • {plan['requests']} Movies",
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
                "🏠 Home",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


# ============================================================
# SEARCH RESULTS
# ============================================================

def search_result_buttons(
    results,
    query,
    page=0,
    has_next=False
):

    buttons = []

    # --------------------------------------------------------
    # FILE BUTTONS
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
                    f"🎬 {title}",
                    callback_data=f"file_{message_id}"
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
                    f"searchpage_{page - 1}_{query[:40]}"
                )
            )
        )

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"searchpage_{page + 1}_{query[:40]}"
                )
            )
        )

    if navigation:
        buttons.append(navigation)

    # --------------------------------------------------------
    # PREMIUM
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "💎 Premium Plans",
                callback_data="premium_plans"
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


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
