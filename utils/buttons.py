# ============================================================
# utils/buttons.py
# ============================================================

from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    session_id,
    page=0,
    has_next=False,
    bot_username=None,
):
    buttons = []

    # --------------------------------------------------------
    # MOVIE / FILE BUTTONS
    # --------------------------------------------------------

    for result in results:
        message_id = (
            result.get("message_id")
            or result.get("telegram_message_id")
            or result.get("msg_id")
        )

        if not message_id:
            continue

        title = (
            result.get("title")
            or result.get("file_name")
            or result.get("filename")
            or result.get("name")
            or "Unknown File"
        )

        title = str(title).strip()

        if len(title) > 55:
            title = title[:52] + "..."

        if bot_username:
            username = str(bot_username).lstrip("@")

            url = (
                f"https://t.me/{username}"
                f"?start=file_{int(message_id)}"
            )

            buttons.append([
                InlineKeyboardButton(
                    f"›› {title}",
                    url=url,
                )
            ])

        else:
            buttons.append([
                InlineKeyboardButton(
                    f"›› {title}",
                    callback_data=f"file_{int(message_id)}",
                )
            ])

    # --------------------------------------------------------
    # SEND ALL
    # --------------------------------------------------------

    if results:

        if bot_username:
            username = str(bot_username).lstrip("@")

            sendall_url = (
                f"https://t.me/{username}"
                f"?start=sendall_{session_id}_{page}"
            )

            send_all_button = InlineKeyboardButton(
                "Sᴇɴᴅ Aʟʟ",
                url=sendall_url,
            )

        else:
            send_all_button = InlineKeyboardButton(
                "Sᴇɴᴅ Aʟʟ",
                callback_data=f"sendall_{session_id}_{page}",
            )

    else:
        send_all_button = None

    # --------------------------------------------------------
    # DIRECT FILTER BUTTONS
    #
    # Layout:
    #
    # SEND ALL | LANGUAGES | YEARS
    # QUALITY  | EPISODES  | SEASONS
    # --------------------------------------------------------

    if send_all_button:
        buttons.append([
            send_all_button,

            InlineKeyboardButton(
                "Lᴀɴɢᴜᴀɢᴇs",
                callback_data=f"filter_lang_{session_id}_{page}",
            ),

            InlineKeyboardButton(
                "Yᴇᴀʀs",
                callback_data=f"filter_year_{session_id}_{page}",
            ),
        ])

        buttons.append([
            InlineKeyboardButton(
                "Qᴜᴀʟɪᴛʏ",
                callback_data=f"filter_quality_{session_id}_{page}",
            ),

            InlineKeyboardButton(
                "Eᴘɪsᴏᴅᴇs",
                callback_data=f"filter_episode_{session_id}_{page}",
            ),

            InlineKeyboardButton(
                "Sᴇᴀsᴏɴs",
                callback_data=f"filter_season_{session_id}_{page}",
            ),
        ])

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "‹ ʙᴀᴄᴋ",
                callback_data=f"page_{session_id}_{page - 1}",
            )
        )

    if has_next:
        navigation.append(
            InlineKeyboardButton(
                "ɴᴇxᴛ ›",
                callback_data=f"page_{session_id}_{page + 1}",
            )
        )

    if navigation:
        buttons.append(navigation)

    return InlineKeyboardMarkup(buttons)


# ============================================================
# FILTER MENU
# ============================================================

