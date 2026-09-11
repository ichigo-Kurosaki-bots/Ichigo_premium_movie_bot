# ============================================================
# handlers/search.py
# ============================================================

import asyncio
import html
import logging
import os
from time import perf_counter
from urllib.parse import quote, unquote

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.dispatcher import StopPropagation

from config import DATABASE_CHANNEL_ID
from database import (
    create_user,
    search_media,
    record_search,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    get_search_session_filters,
    get_media_by_message,
    consume_request,
    restore_request,
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)

from premium import get_remaining_requests


logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

RESULTS_PER_PAGE = 10
MAX_RESULTS = 50
DELETE_AFTER = 300  # 5 minutes

UPDATES_URL = os.getenv(
    "UPDATES_CHANNEL",
    "https://t.me/Aero_Unity"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_updates_url(url):
    """
    Converts:
        @Aero_Unity
    into:
        https://t.me/Aero_Unity

    Leaves normal URLs unchanged.
    """

    if not url:
        return "https://t.me/Aero_Unity"

    url = str(url).strip()

    if url.startswith("@"):
        return f"https://t.me/{url[1:]}"

    if url.startswith("t.me/"):
        return f"https://{url}"

    if not url.startswith(("http://", "https://")):
        return f"https://t.me/{url.lstrip('/')}"

    return url


UPDATES_URL = normalize_updates_url(UPDATES_URL)


def escape_html(text):
    if text is None:
        return ""

    return html.escape(str(text))


def clean_query(text):
    if not text:
        return ""

    text = str(text).strip()

    while "  " in text:
        text = text.replace("  ", " ")

    return text


async def get_bot_username(client):
    try:
        me = await client.get_me()

        if me and me.username:
            return me.username

    except Exception as e:
        logger.error(
            "Failed to get bot username: %s",
            e
        )

    return None


def build_file_deep_link(bot_username, message_id):
    return (
        f"https://t.me/{bot_username}"
        f"?start=file_{int(message_id)}"
    )


def build_sendall_deep_link(
    bot_username,
    session_id,
    page
):
    return (
        f"https://t.me/{bot_username}"
        f"?start=sendall_{session_id}_{page}"
    )


# ============================================================
# DISPLAY TITLE
# ============================================================

def get_result_title(item):
    """
    Choose the best available title.

    Some database records may contain incorrect values
    in `title`, so filename/name fields are preferred.
    """

    candidates = [
        item.get("file_name"),
        item.get("filename"),
        item.get("name"),
        item.get("title"),
    ]

    for value in candidates:

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        # Ignore obviously bad numeric titles.
        if value.isdigit():
            continue

        return value

    return "File"


def get_result_year(item):
    year = (
        item.get("year")
        or item.get("release_year")
        or ""
    )

    if year:
        return str(year)

    return "N/A"


def get_result_audio(item):
    audio = (
        item.get("audio")
        or item.get("language")
        or item.get("languages")
        or "N/A"
    )

    if isinstance(audio, list):
        audio = ", ".join(
            str(x) for x in audio
        )

    return str(audio)


def get_result_rating(item):
    rating = (
        item.get("rating")
        or item.get("imdb")
        or item.get("imdb_rating")
        or "N/A"
    )

    return str(rating)


# ============================================================
# RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    bot_username,
    session_id,
    page
):

    buttons = []

    for item in results:

        message_id = (
            item.get("message_id")
            or item.get("_id")
        )

        if not message_id:
            continue

        title = get_result_title(item)

        # Keep button text readable.
        if len(title) > 55:
            title = title[:52] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🎬 {title}",
                    url=build_file_deep_link(
                        bot_username,
                        message_id
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
                    f"search_page_{session_id}_{page - 1}"
                )
            )
        )

    if len(results) >= RESULTS_PER_PAGE:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"search_page_{session_id}_{page + 1}"
                )
            )
        )

    if navigation:
        buttons.append(navigation)

    # --------------------------------------------------------
    # SEND ALL
    # --------------------------------------------------------

    if results:

        buttons.append(
            [
                InlineKeyboardButton(
                    "📦 Send All",
                    url=build_sendall_deep_link(
                        bot_username,
                        session_id,
                        page
                    )
                )
            ]
        )

    return buttons


