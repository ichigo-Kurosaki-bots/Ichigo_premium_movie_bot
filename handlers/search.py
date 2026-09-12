import asyncio
import logging
import re
import time

from html import escape as html_escape

from pyrogram import filters, enums
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import (
    RESULTS_PER_PAGE,
    MAX_RESULTS,
    UPDATES_CHANNEL, 
    DATABASE_CHANNEL_ID
)

UPDATES_URL = "https://t.me/Aero_Unity"

from database import (
    get_user,
    create_user,
    search_media,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    get_search_session_filters,
    delete_search_session,
    get_filter_options,
    get_media_by_message,
    consume_request,
    restore_request,
    can_make_request,
    record_search
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message
)

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

SEARCH_PAGE_SIZE = int(
    RESULTS_PER_PAGE or 10
)

MAX_SEARCH_RESULTS = int(
    MAX_RESULTS or 50
)

# ============================================================
# QUERY HELPERS
# ============================================================

def clean_query(query):

    if query is None:
        return ""

    query = str(query).strip()

    query = re.sub(
        r"\s+",
        " ",
        query
    )

    return query

def normalize_query(query):

    query = clean_query(query)

    return query.lower()

def escape_regex(text):

    return re.escape(
        str(text)
    )

def create_search_patterns(query):

    query = clean_query(query)

    if not query:
        return []

    words = query.split()

    patterns = []

    for word in words:

        if len(word) >= 2:

            patterns.append(
                re.escape(word)
            )

    if not patterns:
        patterns.append(
            re.escape(query)
        )

    return patterns

# ============================================================
# RESULT HELPERS
# ============================================================

def get_result_title(result):
    """
    Build search result button title.

    Example:
    [450 MB] [720p] Reacher 2026 S04E01 TRUE
    """

    if not result:
        return "Unknown File"

    file_size = result.get("file_size")

    size_text = ""

    if file_size is not None:
        try:
            size_bytes = int(file_size)

            if size_bytes >= 1024 * 1024 * 1024:
                size_text = (
                    f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
                )

            elif size_bytes >= 1024 * 1024:
                size_text = (
                    f"{size_bytes / (1024 * 1024):.0f} MB"
                )

            elif size_bytes >= 1024:
                size_text = (
                    f"{size_bytes / 1024:.0f} KB"
                )

        except (TypeError, ValueError):
            pass

    quality_text = get_result_quality(result)

    title = (
        result.get("title")
        or result.get("file_name")
        or result.get("filename")
        or result.get("name")
        or result.get("caption")
        or "Unknown File"
    )

    title = str(title).strip()

    title = re.sub(
        r"\s*\|\s*\d{3,4}p\s*",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\s*\|\s*\d+(?:\.\d+)?\s*(?:MB|GB|KB)\s*$",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()

    title = re.sub(
        r"\bS(\d{1,2})\s+E(\d{1,3})\b",
        lambda m: f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}",
        title,
        flags=re.IGNORECASE
    )

    parts = []

    if size_text:
        parts.append(f"[{size_text}]")

    if quality_text:
        parts.append(f"[{quality_text}]")

    parts.append(title)

    return " | ".join(parts)

def extract_year_from_result(result):
    title = get_result_title(result)

    match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        title
    )

    if match:
        return match.group(1)

    return "—"

def get_result_message_id(result):

    value = result.get(
        "message_id"
    )

    try:
        return int(value)
    except Exception:
        return None

def get_result_language(result):

    value = result.get(
        "language"
    )

    if value is None:
        return ""

    return str(value).strip()