def filter_menu_buttons(
    session_id,
    page=0,
    available=None,
):
    """
    Main filter menu.

    Only shows filter categories for which matching
    values actually exist.
    """

    available = available or {}

    languages = available.get(
        "languages",
        [],
    )

    years = available.get(
        "years",
        [],
    )

    seasons = available.get(
        "seasons",
        [],
    )

    episodes = available.get(
        "episodes",
        [],
    )

    buttons = []

    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    if languages:
        buttons.append([
            InlineKeyboardButton(
                "🌐 Lᴀɴɢᴜᴀɢᴇ",
                callback_data=(
                    f"filter_lang_{session_id}_{page}"
                ),
            )
        ])

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if years:
        buttons.append([
            InlineKeyboardButton(
                "📅 Yᴇᴀʀ",
                callback_data=(
                    f"filter_year_{session_id}_{page}"
                ),
            )
        ])

    # --------------------------------------------------------
    # SEASON
    # --------------------------------------------------------

    if seasons:
        buttons.append([
            InlineKeyboardButton(
                "📺 Sᴇᴀsᴏɴ",
                callback_data=(
                    f"filter_season_{session_id}_{page}"
                ),
            )
        ])

    # --------------------------------------------------------
    # EPISODE
    # --------------------------------------------------------

    if episodes:
        buttons.append([
            InlineKeyboardButton(
                "🎞 Eᴘɪsᴏᴅᴇ",
                callback_data=(
                    f"filter_episode_{session_id}_{page}"
                ),
            )
        ])

    # --------------------------------------------------------
    # CLEAR FILTERS
    # --------------------------------------------------------

    buttons.append([
        InlineKeyboardButton(
            "✖️ Cʟᴇᴀʀ Fɪʟᴛᴇʀs",
            callback_data=(
                f"filter_clear_{session_id}_{page}"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filter_back_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# LANGUAGE FILTER BUTTONS
# ============================================================

def language_filter_buttons(
    session_id,
    languages,
    page=0,
):
    buttons = []

    languages = languages or []

    row = []

    for language in languages:

        language = str(language).strip()

        if not language:
            continue

        row.append(
            InlineKeyboardButton(
                language,
                callback_data=(
                    f"setlang_{session_id}_{page}_"
                    f"{language[:30]}"
                ),
            )
        )

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "✖️ Clear Language",
            callback_data=(
                f"setlang_{session_id}_{page}_clear"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filters_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# YEAR FILTER BUTTONS
# ============================================================

def year_filter_buttons(
    session_id,
    years,
    page=0,
):
    buttons = []

    years = years or []

    row = []

    # Newest years first.
    try:
        years = sorted(
            [int(year) for year in years],
            reverse=True,
        )
    except Exception:
        pass

    for year in years:

        if not 1960 <= int(year) <= 2026:
            continue

        row.append(
            InlineKeyboardButton(
                str(year),
                callback_data=(
                    f"setyear_{session_id}_{page}_"
                    f"{int(year)}"
                ),
            )
        )

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "✖️ Clear Year",
            callback_data=(
                f"setyear_{session_id}_{page}_clear"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filters_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# SEASON FILTER BUTTONS
# ============================================================

def season_filter_buttons(
    session_id,
    seasons,
    page=0,
):
    buttons = []

    seasons = seasons or []

    try:
        seasons = sorted(
            [int(season) for season in seasons]
        )
    except Exception:
        pass

    row = []

    for season in seasons:

        if not 1 <= int(season) <= 20:
            continue

        row.append(
            InlineKeyboardButton(
                f"S{int(season):02d}",
                callback_data=(
                    f"setseason_{session_id}_{page}_"
                    f"{int(season)}"
                ),
            )
        )

        if len(row) == 4:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "✖️ Clear Season",
            callback_data=(
                f"setseason_{session_id}_{page}_clear"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filters_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# EPISODE FILTER BUTTONS
# ============================================================

def episode_filter_buttons(
    session_id,
    episodes,
    page=0,
):
    buttons = []

    episodes = episodes or []

    try:
        episodes = sorted(
            [int(episode) for episode in episodes]
        )
    except Exception:
        pass

    row = []

    for episode in episodes:

        if not 1 <= int(episode) <= 50:
            continue

        row.append(
            InlineKeyboardButton(
                f"E{int(episode):02d}",
                callback_data=(
                    f"setepisode_{session_id}_{page}_"
                    f"{int(episode)}"
                ),
            )
        )

        if len(row) == 5:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "✖️ Clear Episode",
            callback_data=(
                f"setepisode_{session_id}_{page}_clear"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filters_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# ACTIVE FILTER BUTTONS
# ============================================================

def active_filter_buttons(
    session_id,
    page=0,
    filters=None,
):
    """
    Displays currently selected filters.
    """

    filters = filters or {}

    buttons = []

    language = filters.get("language")
    year = filters.get("year")
    season = filters.get("season")
    episode = filters.get("episode")

    if language:
        buttons.append([
            InlineKeyboardButton(
                f"🌐 {language}",
                callback_data=(
                    f"setlang_{session_id}_{page}_clear"
                ),
            )
        ])

    if year:
        buttons.append([
            InlineKeyboardButton(
                f"📅 {year}",
                callback_data=(
                    f"setyear_{session_id}_{page}_clear"
                ),
            )
        ])

    if season:
        buttons.append([
            InlineKeyboardButton(
                f"📺 S{int(season):02d}",
                callback_data=(
                    f"setseason_{session_id}_{page}_clear"
                ),
            )
        ])

    if episode:
        buttons.append([
            InlineKeyboardButton(
                f"🎞 E{int(episode):02d}",
                callback_data=(
                    f"setepisode_{session_id}_{page}_clear"
                ),
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✖️ Cʟᴇᴀʀ Aʟʟ",
            callback_data=(
                f"filter_clear_{session_id}_{page}"
            ),
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "‹ Bᴀᴄᴋ",
            callback_data=(
                f"filter_back_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# PREMIUM BUTTONS
# ============================================================

def premium_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💎 Gᴇᴛ Pʀᴇᴍɪᴜᴍ",
                callback_data="premium_plans",
            )
        ],
        [
            InlineKeyboardButton(
                "💳 Rᴇᴅᴇᴇᴍ Cᴏᴅᴇ",
                callback_data="redeem",
            )
        ],
        [
            InlineKeyboardButton(
                "‹ Bᴀᴄᴋ",
                callback_data="close",
            )
        ],
    ])

# ============================================================
# PREMIUM PLAN CONFIRM BUTTONS
# ============================================================

def plan_confirm_buttons(amount):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💳 Pᴀʏ Nᴏᴡ",
                callback_data=f"pay_{amount}"
            )
        ],
        [
            InlineKeyboardButton(
                "‹ Bᴀᴄᴋ Tᴏ Pʟᴀɴs",
                callback_data="premium"
            )
        ]
    ])

# ============================================================
# FILE SENT BUTTONS
# ============================================================

def file_sent_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Uᴘᴅᴀᴛᴇs",
                url="https://t.me/Aero_Unity",
            )
        ],
    ])