# ============================================================
# SEARCH RESULT TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    elapsed,
    filters_data=None
):

    query = escape_html(query)

    text = (
        "🔎 <b>Search Results</b>\n\n"
        f"🎬 <b>Title:</b> {query}\n"
    )

    # --------------------------------------------------------
    # FILTERS
    # --------------------------------------------------------

    if filters_data:

        active = []

        for key, value in filters_data.items():

            if value:

                active.append(
                    f"{escape_html(str(key).title())}: "
                    f"{escape_html(str(value))}"
                )

        if active:

            text += (
                "\n🎯 <b>Filters:</b>\n"
                + "\n".join(
                    f"• {x}" for x in active
                )
                + "\n"
            )

    # --------------------------------------------------------
    # RESULT INFORMATION
    # --------------------------------------------------------

    text += (
        f"\n📊 <b>Results:</b> {len(results)}\n"
        f"⏱️ <b>Time:</b> {elapsed:.2f} seconds\n"
        f"⚡ <b>Powered by:</b> "
        f"<a href=\"https://t.me/Aero_Unity\">"
        f"@Aero_Unity</a>\n\n"
        "👇 <b>Here are your Results</b>\n"
    )

    return text


# ============================================================
# SEARCH DATABASE
# ============================================================

async def search_movies(
    query,
    page=0,
    filters_data=None
):

    skip = page * RESULTS_PER_PAGE

    results = await search_media(
        query,
        skip=skip,
        limit=RESULTS_PER_PAGE + 1,
        filters=filters_data
    )

    if not results:
        return [], False

    has_next = len(results) > RESULTS_PER_PAGE

    results = results[:RESULTS_PER_PAGE]

    return results, has_next


# ============================================================
# ADVANCED SEARCH
# ============================================================

async def advanced_search(
    query,
    page=0,
    filters_data=None
):

    query = clean_query(query)

    if not query:
        return [], False

    # Primary search.
    results, has_next = await search_movies(
        query,
        page,
        filters_data
    )

    if results:
        return results, has_next

    # --------------------------------------------------------
    # FALLBACK WORD SEARCH
    # --------------------------------------------------------

    words = [
        word
        for word in query.split()
        if len(word) >= 2
    ]

    if len(words) <= 1:
        return [], False

    combined = {}

    for word in words:

        try:

            word_results = await search_media(
                word,
                skip=0,
                limit=MAX_RESULTS,
                filters=filters_data
            )

            for item in word_results:

                message_id = (
                    item.get("message_id")
                    or item.get("_id")
                )

                if message_id:
                    combined[str(message_id)] = item

        except Exception as e:

            logger.warning(
                "Fallback search error for '%s': %s",
                word,
                e
            )

    all_results = list(
        combined.values()
    )

    all_results.sort(
        key=lambda x: int(
            x.get("message_id", 0) or 0
        ),
        reverse=True
    )

    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE

    page_results = all_results[start:end]

    return (
        page_results,
        end < len(all_results)
    )


# ============================================================
# SESSION FILTER HELPER
# ============================================================

async def get_session_filters(
    session_id,
    user_id
):

    try:

        data = await get_search_session_filters(
            session_id,
            user_id
        )

        if data is None:
            return {}

        return data

    except Exception as e:

        logger.warning(
            "Failed to get session filters: %s",
            e
        )

        return {}


# ============================================================
# REQUEST BALANCE
# ============================================================

async def has_requests(user_id):

    try:

        remaining = await get_remaining_requests(
            user_id
        )

        if remaining is None:
            return True

        return int(remaining) > 0

    except Exception as e:

        logger.warning(
            "Failed to check request balance: %s",
            e
        )

        # Do not block users if balance lookup itself fails.
        return True


# ============================================================
# AUTO DELETE
# ============================================================

async def delete_messages_after_delay(
    client,
    chat_id,
    message_ids,
    delay=DELETE_AFTER
):

    try:

        await asyncio.sleep(delay)

    except asyncio.CancelledError:
        return

    for message_id in message_ids:

        if not message_id:
            continue

        try:

            await client.delete_messages(
                chat_id,
                message_id
            )

            logger.info(
                "Deleted message %s after %s seconds",
                message_id,
                delay
            )

        except Exception as e:

            logger.warning(
                "Failed to delete message %s: %s",
                message_id,
                e
            )


def schedule_auto_delete(
    client,
    chat_id,
    message_ids
):

    clean_ids = [
        int(x)
        for x in message_ids
        if x
    ]

    if not clean_ids:
        return

    asyncio.create_task(
        delete_messages_after_delay(
            client,
            chat_id,
            clean_ids,
            DELETE_AFTER
        )
    )