def get_result_year(result):

    if not result:
        return ""

    # Check database fields
    value = (
        result.get("year")
        or result.get("release_year")
        or result.get("releaseYear")
    )

    if value:
        return str(value).strip()

    # Check nested data
    data = result.get("data")

    if isinstance(data, dict):

        value = (
            data.get("year")
            or data.get("release_year")
            or data.get("releaseYear")
        )

        if value:
            return str(value).strip()

    # Extract year from title / filename / caption
    text = " ".join(
        str(result.get(key, "") or "")
        for key in [
            "title",
            "file_name",
            "filename",
            "name",
            "caption"
        ]
    )

    match = re.search(
        r"\b(19\d{2}|20\d{2})\b",
        text
    )

    if match:
        return match.group(1)

    return ""

    # Try to detect rating from title/caption
    text = " ".join(
        str(result.get(key, "") or "")
        for key in [
            "title",
            "file_name",
            "filename",
            "name",
            "caption"
        ]
    )

    match = re.search(
        r"\b(?:IMDb?\s*)?([0-9](?:\.[0-9])?)\s*(?:/10)?\b",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return ""

def get_result_quality(result):

    # Check database fields first
    quality = (
        result.get("quality")
        or result.get("video_quality")
        or result.get("resolution")
        or result.get("video_resolution")
    )

    if quality:
        return str(quality).strip()

    # If quality is not stored separately,
    # detect it from the file title/name/caption
    text = " ".join(
        str(result.get(key, "") or "")
        for key in [
            "title",
            "file_name",
            "filename",
            "name",
            "caption",
        ]
    )

    patterns = [
        r"\b(HDRip)\b",
        r"\b(4k)\b",
        r"\b(2160p)\b",
        r"\b(1440p)\b",
        r"\b(1080p)\b",
        r"\b(720p)\b",
        r"\b(576p)\b",
        r"\b(480p)\b",
        r"\b(360p)\b",
        r"\b(240p)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return ""

def format_file_size(size):

    try:
        size = int(size)
    except Exception:
        return ""

    if size <= 0:
        return ""

    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

    return f"{size / (1024 * 1024):.0f} MB"


def get_result_file_size(result):

    value = (
        result.get("file_size")
        or result.get("filesize")
        or result.get("size")
        or 0
    )

    return format_file_size(value)

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

    for index, result in enumerate(
        results,
        start=1
    ):

        message_id = get_result_message_id(
            result
        )

        if message_id is None:
            continue

        title = get_result_title(
            result
        )
        
        title = title[:55]

        button_text = f"›› {title}"
        
        buttons.append(
            [
                InlineKeyboardButton(
                    button_text,
                    callback_data=(
                        f"file_{session_id}_"
                        f"{message_id}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # SEND ALL + NEXT
    # --------------------------------------------------------

    if results:

        send_all_button = InlineKeyboardButton(
            "• Sᴇɴᴅ Aʟʟ •",
            callback_data=(
                f"sendall_{session_id}_"
                f"{page}"
            )
        )

        next_button = InlineKeyboardButton(
            "• Nᴇxᴛ •",
            callback_data=(
                f"search_page_"
                f"{session_id}_"
                f"{page + 1}"
            )
        )

        if has_next:

            buttons.append(
                [
                    send_all_button,
                    next_button
                ]
            )

        else:

            buttons.append(
                [
                    send_all_button
                ]
            )

    # --------------------------------------------------------
    # FILTER BUTTON
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "• ғɪʟᴛᴇʀs •",
                callback_data=(
                    f"filters_{session_id}_"
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
                    f"search_page_"
                    f"{session_id}_"
                    f"{page - 1}"
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
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page=0,
    has_next=False,
    filters_data=None,
    search_time=0,
    requested_by_id=None,
    requested_by_name="User"
):
    start = page * SEARCH_PAGE_SIZE + 1
    end = start + len(results) - 1

    # Get metadata from first result
    first_result = results[0] if results else {}

    title = query.strip()

    year = get_result_year(first_result) or "—"

    language = get_result_language(first_result) or "—"

    # Clickable Telegram user name
    if requested_by_id:
        requested_by = (
            f'<a href="tg://user?id={requested_by_id}">'
            f'{html_escape(requested_by_name or "User")}'
            f'</a>'
        )
    else:
        requested_by = html_escape(
            requested_by_name or "User"
        )

    text = (
        f"🎬 <b>Tɪᴛʟᴇ:</b> "
        f"{html_escape(str(title))}\n"

        f"📅 <b>Yᴇᴀʀ:</b> "
        f"{html_escape(str(year))}\n"

        f"🌐 <b>Lᴀɴɢᴜᴀɢᴇ:</b> "
        f"{html_escape(str(language))}\n"

        f"⏰ <b>ʀᴇsᴜʟᴛ ɪɴ :</b> "
        f"{search_time:.2f} Sᴇᴄᴏɴᴅs\n"

        f'🔎 <b>Requested by : <a href="tg://user?id={requested_by_id}">{html_escape(requested_by_name or "User")}</a></b>\n'
        
        f"⚡ <b>Pᴏᴡᴇʀᴇᴅ Bʏ:</b> "
        f"<b>@Aero_Unity</b>\n\n"

        f"<b>Hᴇʀᴇ Aʀᴇ Yᴏᴜʀ Rᴇsᴜʟᴛs</b> 👇"
    )

    return text
# ============================================================
# FILTER TEXT
# ============================================================

def build_filter_text(
    options,
    current_filters=None
):

    current_filters = (
        current_filters or {}
    )

    text = (
        "⚙️ <b>Sᴇᴀʀᴄ Fɪʟᴛᴇʀs</b>\n\n"
    )

    if current_filters:

        text += "<b>Current:</b>\n"

        for key, value in current_filters.items():

            text += (
                f"• {html_escape(str(key))}: "
                f"{html_escape(str(value))}\n"
            )

        text += "\n"

    languages = options.get(
        "languages",
        []
    )

    years = options.get(
        "years",
        []
    )

    qualities = options.get(
        "qualities",
        []
    )

    seasons = options.get(
        "seasons",
        []
    )

    episodes = options.get(
        "episodes",
        []
    )

    if languages:

        text += (
            "🌐 <b>Lᴀɴɢᴜᴀɢᴇ</b>\n"
        )

        text += ", ".join(
            str(x)
            for x in languages[:20]
        )

        text += "\n\n"

    if years:

        text += (
            "📅 <b>Yᴇᴀʀ</b>\n"
        )

        text += ", ".join(
            str(x)
            for x in years[:20]
        )

        text += "\n\n"

    if qualities:

        text += (
            "🎞 <b>Qᴜᴀʟɪᴛʏ</b>\n"
        )

        text += ", ".join(
            str(x)
            for x in qualities[:20]
        )

        text += "\n\n"

    if seasons:

        text += (
            "📺 <b>Sᴇᴀsᴏɴ</b>\n"
        )

        text += ", ".join(
            str(x)
            for x in seasons[:20]
        )

        text += "\n\n"

    if episodes:

        text += (
            "🎬 <b>Eᴘɪsᴏᴅᴇ</b>\n"
        )

        text += ", ".join(
            str(x)
            for x in episodes[:20]
        )

        text += "\n\n"

    if not any(
        [
            languages,
            years,
            qualities,
            seasons,
            episodes
        ]
    ):

        text += (
            "❌ <b>Nᴏ Fɪʟᴛᴇʀ Oᴘᴛɪᴏɴs Aᴠᴀɪʟᴀʙʟᴇ.</b>"
        )

    return text


def build_filter_buttons(
    session_id,
    options,
    current_filters=None
):

    current_filters = (
        current_filters or {}
    )

    buttons = []

    languages = options.get(
        "languages",
        []
    )

    years = options.get(
        "years",
        []
    )

    qualities = options.get(
        "qualities",
        []
    )

    seasons = options.get(
        "seasons",
        []
    )

    episodes = options.get(
        "episodes",
        []
    )

    # --------------------------------------------------------
    # LANGUAGES
    # --------------------------------------------------------

    for language in languages[:12]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🌐 {language}",
                    callback_data=(
                        f"setfilter_{session_id}_"
                        f"language_{language}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # YEARS
    # --------------------------------------------------------

    for year in years[:12]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📅 {year}",
                    callback_data=(
                        f"setfilter_{session_id}_"
                        f"year_{year}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # QUALITY
    # --------------------------------------------------------

    for quality in qualities[:12]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎞 {quality}",
                    callback_data=(
                        f"setfilter_{session_id}_"
                        f"quality_{quality}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # SEASON
    # --------------------------------------------------------

    for season in seasons[:12]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📺 Season {season}",
                    callback_data=(
                        f"setfilter_{session_id}_"
                        f"season_{season}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # EPISODE
    # --------------------------------------------------------

    for episode in episodes[:12]:

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎬 Episode {episode}",
                    callback_data=(
                        f"setfilter_{session_id}_"
                        f"episode_{episode}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    if current_filters:

        buttons.append(
            [
                InlineKeyboardButton(
                    "🗑 ᴄʟᴇᴀʀ ғɪʟᴛᴇʀs",
                    callback_data=(
                        f"clearfilters_{session_id}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ ʙᴀᴄᴋ",
                callback_data=(
                    f"filterback_{session_id}"
                )
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )

# ============================================================
# SEARCH
# ============================================================

async def search_movies(
    query,
    page=0,
    filters_data=None
):

    query = clean_query(
        query
    )

    if not query:
        return [], False

    try:
        page = max(
            0,
            int(page)
        )
    except Exception:
        page = 0

    skip = (
        page * SEARCH_PAGE_SIZE
    )

    # One extra result determines next page.
    limit = SEARCH_PAGE_SIZE + 1

    results = await search_media(
        query=query,
        skip=skip,
        limit=limit,
        filters=filters_data or {}
    )

    has_next = (
        len(results) > SEARCH_PAGE_SIZE
    )

    results = results[
        :SEARCH_PAGE_SIZE
    ]

    return results, has_next


async def advanced_search(
    query,
    page=0,
    filters_data=None
):

    query = clean_query(
        query
    )

    if not query:
        return [], False

    results, has_next = await search_movies(
        query,
        page,
        filters_data
    )

    return results, has_next


async def search_exact_title(
    query,
    limit=10
):

    results = await search_media(
        query=query,
        skip=0,
        limit=limit,
        filters={}
    )

    return results

# ============================================================
# FILTER OPTIONS
# ============================================================

async def get_available_filter_options(
    query,
    filters_data=None
):

    return await get_filter_options(
        query=query,
        filters=filters_data or {}
    )


async def get_available_years(
    query,
    filters_data=None
):

    options = await get_filter_options(
        query,
        filters_data
    )

    return options.get(
        "years",
        []
    )


async def get_available_languages(
    query,
    filters_data=None
):

    options = await get_filter_options(
        query,
        filters_data
    )

    return options.get(
        "languages",
        []
    )


async def get_available_qualities(
    query,
    filters_data=None
):

    options = await get_filter_options(
        query,
        filters_data
    )

    return options.get(
        "qualities",
        []
    )


async def get_available_seasons(
    query,
    filters_data=None
):

    options = await get_filter_options(
        query,
        filters_data
    )

    return options.get(
        "seasons",
        []
    )


async def get_available_episodes(
    query,
    filters_data=None
):

    options = await get_filter_options(
        query,
        filters_data
    )

    return options.get(
        "episodes",
        []
    )


# ============================================================
# SEARCH SESSION HELPERS
# ============================================================

async def create_session(
    user_id,
    query,
    filters_data=None
):

    return await create_search_session(
        user_id=user_id,
        query=query,
        filters=filters_data or {}
    )


async def get_session(
    session_id,
    user_id
):

    return await get_search_session(
        session_id=session_id,
        user_id=user_id
    )


async def update_filters(
    session_id,
    user_id,
    filters_data
):

    return await update_search_session_filters(
        session_id=session_id,
        user_id=user_id,
        filters=filters_data or {}
    )


async def get_filters(
    session_id,
    user_id
):

    return await get_search_session_filters(
        session_id=session_id,
        user_id=user_id
    )

# ============================================================
# USER HELPER
# ============================================================

async def ensure_user(
    client,
    user_id
):

    user = await get_user(
        user_id
    )

    if user:
        return user

    try:

        chat = await client.get_users(
            user_id
        )

        first_name = (
            chat.first_name
            or "User"
        )

        username = (
            chat.username
            or ""
        )

    except Exception:

        first_name = "User"
        username = ""

    return await create_user(
        user_id=user_id,
        first_name=first_name,
        username=username
    )

# ============================================================
# AUTO DELETE FILE AFTER 5 MINUTES
# ============================================================

async def delete_file_after_5_minutes(message):

    await asyncio.sleep(300)

    try:

        await message.delete()

        logger.info(
            "FILE AUTO-DELETED AFTER 5 MINUTES | message_id=%s",
            message.id
        )

    except Exception as e:

        logger.warning(
            "FILE AUTO-DELETE FAILED | message_id=%s | %s",
            getattr(message, "id", "unknown"),
            e
        )


async def delete_search_results_after_5_minutes(client, chat_id, message_id):
    try:
        await asyncio.sleep(300)  # 5 minutes

        try:
            await client.delete_messages(
                chat_id,
                message_id
            )
        except Exception:
            pass

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning(
            f"Failed to delete search results "
            f"{chat_id}:{message_id}: {e}"
        )

# ============================================================
# DATABASE FILE DELIVERY
# ============================================================

async def send_database_file(
    client,
    chat_id,
    message_id
):

    try:

        message_id = int(
            message_id
        )

    except Exception:

        return None

    try:

        copied = await client.copy_message(
            chat_id=chat_id,
            from_chat_id=DATABASE_CHANNEL_ID,
            message_id=message_id
        )

        if copied.caption:

            clickable_caption = (
                f'<a href="{UPDATES_URL}">'
                f'<b>{html_escape(copied.caption)}</b>'
                f'</a>'
            )

            await client.edit_message_caption(
                chat_id=chat_id,
                message_id=copied.id,
                caption=clickable_caption,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "• Uᴘᴅᴀᴛᴇs •",
                            url=UPDATES_URL
                        )
                    ]
                ])
            )

        else:

            await client.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=copied.id,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "• Uᴘᴅᴀᴛᴇs •",
                            url=UPDATES_URL
                        )
                    ]
                ])
            )

        asyncio.create_task(
            delete_file_after_5_minutes(copied)
        )

        return copied

    except Exception as e:

        logger.error(
            "DATABASE FILE SEND ERROR: %s",
            e,
            exc_info=True
        )

        return None

# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id,
    user_id=None
):

    if user_id is None:

        if not message.from_user:
            return

        user_id = message.from_user.id

    try:

        message_id = int(
            message_id
        )

    except Exception:

        await message.reply_text(
            "❌ <b>Invalid file ID.</b>"
        )

        return

    # --------------------------------------------------------
    # PRIVATE ONLY
    # --------------------------------------------------------

    if message.chat.type != enums.ChatType.PRIVATE:

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    await ensure_user(
        client,
        user_id
    )

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    not_joined = await check_all_fsubs(
        client,
        user_id
    )

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=f"file_{message_id}"
        )

        return

    # --------------------------------------------------------
    # MEDIA LOOKUP
    # --------------------------------------------------------

    media = await get_media_by_message(
        DATABASE_CHANNEL_ID,
        message_id
    )

    if not media:

        await message.reply_text(
            "<b>This Movie Not Found in Database</b>\n\n"
            "<b>Request To Owner [@Mr_Mohammed_29] To add movie</b>"
        )

        return

    # --------------------------------------------------------
    # REQUEST CHECK
    # --------------------------------------------------------

    allowed = await can_make_request(
        user_id
    )

    if not allowed:

        await message.reply_text(
            "❌ <b>No requests remaining.</b>\n\n"
            "💎 Please activate Premium to continue."
        )

        return

    # --------------------------------------------------------
    # RESERVE REQUEST
    # --------------------------------------------------------

    consumed = await consume_request(
        user_id
    )

    if not consumed:

        await message.reply_text(
            "❌ <b>No requests remaining.</b>"
        )

        return

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    sent = await send_database_file(
        client=client,
        chat_id=user_id,
        message_id=message_id
    )

    if not sent:

        # Restore request if Telegram delivery failed.
        await restore_request(
            user_id
        )

        await message.reply_text(
            "❌ <b>Unable to send this file.</b>\n\n"
            "Your request was restored. Please try again."
        )

        return

    # --------------------------------------------------------
    # WARNING AFTER SINGLE FILE
    # --------------------------------------------------------

    warning_message = await client.send_message(
        user_id,
        "<b>⏳️ ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs...</b>\n\n"
        "<b>›› ʏᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 5 min</b>"
        "<b>sᴏ ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ᴏʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ</b>\n\n"
        "<b> ɴᴏᴛᴇ : ᴜsᴇ ᴠʟᴄ ᴘʟᴀʏᴇʀ ᴏʀ ᴍx ᴘʟᴀʏᴇʀ ᴛᴏ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇs ᴡɪᴛʜ ɢᴏᴏᴅ ᴇxᴘᴇʀɪᴇɴᴄᴇ</b>"
    )
    asyncio.create_task(
        delete_file_after_5_minutes(warning_message)
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    try:
        await record_search(
            str(
                media.get(
                    "title",
                    media.get(
                        "file_name",
                        ""
                    )
                ) 
            )
        )
    except Exception:
        pass

    return 

# ============================================================
# SEND ALL DEEP LINK
# ============================================================

async def handle_sendall_deep_link(
    client,
    message,
    session_id,
    page,
    user_id=None
):

    if user_id is None:

        if not message.from_user:
            return

        user_id = message.from_user.id

    if message.chat.type != enums.ChatType.PRIVATE:

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    await ensure_user(
        client,
        user_id
    )

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    not_joined = await check_all_fsubs(
        client,
        user_id
    )

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=(
                f"sendall_{session_id}_{page}"
            )
        )

        return

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session = await get_search_session(
        session_id=session_id,
        user_id=user_id
    )

    if not session:

        await message.reply_text(
            "❌ <b>Search session expired.</b>\n\n"
            "Please search the movie again."
        )

        return

    query = session.get(
        "query",
        ""
    )

    filters_data = session.get(
        "filters",
        {}
    ) or {}

    try:

        page = max(
            0,
            int(page)
        )

    except Exception:

        page = 0

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    results, _ = await search_movies(
        query=query,
        page=page,
        filters_data=filters_data
    )

    if not results:

        await message.reply_text(
            "❌ <b>No files found on this page.</b>"
        )

        return

    # --------------------------------------------------------
    # SEND ALL
    # --------------------------------------------------------

    sent_count = 0
    failed_count = 0

    for result in results:

        media_message_id = get_result_message_id(
            result
        )

        if media_message_id is None:

            failed_count += 1
            continue

        # Check before each file.
        if not await can_make_request(
            user_id
        ):

            break

        consumed = await consume_request(
            user_id
        )

        if not consumed:
            break

        sent = await send_database_file(
            client=client,
            chat_id=user_id,
            message_id=media_message_id
        )

        if sent:

            sent_count += 1

        else:

            failed_count += 1

            await restore_request(
                user_id
            )

            return
    # --------------------------------------------------------
    # ONE WARNING AFTER SEND ALL
    # --------------------------------------------------------

    if sent_count > 0:

        warning_message = await client.send_message(
            user_id,
            "<b>⏳️ ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs...</b>\n\n"
            "<b>›› ʏᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 5 min</b>"
            "<b>sᴏ ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ᴏʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ</b>\n\n"
            "<b> ɴᴏᴛᴇ : ᴜsᴇ ᴠʟᴄ ᴘʟᴀʏᴇʀ ᴏʀ ᴍx ᴘʟᴀʏᴇʀ ᴛᴏ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇs ᴡɪᴛʜ ɢᴏᴏᴅ ᴇxᴘᴇʀɪᴇɴᴄᴇ</b>"
        )
        asyncio.create_task(
            delete_file_after_5_minutes(warning_message)
        )

# ============================================================
# REFRESH SEARCH RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    message,
    session_id,
    page=0
):

    user_id = message.from_user.id

    session = await get_search_session(
        session_id,
        user_id
    )

    if not session:
        return

    query = session.get(
        "query",
        ""
    )

    filters_data = session.get(
        "filters",
        {}
    ) or {}

    results, has_next = await search_movies(
        query=query,
        page=page,
        filters_data=filters_data
    )

    text = build_search_text(
        query=query,
        results=results,
        page=page,
        has_next=has_next,
        filters_data=filters_data
    )

    keyboard = search_result_buttons(
        results=results,
        session_id=session_id,
        page=page,
        has_next=has_next
    )

    try:

        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )

    except Exception as e:

        logger.error(
            "REFRESH SEARCH ERROR: %s",
            e
        )


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # NORMAL TEXT SEARCH
    # ========================================================

    @app.on_message(
        filters.text
        & ~filters.command([
            "start",
            "alive",
            "gentoken",
            "token",
            "redeem",
            "plans",
            "myplan",
            "id",
            "font",
            "trendlist",
            "generatecode",
            "codes",
            "addfsub",
            "delfsub",
            "fsublist",
            "channel",
            "user",
            "premiumuser",
            "activate",
            "deactivate",
            "addpremium",
            "removepremium",
            "stats",
            "indexstatus",
            "resetindex",
            "ban",
            "unban",
            "banlist",
            "maintenance",
            "broadcast"
        ])
    )
    async def movie_search_handler(
        client,
        message
    ):

        query = clean_query(
            message.text
        )

        if not query:
            return

        if query.startswith("/"):
            return

        user_id = message.from_user.id

        logger.info(
            "Movie search from %s: %s",
            user_id,
            query
        )

        await ensure_user(
            client,
            user_id
        )

        # ----------------------------------------------------
        # FORCE SUB
        # ----------------------------------------------------

        if message.chat.type == enums.ChatType.PRIVATE:

            not_joined = await check_all_fsubs(
                client,
                user_id
            )

            if not_joined:

                await send_fsub_message(
                    client,
                    message,
                    not_joined
                )      

                return

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        try:

            await record_search(
                query
            )

        except Exception:

            pass

        search_start = time.perf_counter()

        results, has_next = await search_movies(
            query=query,
            page=0,
            filters_data={}
        )

        search_time = time.perf_counter() - search_start

        if not results:

            await message.reply_text(
                "<b>Your Requested Files Not Found in Database</b>\n\n"
                "<b>🔎 Please Check Your Spelling On Google & "
                "Try Again ✅</b>",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "• Rᴇǫᴜᴇsᴛ Tᴏ Oᴡɴᴇʀ •",
                            url="https://t.me/Mr_Mohammed_29"
                        ),
                        InlineKeyboardButton(
                            "• Cʜᴇᴄᴋ Sᴘᴇʟʟɪɴɢ •",
                            url=f"https://www.google.com/search?q={query}"
                        )
                    ]
                ])
            )

            return
  
        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        session_id = await create_search_session(
            user_id=user_id,
            query=query,
            filters={}
        )

        text = build_search_text(
            query=query,
            results=results,
            page=0,
            has_next=has_next,
            filters_data={},
            search_time=search_time,
            requested_by_id=user_id,
            requested_by_name=(
                message.from_user.first_name
                or "User"
            )
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=0,
            has_next=has_next
        )

        sent = await message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
        )

        asyncio.create_task(
            delete_search_results_after_5_minutes(
                client,
                sent.chat.id,
                sent.id
            )
        )

    # ========================================================
    # SEARCH PAGE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_page_[a-fA-F0-9]+_\d+$"
        )
    )
    async def search_page_callback(
        client,
        callback
    ):

        parts = callback.data.split(
            "_"
        )

        if len(parts) != 4:
            await callback.answer(
                "Invalid page.",
                show_alert=True
            )
            return

        session_id = parts[2]

        try:
            page = int(parts[3])
        except Exception:
            page = 0

        user_id = callback.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired. Search again.",
                show_alert=True
            )

            return

        query = session.get(
            "query",
            ""
        )

        filters_data = session.get(
            "filters",
            {}
        ) or {}

        results, has_next = await search_movies(
            query=query,
            page=page,
            filters_data=filters_data
        )

        if not results:

            await callback.answer(
                "No more results.",
                show_alert=True
            )

            return

        try:
            requester = await client.get_users(
                user_id
            )

            requested_by_name = (
                requester.first_name
                or "User"
            )

        except Exception:
            requested_by_name = "User"

        text = build_search_text(
            query=query,
            results=results,
            page=page,
            has_next=has_next,
            filters_data=filters_data,
            search_time=0,
            requested_by_id=user_id,
        requested_by_name=requested_by_name
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=page,
            has_next=has_next
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )

        except Exception as e:

            logger.error(
                "SEARCH PAGE EDIT ERROR: %s",
                e
            )

        await callback.answer()

    # ========================================================
    # FILE BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_[a-fA-F0-9]+_\d+$"
        )
    )
    async def file_callback(
        client,
        callback
    ):

        parts = callback.data.split(
            "_"
        )

        if len(parts) != 3:

            await callback.answer(
                "Invalid file.",
                show_alert=True
            )

            return

        session_id = parts[1]

        try:

            message_id = int(
                parts[2]
            )

        except Exception:

            await callback.answer(
                "Invalid file ID.",
                show_alert=True
            )

            return

        user_id = callback.from_user.id

        if callback.message.chat.type != enums.ChatType.PRIVATE:

            me = await client.get_me()

            bot_username = (
                me.username
                or ""
            )

            deep_link = (
                f"https://t.me/"
                f"{bot_username}"
                f"?start=file_{message_id}"
            )

            await callback.answer(
                url=deep_link
            )

            return

        # ----------------------------------------------------
        # PRIVATE
        # ----------------------------------------------------

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired. Search again.",
                show_alert=True
            )

            return

        await callback.answer(
            "Checking file..."
        )

        await handle_file_deep_link(
            client=client,
            message=callback.message,
            message_id=message_id,
            user_id=user_id
        )

    # ========================================================
    # SEND ALL
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^sendall_[a-fA-F0-9]+_\d+$"
        )
    )
    async def sendall_callback(
        client,
        callback
    ):

        parts = callback.data.split(
            "_"
        )

        if len(parts) != 3:

            await callback.answer(
                "Invalid request.",
                show_alert=True
            )

            return

        session_id = parts[1]

        try:
            page = int(parts[2])
        except Exception:
            page = 0

        user_id = callback.from_user.id

        # ----------------------------------------------------
        # GROUP
        # ----------------------------------------------------

        if callback.message.chat.type != enums.ChatType.PRIVATE:

            me = await client.get_me()

            bot_username = (
                me.username
                or ""
            )

            deep_link = (
                f"https://t.me/"
                f"{bot_username}"
                f"?start="
                f"sendall_{session_id}_{page}"
            )

            await callback.answer(
                url=deep_link
            )

            return

        # ----------------------------------------------------
        # PRIVATE
        # ----------------------------------------------------

        await callback.answer(
            "Preparing files..."
        )

        await handle_sendall_deep_link(
            client=client,
            message=callback.message,
            session_id=session_id,
            page=page,
            user_id=user_id
        )

    # ========================================================
    # FILTER PAGE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filters_[a-fA-F0-9]+_\d+$"
        )
    )
    async def filters_callback(
        client,
        callback
    ):

        parts = callback.data.split(
            "_"
        )

        if len(parts) != 3:

            await callback.answer(
                "Invalid filter.",
                show_alert=True
            )

            return

        session_id = parts[1]

        user_id = callback.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired.",
                show_alert=True
            )

            return

        query = session.get(
            "query",
            ""
        )

        current_filters = session.get(
            "filters",
            {}
        ) or {}

        options = await get_filter_options(
            query=query,
            filters=current_filters
        )

        text = build_filter_text(
            options,
            current_filters
        )

        keyboard = build_filter_buttons(
            session_id,
            options,
            current_filters
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )

        except MessageNotModified:
  
            pass

        except Exception as e:

           logger.error(
               "FILTER EDIT ERROR: %s",
               e,
               exc_info=True
           )

        await callback.answer()

    # ========================================================
    # SET FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setfilter_[a-fA-F0-9]+_(language|year|quality|season|episode)_.+$"
        )
    )
    async def set_filter_callback(
        client,
        callback
    ):

        parts = callback.data.split(
            "_",
            3
        )

        if len(parts) != 4:

            await callback.answer(
                "Invalid filter.",
                show_alert=True
            )

            return

        session_id = parts[1]
        field = parts[2]
        value = parts[3]

        user_id = callback.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired.",
                show_alert=True
            )

            return

        if field in (
            "year",
            "season",
            "episode"
        ):

            try:
                value = int(value)
            except Exception:
                pass

        current_filters = session.get(
            "filters",
            {}
        ) or {}

        current_filters[field] = value

        await update_search_session_filters(
            session_id=session_id,
            user_id=user_id,
            filters=current_filters
        )

        await callback.answer(
            f"{field.title()} filter applied."
        )

        # Return directly to refreshed results.
        query = session.get(
            "query",
            ""
        )

        results, has_next = await search_movies(
            query=query,
            page=0,
            filters_data=current_filters
        )

        text = build_search_text(
            query=query,
            results=results,
            page=0,
            has_next=has_next,
            filters_data=current_filters
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=0,
            has_next=has_next
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )

        except MessageNotModified:

            pass

        except Exception as e:

            logger.error(
                "FILTER RESULT EDIT ERROR: %s",
                e,
                exc_info=True
            )

    # ========================================================
    # CLEAR FILTERS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^clearfilters_[a-fA-F0-9]+$"
        )
    )
    async def clear_filters_callback(
        client,
        callback
    ):

        session_id = callback.data.split(
            "_",
            1
        )[1]

        user_id = callback.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired.",
                show_alert=True
            )

            return

        await update_search_session_filters(
            session_id=session_id,
            user_id=user_id,
            filters={}
        )

        query = session.get(
            "query",
            ""
        )

        results, has_next = await search_movies(
            query=query,
            page=0,
            filters_data={}
        )

        text = build_search_text(
            query=query,
            results=results,
            page=0,
            has_next=has_next,
            filters_data={}
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=0,
            has_next=has_next
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )

        except MessageNotModified:

            pass

        except Exception as e:

            logger.error(
                "CLEAR FILTER ERROR: %s",
                e,
                exc_info=True
            )

        await callback.answer(
            "Filters cleared."
        )

    # ========================================================
    # FILTER BACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filterback_[a-fA-F0-9]+$"
        )
    )
    async def filter_back_callback(
        client,
        callback
    ):

        session_id = callback.data.split(
            "_",
            1
        )[1]

        user_id = callback.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback.answer(
                "Search expired.",
                show_alert=True
            )

            return

        query = session.get(
            "query",
            ""
        )

        filters_data = session.get(
            "filters",
            {}
        ) or {}

        results, has_next = await search_movies(
            query=query,
            page=0,
            filters_data=filters_data
        )

        text = build_search_text(
            query=query,
            results=results,
            page=0,
            has_next=has_next,
            filters_data=filters_data
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=0,
            has_next=has_next
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML
            )

        except MessageNotModified:

            pass

        except Exception as e:

            logger.error(
                "FILTER BACK ERROR: %s",
                e,
                exc_info=True
            )

        await callback.answer()

    # ========================================================
    # CLOSE SEARCH
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_close_[a-fA-F0-9]+$"
        )
    )
    async def search_close_callback(
        client,
        callback
    ):

        session_id = callback.data.split(
            "_",
            2
        )[2]

        try:

            await delete_search_session(
                session_id
            )

        except Exception:

            pass

        try:

            await callback.message.delete()

        except Exception:

            pass

        await callback.answer()

    # ========================================================
    # NO-OP
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^noop$"
        )
    )
    async def noop_callback(
        client,
        callback
    ):

        await callback.answer()