# ============================================================
# OPEN BOT BUTTON
# ============================================================

def open_bot_button(
    bot_username,
    start_parameter=None,
):
    username = str(bot_username).lstrip("@")

    if start_parameter:
        url = (
            f"https://t.me/{username}"
            f"?start={start_parameter}"
        )
    else:
        url = f"https://t.me/{username}"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🤖 Oᴘᴇɴ Bᴏᴛ",
                url=url,
            )
        ]
    ])


# ============================================================
# OPEN BOT + CLOSE
# ============================================================

def open_bot_close_buttons(
    bot_username,
    start_parameter=None,
):
    username = str(bot_username).lstrip("@")

    if start_parameter:
        url = (
            f"https://t.me/{username}"
            f"?start={start_parameter}"
        )
    else:
        url = f"https://t.me/{username}"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🤖 Oᴘᴇɴ Bᴏᴛ",
                url=url,
            )
        ],
        [
            InlineKeyboardButton(
                "• Cʟᴏsᴇ •",
                callback_data="close",
            )
        ],
    ])


# ============================================================
# CLOSE BUTTON
# ============================================================

def close_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "• Cʟᴏsᴇ •",
                callback_data="close",
            )
        ]
    ])


# ============================================================
# BACK BUTTON
# ============================================================

def back_button(callback_data="close"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "‹ Bᴀᴄᴋ",
                callback_data=callback_data,
            )
        ]
    ])

# ============================================================
# ACCOUNT BUTTONS
# ============================================================

def account_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👤 Mʏ Aᴄᴄᴏᴜɴᴛ",
                callback_data="account",
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Pʀᴇᴍɪᴜᴍ",
                callback_data="premium",
            )
        ],
        [
            InlineKeyboardButton(
                "‹ Bᴀᴄᴋ",
                callback_data="close",
            )
        ],
    ])

# ============================================================
# HELP BUTTONS
# ============================================================

