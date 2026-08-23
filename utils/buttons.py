from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from config import PREMIUM_PLANS


def main_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔎 Search Movie",
                    callback_data="search"
                )
            ],
            [
                InlineKeyboardButton(
                    "💎 Premium",
                    callback_data="premium"
                ),
                InlineKeyboardButton(
                    "📊 My Plan",
                    callback_data="myplan"
                )
            ],
            [
                InlineKeyboardButton(
                    "ℹ️ Help",
                    callback_data="help"
                )
            ]
        ]
    )


def premium_buttons():

    rows = []

    for amount, plan in PREMIUM_PLANS.items():

        rows.append(
            [
                InlineKeyboardButton(
                    f"₹{amount} • {plan['requests']} Movies",
                    callback_data=f"plan_{amount}"
                )
            ]
        )

    return InlineKeyboardMarkup(
        rows
    )


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


def search_result_buttons(
    results,
    page=0
):

    buttons = []

    for item in results:

        title = item.get(
            "title",
            "Unknown"
        )

        media_id = item.get(
            "message_id"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    title[:60],
                    callback_data=f"file_{media_id}"
                )
            ]
        )

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"page_{page - 1}"
            )
        )

    if len(results) >= 10:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"page_{page + 1}"
            )
        )

    if navigation:
        buttons.append(
            navigation
        )

    return InlineKeyboardMarkup(
        buttons
    )