# ============================================================
# SEND DATABASE FILE
# ============================================================

async def send_database_file(
    client,
    message,
    message_id
):

    caption = (
        "⚠️ <b>Please save this file before it is "
        "automatically deleted after 5 minutes.</b>\n\n"
        f'📢 <b><a href="{UPDATES_URL}">'
        f'Updates</a></b>'
    )

    reply_markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 Updates",
                    url=UPDATES_URL
                )
            ]
        ]
    )

    return await client.copy_message(
        chat_id=message.chat.id,
        from_chat_id=DATABASE_CHANNEL_ID,
        message_id=int(message_id),
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id
):

    # Only PM.
    if message.chat.type != "private":
        return

    user = message.from_user

    if not user:
        return

    user_id = user.id

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    try:

        await create_user(
            user_id,
            user.username,
            user.first_name
        )

    except Exception as e:

        logger.warning(
            "create_user failed: %s",
            e
        )

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    try:

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

    except Exception as e:

        logger.error(
            "FSub check error: %s",
            e
        )

        not_joined = []

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=f"file_{message_id}"
        )

        return

    # --------------------------------------------------------
    # FIND MEDIA
    # --------------------------------------------------------

    media = None

    try:

        media = await get_media_by_message(
            DATABASE_CHANNEL_ID,
            int(message_id)
        )

    except Exception as e:

        logger.warning(
            "Media lookup failed: %s",
            e
        )

    if not media:

        await message.reply_text(
            "❌ <b>File not found.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # REQUEST LIMIT
    # --------------------------------------------------------

    if not await has_requests(user_id):

        await message.reply_text(
            "❌ <b>You have no requests remaining.</b>\n\n"
            "Please upgrade your plan to continue.",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # CONSUME REQUEST
    # --------------------------------------------------------

    consumed = False

    try:

        consumed = await consume_request(
            user_id
        )

    except Exception as e:

        logger.error(
            "consume_request error: %s",
            e
        )

    if consumed is False:

        await message.reply_text(
            "❌ <b>You have no requests remaining.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    try:

        sent = await send_database_file(
            client,
            message,
            message_id
        )

        if not sent:

            raise RuntimeError(
                "copy_message returned no message"
            )

        # ----------------------------------------------------
        # AUTO DELETE AFTER 5 MINUTES
        # ----------------------------------------------------

        schedule_auto_delete(
            client,
            message.chat.id,
            [sent.id]
        )

        logger.info(
            "File %s sent to %s; scheduled deletion",
            message_id,
            user_id
        )

    except FloodWait as e:

        try:
            await restore_request(user_id)
        except Exception:
            pass

        await message.reply_text(
            f"⏳ <b>Telegram rate limit.</b>\n"
            f"Please try again after {e.value} seconds.",
            parse_mode=ParseMode.HTML
        )

    except RPCError as e:

        try:
            await restore_request(user_id)
        except Exception:
            pass

        logger.error(
            "Telegram error while sending file: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n"
            "Please try again later.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        try:
            await restore_request(user_id)
        except Exception:
            pass

        logger.exception(
            "File send error: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n"
            "Please try again later.",
            parse_mode=ParseMode.HTML
        )


# ============================================================
# SEND ALL DEEP LINK
# ============================================================

async def handle_sendall_deep_link(
    client,
    message,
    session_id,
    page=0
):

    if message.chat.type != "private":
        return

    user = message.from_user

    if not user:
        return

    user_id = user.id

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    try:

        await create_user(
            user_id,
            user.username,
            user.first_name
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    try:

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

    except Exception:

        not_joined = []

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

    session = None

    try:

        session = await get_search_session(
            session_id,
            user_id
        )

    except Exception as e:

        logger.warning(
            "Session lookup failed: %s",
            e
        )

    if not session:

        await message.reply_text(
            "❌ <b>Search session expired.</b>\n"
            "Please search again.",
            parse_mode=ParseMode.HTML
        )

        return

    query = (
        session.get("query")
        or session.get("search_query")
        or ""
    )

    filters_data = (
        session.get("filters")
        or {}
    )

    results, _ = await advanced_search(
        query,
        page=page,
        filters_data=filters_data
    )

    if not results:

        await message.reply_text(
            "❌ <b>No files found.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # SEND FILES
    # --------------------------------------------------------

    sent_messages = []

    success = 0
    failed = 0

    for item in results:

        message_id = (
            item.get("message_id")
            or item.get("_id")
        )

        if not message_id:
            failed += 1
            continue

        if not await has_requests(user_id):
            break

        consumed = False

        try:

            consumed = await consume_request(
                user_id
            )

        except Exception:

            consumed = False

        if consumed is False:
            break

        try:

            sent = await send_database_file(
                client,
                message,
                message_id
            )

            if not sent:
                raise RuntimeError(
                    "File copy failed"
                )

            sent_messages.append(
                sent.id
            )

            success += 1

        except FloodWait as e:

            try:
                await restore_request(
                    user_id
                )
            except Exception:
                pass

            failed += 1

            await asyncio.sleep(
                e.value
            )

        except Exception as e:

            try:
                await restore_request(
                    user_id
                )
            except Exception:
                pass

            failed += 1

            logger.warning(
                "Send all file failed: %s",
                e
            )

    # --------------------------------------------------------
    # AUTO DELETE ALL
    # --------------------------------------------------------

    if sent_messages:

        schedule_auto_delete(
            client,
            message.chat.id,
            sent_messages
        )

    # --------------------------------------------------------
    # RESULT MESSAGE
    # --------------------------------------------------------

    remaining = None

    try:

        remaining = await get_remaining_requests(
            user_id
        )

    except Exception:
        pass

    status = (
        "📦 <b>Send All Completed</b>\n\n"
        f"✅ <b>Sent:</b> {success}\n"
        f"❌ <b>Failed:</b> {failed}\n"
        "⏱️ <b>Files will be deleted after 5 minutes.</b>"
    )

    if remaining is not None:

        status += (
            f"\n\n💳 <b>Remaining Requests:</b> "
            f"{remaining}"
        )

    await message.reply_text(
        status,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# REFRESH FILTERED RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    callback_query,
    session_id,
    page=0
):

    user = callback_query.from_user

    filters_data = await get_session_filters(
        session_id,
        user.id
    )

    session = await get_search_session(
        session_id,
        user.id
    )

    if not session:
        await callback_query.answer(
            "Search session expired.",
            show_alert=True
        )
        return

    query = (
        session.get("query")
        or session.get("search_query")
        or ""
    )

    started = perf_counter()

    results, has_next = await search_movies(
        query,
        page=page,
        filters_data=filters_data
    )

    elapsed = (
        perf_counter() - started
    )

    bot_username = await get_bot_username(
        client
    )

    if not bot_username:
        await callback_query.answer(
            "Bot username unavailable.",
            show_alert=True
        )
        return

    text = build_search_text(
        query,
        results,
        page,
        elapsed,
        filters_data
    )

    keyboard = search_result_buttons(
        results,
        bot_username,
        session_id,
        page
    )

    try:

        await callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=(
                InlineKeyboardMarkup(keyboard)
                if keyboard
                else None
            )
        )

    except Exception as e:

        logger.warning(
            "Failed to edit search results: %s",
            e
        )

    await callback_query.answer()


# ============================================================
# MOVIE SEARCH HANDLER
# ============================================================

async def movie_search_handler(
    client,
    message
):

    if message.chat.type != "private":
        return

    query = clean_query(
        message.text
    )

    if not query:
        return

    if query.startswith("/"):
        return

    started = perf_counter()

    # --------------------------------------------------------
    # SEARCHING MESSAGE
    # --------------------------------------------------------

    searching = await message.reply_text(
        "🔎 <b>Searching...</b>",
        parse_mode=ParseMode.HTML
    )

    try:

        await create_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # RECORD SEARCH
    # --------------------------------------------------------

    try:

        await record_search(
            message.from_user.id,
            query
        )

    except Exception as e:

        logger.warning(
            "record_search failed: %s",
            e
        )

    # --------------------------------------------------------
    # CREATE SESSION
    # --------------------------------------------------------

    try:

        session_id = await create_search_session(
            message.from_user.id,
            query,
            {}
        )

    except Exception as e:

        logger.error(
            "Failed to create search session: %s",
            e
        )

        session_id = None

    if not session_id:

        await searching.edit_text(
            "❌ <b>Unable to create search session.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    try:

        results, has_next = await advanced_search(
            query,
            page=0,
            filters_data={}
        )

    except Exception as e:

        logger.exception(
            "Search failed: %s",
            e
        )

        await searching.edit_text(
            "❌ <b>Search failed.</b>\n\n"
            "Please try again.",
            parse_mode=ParseMode.HTML
        )

        return

    elapsed = (
        perf_counter() - started
    )

    # --------------------------------------------------------
    # NO RESULTS
    # --------------------------------------------------------

    if not results:

        await searching.edit_text(
            (
                "❌ <b>No Results Found</b>\n\n"
                f"🔎 <b>Query:</b> "
                f"{escape_html(query)}\n\n"
                f"⏱️ <b>Time:</b> "
                f"{elapsed:.2f} seconds\n"
                f"⚡ <b>Powered by:</b> "
                f'<a href="https://t.me/Aero_Unity">'
                f"@Aero_Unity</a>"
            ),
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # BOT USERNAME
    # --------------------------------------------------------

    bot_username = await get_bot_username(
        client
    )

    if not bot_username:

        await searching.edit_text(
            "❌ <b>Bot username unavailable.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # RESULT TEXT
    # --------------------------------------------------------

    text = build_search_text(
        query,
        results,
        0,
        elapsed,
        {}
    )

    keyboard = search_result_buttons(
        results,
        bot_username,
        session_id,
        0
    )

    # --------------------------------------------------------
    # SHOW RESULTS
    # --------------------------------------------------------

    try:

        await searching.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=(
                InlineKeyboardMarkup(
                    keyboard
                )
                if keyboard
                else None
            )
        )

    except Exception as e:

        logger.error(
            "Failed to show search results: %s",
            e
        )


# ============================================================
# PAGINATION CALLBACK
# ============================================================

async def search_page_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        parts = data.split("_")

        # search_page_SESSION_PAGE
        if len(parts) < 4:
            raise ValueError

        session_id = parts[2]
        page = int(parts[3])

    except Exception:

        await callback_query.answer(
            "Invalid page.",
            show_alert=True
        )

        return

    await refresh_filtered_results(
        client,
        callback_query,
        session_id,
        page
    )


# ============================================================
# FILTER CALLBACK
# ============================================================

async def filter_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        # filter_SESSION
        parts = data.split("_", 1)

        session_id = parts[1]

    except Exception:

        await callback_query.answer(
            "Invalid filter.",
            show_alert=True
        )

        return

    session = await get_search_session(
        session_id,
        callback_query.from_user.id
    )

    if not session:

        await callback_query.answer(
            "Search session expired.",
            show_alert=True
        )

        return

    query = (
        session.get("query")
        or session.get("search_query")
        or ""
    )

    filters_data = (
        session.get("filters")
        or {}
    )

    buttons = []

    # --------------------------------------------------------
    # CURRENT FILTERS
    # --------------------------------------------------------

    if filters_data:

        for key, value in filters_data.items():

            if value:

                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"❌ {key.title()}: {value}",
                            callback_data=(
                                f"clear_filter_"
                                f"{session_id}_{key}"
                            )
                        )
                    ]
                )

    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------

    buttons.append(
        [
            InlineKeyboardButton(
                "🗑 Clear Filters",
                callback_data=(
                    f"clear_filters_{session_id}"
                )
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=(
                    f"filter_back_{session_id}"
                )
            )
        ]
    )

    await callback_query.message.edit_reply_markup(
        InlineKeyboardMarkup(buttons)
    )

    await callback_query.answer()


# ============================================================
# SET FILTER CALLBACK
# ============================================================

async def set_filter_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        # set_filter_SESSION_KEY_VALUE
        parts = data.split("_", 4)

        session_id = parts[2]
        key = parts[3]
        value = parts[4]

    except Exception:

        await callback_query.answer(
            "Invalid filter.",
            show_alert=True
        )

        return

    session = await get_search_session(
        session_id,
        callback_query.from_user.id
    )

    if not session:

        await callback_query.answer(
            "Session expired.",
            show_alert=True
        )

        return

    current = (
        session.get("filters")
        or {}
    )

    current[key] = value

    await update_search_session_filters(
        session_id,
        callback_query.from_user.id,
        current
    )

    await refresh_filtered_results(
        client,
        callback_query,
        session_id,
        0
    )


# ============================================================
# CLEAR FILTER CALLBACK
# ============================================================

async def clear_filters_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        session_id = data.split(
            "clear_filters_",
            1
        )[1]

    except Exception:

        await callback_query.answer(
            "Invalid request.",
            show_alert=True
        )

        return

    await update_search_session_filters(
        session_id,
        callback_query.from_user.id,
        {}
    )

    await refresh_filtered_results(
        client,
        callback_query,
        session_id,
        0
    )


# ============================================================
# CLEAR SINGLE FILTER
# ============================================================

async def clear_single_filter_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        rest = data.split(
            "clear_filter_",
            1
        )[1]

        session_id, key = rest.rsplit(
            "_",
            1
        )

    except Exception:

        await callback_query.answer(
            "Invalid filter.",
            show_alert=True
        )

        return

    filters_data = await get_session_filters(
        session_id,
        callback_query.from_user.id
    )

    filters_data.pop(
        key,
        None
    )

    await update_search_session_filters(
        session_id,
        callback_query.from_user.id,
        filters_data
    )

    await refresh_filtered_results(
        client,
        callback_query,
        session_id,
        0
    )


# ============================================================
# FILTER BACK
# ============================================================

async def filter_back_callback(
    client,
    callback_query
):

    data = callback_query.data

    try:

        session_id = data.split(
            "filter_back_",
            1
        )[1]

    except Exception:

        await callback_query.answer(
            "Invalid request.",
            show_alert=True
        )

        return

    await refresh_filtered_results(
        client,
        callback_query,
        session_id,
        0
    )


# ============================================================
# START DEEP LINK HANDLER
# ============================================================

async def deep_link_start_handler(
    client,
    message
):

    if message.chat.type != "private":
        return

    text = (
        message.text
        or ""
    ).strip()

    if not text.startswith("/start"):
        return

    parts = text.split(
        maxsplit=1
    )

    if len(parts) < 2:
        return

    payload = parts[1].strip()

    # --------------------------------------------------------
    # FILE
    # --------------------------------------------------------

    if payload.startswith("file_"):

        try:

            message_id = int(
                payload.split(
                    "file_",
                    1
                )[1]
            )

        except Exception:

            await message.reply_text(
                "❌ <b>Invalid file link.</b>",
                parse_mode=ParseMode.HTML
            )

            raise StopPropagation

        await handle_file_deep_link(
            client,
            message,
            message_id
        )

        raise StopPropagation

    # --------------------------------------------------------
    # SEND ALL
    # --------------------------------------------------------

    if payload.startswith("sendall_"):

        try:

            parts = payload.split("_")

            session_id = parts[1]
            page = int(parts[2])

        except Exception:

            await message.reply_text(
                "❌ <b>Invalid Send All link.</b>",
                parse_mode=ParseMode.HTML
            )

            raise StopPropagation

        await handle_sendall_deep_link(
            client,
            message,
            session_id,
            page
        )

        raise StopPropagation


# ============================================================
# NOOP CALLBACK
# ============================================================

async def noop_callback(
    client,
    callback_query
):

    try:

        await callback_query.answer()

    except Exception:
        pass


# ============================================================
# REGISTER HANDLERS
# ============================================================

def register_search_handlers(app):

    # --------------------------------------------------------
    # DEEP LINKS
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            deep_link_start_handler,
            filters.private
            & filters.command("start"),
        ),
        group=-1
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            movie_search_handler,
            filters.private
            & filters.text
            & ~filters.command(
                [
                    "start",
                    "help",
                    "premium",
                    "plans",
                    "myplan"
                ]
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            search_page_callback,
            filters.regex(
                r"^search_page_.+_\d+$"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            filter_callback,
            filters.regex(
                r"^filter_.+"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # SET FILTER
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            set_filter_callback,
            filters.regex(
                r"^set_filter_.+"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # CLEAR ALL FILTERS
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            clear_filters_callback,
            filters.regex(
                r"^clear_filters_.+"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # CLEAR SINGLE FILTER
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            clear_single_filter_callback,
            filters.regex(
                r"^clear_filter_.+"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # FILTER BACK
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            filter_back_callback,
            filters.regex(
                r"^filter_back_.+"
            )
        ),
        group=0
    )

    # --------------------------------------------------------
    # NOOP
    # --------------------------------------------------------

    app.add_handler(
        CallbackQueryHandler(
            noop_callback,
            filters.regex(
                r"^noop$"
            )
        ),
        group=0
    )

    logger.info(
        "Search handlers registered successfully."
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "register_search_handlers",
    "movie_search_handler",
    "handle_file_deep_link",
    "handle_sendall_deep_link",
    "search_movies",
    "advanced_search",
]
