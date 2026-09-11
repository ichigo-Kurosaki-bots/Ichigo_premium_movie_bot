# ============================================================
# handlers/search.py
# ============================================================

import logging
import re
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
    DATABASE_CHANNEL_ID
)

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

    title = (
        result.get("title")
        or result.get("file_name")
        or result.get("filename")
        or result.get("name")
        or result.get("caption")
        or "Unknown File"
    )

    return str(title).strip()


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

    value = result.get(
        "year"
    )

    if value is None:
        return ""

    return str(value).strip()


def get_result_quality(result):

    value = result.get(
        "quality"
    )

    if value is None:
        return ""

    return str(value).strip()


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

        title = title[:45]

        button_text = (
            f"{index}. {title}"
        )

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
    # SEND ALL
    # --------------------------------------------------------

    if results:

        buttons.append(
            [
                InlineKeyboardButton(
                    "📦 sᴇɴᴅ ᴀʟʟ",
                    callback_data=(
                        f"sendall_{session_id}_"
                        f"{page}"
                    )
                )
            ]
        )

    # --------------------------------------------------------
    # FILTER BUTTON
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "⚙️ ғɪʟᴛᴇʀs",
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
                "⬅️",
                callback_data=(
                    f"search_page_"
                    f"{session_id}_"
                    f"{page - 1}"
                )
            )
        )

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=(
                    f"search_page_"
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
    # CLOSE
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "✖️ ᴄʟᴏsᴇ",
                callback_data=(
                    f"search_close_"
                    f"{session_id}"
                )
            )
        ]
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
    filters_data=None
):

    query = html_escape(
        str(query)
    )

    total_on_page = len(
        results
    )

    start_number = (
        page * SEARCH_PAGE_SIZE
    ) + 1

    end_number = (
        page * SEARCH_PAGE_SIZE
        + total_on_page
    )

    text = (
        "🔎 <b>Sᴇᴀʀᴄ Rᴇsᴜʟᴛs</b>\n\n"
        f"🎬 <b>Qᴜᴇʀʏ:</b> "
        f"<code>{query}</code>\n"
    )

    if total_on_page:

        text += (
            f"📁 <b>Rᴇsᴜʟᴛs:</b> "
            f"{start_number}-{end_number}\n\n"
        )

    else:

        text += (
            "❌ <b>Nᴏ ʀᴇsᴜʟᴛs ғᴏᴜɴᴅ.</b>\n\n"
        )

    # --------------------------------------------------------
    # ACTIVE FILTERS
    # --------------------------------------------------------

    if filters_data:

        active = []

        for key in (
            "language",
            "year",
            "quality",
            "season",
            "episode"
        ):

            value = filters_data.get(
                key
            )

            if value is not None and str(
                value
            ).strip():

                active.append(
                    f"{key.title()}: {value}"
                )

        if active:

            text += (
                "⚙️ <b>Fɪʟᴛᴇʀs:</b>\n"
                + "\n".join(
                    f"• {html_escape(str(x))}"
                    for x in active
                )
                + "\n\n"
            )

    if has_next:

        text += (
            "➡️ <b>Uѕᴇ Nᴇxᴛ Bᴜᴛᴛᴏɴ Fᴏʀ Mᴏʀᴇ.</b>\n\n"
        )

    text += (
        "👇 <b>Sᴇʟᴇᴄᴛ A Fɪʟᴇ Bᴇʟᴏᴡ.</b>"
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

    # The database search already handles
    # multi-word matching, so do not perform
    # a loose OR search here.
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
            "❌ <b>File not found in database.</b>\n\n"
            "The requested file may have been removed "
            "or is no longer available."
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
        & filters.text
        & ~filters.command(
            [
                "start"
            ]
        )
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
        # REQUEST CHECK
        # ----------------------------------------------------

        if not await can_make_request(
            user_id
        ):

            await message.reply_text(
                "❌ <b>Yᴏᴜ Hᴀᴠᴇ Nᴏ Rᴇǫᴜᴇsᴛs Lᴇғᴛ.</b>\n\n"
                "💎 <b>Aᴄᴛɪᴠᴀᴛᴇ Pʀᴇᴍɪᴜᴍ Tᴏ Cᴏɴᴛɪɴᴜᴇ.</b>"
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

        results, has_next = await search_movies(
            query=query,
            page=0,
            filters_data={}
        )

        if not results:

            await message.reply_text(
                "❌ <b>Nᴏ Rᴇsᴜʟᴛs Fᴏᴜɴᴅ.</b>\n\n"
                f"🔎 <code>{html_escape(query)}</code>\n\n"
                "Tʀʏ Aɴᴏᴛʜᴇʀ Mᴏᴠɪᴇ Oʀ Sᴇʀɪᴇs Nᴀᴍᴇ."
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
            filters_data={}
        )

        keyboard = search_result_buttons(
            results=results,
            session_id=session_id,
            page=0,
            has_next=has_next
        )

        await message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML
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

        except Exception as e:

            logger.error(
                "FILTER EDIT ERROR: %s",
                e
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

        except Exception as e:

            logger.error(
                "FILTER RESULT EDIT ERROR: %s",
                e
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

        except Exception as e:

            logger.error(
                "CLEAR FILTER ERROR: %s",
                e
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

        except Exception as e:

            logger.error(
                "FILTER BACK ERROR: %s",
                e
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
