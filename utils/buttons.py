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

    # Create two buttons per row.
    row = []

    for amount, plan in PREMIUM_PLANS.items():

        row.append(
            InlineKeyboardButton(
                f"₹{amount} • {plan['requests']} Movies",
                callback_data=f"plan_{amount}"
            )
        )

        if len(row) == 2:

            buttons.append(
                row
            )

            row = []

    if row:

        buttons.append(
            row
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="home"
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    page=0
):

    buttons = []

    # --------------------------------------------------------
    # FILE RESULTS
    # --------------------------------------------------------

    for item in results:

        message_id = item.get(
            "message_id"
        )

        title = item.get(
            "title"
        )

        if not title:

            title = item.get(
                "file_name",
                "Unknown File"
            )

        # Telegram button text has a practical
        # length limit, so shorten very long names.

        if len(title) > 55:

            title = (
                title[:52]
                + "..."
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎬 {title}",
                    callback_data=(
                        f"file_{message_id}"
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
                "⬅️ Previous",
                callback_data=(
                    f"page_{page - 1}"
                )
            )
        )

    if len(results) >= RESULTS_PER_PAGE:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"page_{page + 1}"
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

    return InlineKeyboardMarkup(
        buttons
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