def help_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📖 Hᴏᴡ Tᴏ Uѕᴇ",
                callback_data="help_usage",
            )
        ],
        [
            InlineKeyboardButton(
                "🔍 Sᴇᴀʀᴄʜ Hᴇʟᴘ",
                callback_data="help_search",
            )
        ],
        [
            InlineKeyboardButton(
                "💎 Pʀᴇᴍɪᴜᴍ",
                callback_data="premium",
            )
        ],
        [
            InlineKeyboardButton(
                "‹ Bᴀᴄᴋ",
                callback_data="close",
            )
        ],
    ])

# ============================================================
# HOME BUTTONS
# ============================================================

def home_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 Sᴇᴀʀᴄ",
                callback_data="search",
            ),
            InlineKeyboardButton(
                "• Pʀᴇᴍɪᴜᴍ •",
                callback_data="premium",
            ),
        ],
        [
            InlineKeyboardButton(
                "• Uᴘᴅᴀᴛᴇs •",
                url="https://t.me/Aero_Unity",
            )
        ],
    ])


# ============================================================
# FORCE SUB BUTTONS
# ============================================================

def fsub_channel_button(
    channel_name,
    channel_url,
):
    return InlineKeyboardButton(
        f"📢 {channel_name}",
        url=channel_url,
    )


def fsub_try_again_button(
    deep_link,
):
    return InlineKeyboardButton(
        "• Tʀʏ Aɢᴀɪɴ •",
        callback_data=f"fsub_check_{deep_link}",
    )


def fsub_close_button():
    return InlineKeyboardButton(
        "• Cʟᴏsᴇ •",
        callback_data="fsub_close",
    )


# ============================================================
# FORCE SUB KEYBOARD
# ============================================================

def force_sub_buttons(
    channels=None,
    deep_link=None,
):
    buttons = []

    channels = channels or []

    for channel in channels:
        if isinstance(channel, dict):
            name = (
                channel.get("name")
                or channel.get("title")
                or channel.get("username")
                or "Join Channel"
            )

            url = (
                channel.get("url")
                or channel.get("invite_link")
                or channel.get("link")
            )

            if url:
                buttons.append([
                    fsub_channel_button(
                        name,
                        url,
                    )
                ])

        elif isinstance(channel, (list, tuple)):
            if len(channel) >= 2:
                buttons.append([
                    fsub_channel_button(
                        str(channel[0]),
                        str(channel[1]),
                    )
                ])

    if deep_link:
        buttons.append([
            fsub_try_again_button(
                deep_link
            )
        ])

    buttons.append([
        fsub_close_button()
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# PAGINATION ONLY
# ============================================================

def pagination_buttons(
    session_id,
    page=0,
    has_next=False,
):
    buttons = []
    row = []

    if page > 0:
        row.append(
            InlineKeyboardButton(
                "‹",
                callback_data=(
                    f"page_{session_id}_{page - 1}"
                ),
            )
        )

    row.append(
        InlineKeyboardButton(
            f"• {page + 1} •",
            callback_data="noop",
        )
    )

    if has_next:
        row.append(
            InlineKeyboardButton(
                "›",
                callback_data=(
                    f"page_{session_id}_{page + 1}"
                ),
            )
        )

    buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# ============================================================
# FILTER PAGE NAVIGATION
# ============================================================

def filter_page_buttons(
    session_id,
    page=0,
    has_next=False,
):
    buttons = []

    row = []

    if page > 0:
        row.append(
            InlineKeyboardButton(
                "‹",
                callback_data=(
                    f"page_{session_id}_{page - 1}"
                ),
            )
        )

    if has_next:
        row.append(
            InlineKeyboardButton(
                "›",
                callback_data=(
                    f"page_{session_id}_{page + 1}"
                ),
            )
        )

    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            "• Fɪʟᴛᴇʀs •",
            callback_data=(
                f"filters_{session_id}_{page}"
            ),
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# NO RESULTS
# ============================================================

def no_results_buttons(
    bot_username=None,
):
    buttons = []

    if bot_username:
        username = str(bot_username).lstrip("@")

        buttons.append([
            InlineKeyboardButton(
                "• Sᴇᴀʀᴄh Aɢᴀɪɴ •",
                url=f"https://t.me/{username}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "• Uᴘᴅᴀᴛᴇs •",
            url="https://t.me/Aero_Unity",
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# CALLBACK-SAFE BUTTON
# ============================================================

def noop_button(text="•"):
    return InlineKeyboardButton(
        text,
        callback_data="noop",
    )
