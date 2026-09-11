# ============================================================
# handlers/search.py
# ============================================================

import asyncio
import html
import logging
import os
import re
from time import perf_counter

from pyrogram import filters, StopPropagation
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, RPCError
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
    get_user,
    consume_request,
    restore_request,
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)


logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

RESULTS_PER_PAGE = 10
MAX_RESULTS = 50

# 5 minutes
DELETE_AFTER = 300

UPDATES_URL = os.getenv(
    "UPDATES_CHANNEL",
    "https://t.me/Aero_Unity"
)


# ============================================================
# URL HELPERS
# ============================================================

def normalize_updates_url(url):

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


UPDATES_URL = normalize_updates_url(
    UPDATES_URL
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def escape_html(text):

    if text is None:
        return ""

    return html.escape(
        str(text)
    )


def clean_query(text):

    if not text:
        return ""

    text = str(text).strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

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


# ============================================================
# DEEP LINKS
# ============================================================

def build_file_deep_link(
    bot_username,
    message_id
):

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
# RESULT INFORMATION
# ============================================================

def _valid_text(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # Ignore values which are obviously metadata
    # instead of a movie/file title.
    if re.fullmatch(
        r"(?:\d+|s\d+|e\d+|\d{3,4}p)",
        value,
        re.IGNORECASE
    ):
        return None

    return value


def get_result_title(item):

    candidates = [
        item.get("file_name"),
        item.get("filename"),
        item.get("name"),
        item.get("title"),
        item.get("caption"),
    ]

    for value in candidates:

        value = _valid_text(
            value
        )

        if value:

            # Remove common extension.
            value = re.sub(
                r"\.(mkv|mp4|avi|mov|webm|flv|ts)$",
                "",
                value,
                flags=re.IGNORECASE
            )

            # Make filename easier to read.
            value = value.replace(
                "_",
                " "
            )

            value = re.sub(
                r"\s+",
                " ",
                value
            ).strip()

            if value:
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
            str(x)
            for x in audio
            if x
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


def get_page_year(results):

    years = []

    for item in results:

        year = get_result_year(
            item
        )

        if year != "N/A" and year not in years:
            years.append(year)

    if not years:
        return "N/A"

    return ", ".join(
        years[:5]
    )


def get_page_languages(results):

    languages = []

    for item in results:

        audio = get_result_audio(
            item
        )

        if audio == "N/A":
            continue

        for language in audio.split(","):

            language = language.strip()

            if (
                language
                and language not in languages
            ):
                languages.append(
                    language
                )

    if not languages:
        return "N/A"

    return ", ".join(
        languages[:10]
    )


# ============================================================
# RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    bot_username,
    session_id,
    page,
    has_next=False
):

    buttons = []

    for item in results:

        message_id = (
            item.get("message_id")
            or item.get("_id")
        )

        if not message_id:
            continue

        title = get_result_title(
            item
        )

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

    if has_next:

        navigation.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"search_page_{session_id}_{page + 1}"
                )
            )
        )

    if navigation:
        buttons.append(
            navigation
        )

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
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    elapsed,
    filters_data=None
):

    query = escape_html(
        query
    )

    year = escape_html(
        get_page_year(results)
    )

    language = escape_html(
        get_page_languages(results)
    )

    text = (
        "🔎 <b>Search Results</b>\n\n"

        f"🎬 <b>Title:</b> {query}\n"

        f"📅 <b>Year:</b> {year}\n"

        f"🔊 <b>Language:</b> {language}\n"
    )

    # --------------------------------------------------------
    # FILTER INFORMATION
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
                    f"• {x}"
                    for x in active
                )
                + "\n"
            )

    # --------------------------------------------------------
    # RESULT INFORMATION
    # --------------------------------------------------------

    text += (
        f"\n📊 <b>Results:</b> "
        f"{len(results)}\n"

        f"⏱️ <b>Results shown in:</b> "
        f"{elapsed:.2f} seconds\n"

        f"⚡ <b>Powered by:</b> "
        f'<a href="https://t.me/Aero_Unity">'
        f"@Aero_Unity</a>\n\n"

        "👇 <b>Here are your results</b>"
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

    skip = (
        page * RESULTS_PER_PAGE
    )

    results = await search_media(
        query,
        skip=skip,
        limit=RESULTS_PER_PAGE + 1,
        filters=filters_data
    )

    if not results:
        return [], False

    has_next = (
        len(results)
        > RESULTS_PER_PAGE
    )

    results = results[
        :RESULTS_PER_PAGE
    ]

    return results, has_next


# ============================================================
# ADVANCED SEARCH
# ============================================================

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

    # --------------------------------------------------------
    # PRIMARY SEARCH
    # --------------------------------------------------------

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

                    combined[
                        str(message_id)
                    ] = item

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
            x.get(
                "message_id",
                0
            ) or 0
        ),
        reverse=True
    )

    start = (
        page * RESULTS_PER_PAGE
    )

    end = (
        start + RESULTS_PER_PAGE
    )

    page_results = all_results[
        start:end
    ]

    return (
        page_results,
        end < len(all_results)
    )


# ============================================================
# SESSION FILTERS
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

async def get_remaining_requests_count(
    user_id
):

    try:

        user = await get_user(
            user_id
        )

        if not user:
            return 0

        remaining = user.get(
            "remaining_requests",
            0
        )

        return int(
            remaining or 0
        )

    except Exception as e:

        logger.warning(
            "Failed to get request balance: %s",
            e
        )

        return 0


async def has_requests(
    user_id
):

    return (
        await get_remaining_requests_count(
            user_id
        )
        > 0
    )


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

        await asyncio.sleep(
            delay
        )

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

    clean_ids = []

    for message_id in message_ids:

        if not message_id:
            continue

        try:

            clean_ids.append(
                int(message_id)
            )

        except Exception:
            continue

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
# SEND WARNING
# ============================================================

async def send_delete_warning(
    client,
    message,
    sent_count=1,
    send_all=False
):

    if send_all:

        text = (
            "⚠️ <b>Important</b>\n\n"
            f"📦 <b>{sent_count}</b> file(s) "
            "were sent successfully.\n\n"
            "🗑 <b>These files will be "
            "automatically deleted after "
            "5 minutes.</b>\n\n"
            "Please save them before they are deleted."
        )

    else:

        text = (
            "⚠️ <b>Important</b>\n\n"
            "🗑 <b>This file will be "
            "automatically deleted after "
            "5 minutes.</b>\n\n"
            "Please save it before it is deleted."
        )

    return await message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# SEND DATABASE FILE
# ============================================================

async def send_database_file(
    client,
    message,
    message_id
):

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

    sent = await client.copy_message(
        chat_id=message.chat.id,
        from_chat_id=DATABASE_CHANNEL_ID,
        message_id=int(message_id),
        reply_markup=reply_markup
    )

    return sent


# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id
):

    # --------------------------------------------------------
    # DELIVERY MUST ALWAYS HAPPEN IN PM
    # --------------------------------------------------------

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
    # FORCE SUBSCRIBE
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
    # REQUEST BALANCE
    # --------------------------------------------------------

    if not await has_requests(
        user_id
    ):

        await message.reply_text(
            "❌ <b>You have no requests remaining.</b>\n\n"
            "Please upgrade your plan to continue.",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # CONSUME REQUEST
    # --------------------------------------------------------

    try:

        consumed = await consume_request(
            user_id
        )

    except Exception as e:

        logger.error(
            "consume_request error: %s",
            e
        )

        consumed = False

    if not consumed:

        await message.reply_text(
            "❌ <b>You have no requests remaining.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    sent = None
    warning = None

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
        # WARNING
        # ----------------------------------------------------

        warning = await send_delete_warning(
            client,
            message,
            sent_count=1,
            send_all=False
        )

        # ----------------------------------------------------
        # AUTO DELETE
        # ----------------------------------------------------

        delete_ids = [
            sent.id
        ]

        if warning:
            delete_ids.append(
                warning.id
            )

        schedule_auto_delete(
            client,
            message.chat.id,
            delete_ids
        )

        logger.info(
            "File %s sent to user %s",
            message_id,
            user_id
        )

    except FloodWait as e:

        try:
            await restore_request(
                user_id
            )
        except Exception:
            pass

        await message.reply_text(
            f"⏳ <b>Telegram rate limit.</b>\n\n"
            f"Please try again after "
            f"{e.value} seconds.",
            parse_mode=ParseMode.HTML
        )

    except RPCError as e:

        try:
            await restore_request(
                user_id
            )
        except Exception:
            pass

        logger.error(
            "Telegram error while sending file: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n"
            "Your request has been restored.",
            parse_mode=ParseMode.HTML
        )

    except Exception as e:

        try:
            await restore_request(
                user_id
            )
        except Exception:
            pass

        logger.exception(
            "File send error: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n"
            "Your request has been restored.",
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

    # --------------------------------------------------------
    # ONLY PM
    # --------------------------------------------------------

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
    # FORCE SUBSCRIBE
    # --------------------------------------------------------

    try:

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

    except Exception as e:

        logger.error(
            "Send All FSub check error: %s",
            e
        )

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

        session = None

    if not session:

        await message.reply_text(
            "❌ <b>Search session expired.</b>\n\n"
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

    try:

        results, _ = await advanced_search(
            query,
            page=page,
            filters_data=filters_data
        )

    except Exception as e:

        logger.exception(
            "Send All search failed: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Unable to load files.</b>",
            parse_mode=ParseMode.HTML
        )

        return

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

        # ----------------------------------------------------
        # CHECK BALANCE
        # ----------------------------------------------------

        if not await has_requests(
            user_id
        ):

            break

        # ----------------------------------------------------
        # CONSUME
        # ----------------------------------------------------

        try:

            consumed = await consume_request(
                user_id
            )

        except Exception as e:

            logger.warning(
                "Send All consume error: %s",
                e
            )

            consumed = False

        if not consumed:
            break

        # ----------------------------------------------------
        # SEND
        # ----------------------------------------------------

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
                "Send All file failed: %s",
                e
            )

    # --------------------------------------------------------
    # NOTHING SENT
    # --------------------------------------------------------

    if not sent_messages:

        await message.reply_text(
            "❌ <b>No files could be sent.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    # --------------------------------------------------------
    # WARNING
    # --------------------------------------------------------

    warning = None

    try:

        warning = await send_delete_warning(
            client,
            message,
            sent_count=success,
            send_all=True
        )

    except Exception as e:

        logger.warning(
            "Failed to send deletion warning: %s",
            e
        )

    # --------------------------------------------------------
    # AUTO DELETE
    # --------------------------------------------------------

    delete_ids = list(
        sent_messages
    )

    if warning:

        delete_ids.append(
            warning.id
        )

    schedule_auto_delete(
        client,
        message.chat.id,
        delete_ids
    )

    # --------------------------------------------------------
    # REMAINING REQUESTS
    # --------------------------------------------------------

    remaining = await get_remaining_requests_count(
        user_id
    )

    logger.info(
        "Send All completed | user=%s | sent=%s | failed=%s | remaining=%s",
        user_id,
        success,
        failed,
        remaining
    )


# ============================================================
# REFRESH SEARCH RESULTS
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
        perf_counter()
        - started
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
        page,
        has_next=has_next
    )

    try:

        await callback_query.message.edit_text(
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

    # --------------------------------------------------------
    # ALLOW PM + GROUP + SUPERGROUP
    # --------------------------------------------------------

    if message.chat.type not in [
        "private",
        "group",
        "supergroup"
    ]:

        return

    if not message.from_user:
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

    user_id = (
        message.from_user.id
    )

    # --------------------------------------------------------
    # CREATE USER
    # --------------------------------------------------------

    try:

        await create_user(
            user_id,
            message.from_user.username,
            message.from_user.first_name
        )

    except Exception as e:

        logger.warning(
            "create_user failed: %s",
            e
        )

    # --------------------------------------------------------
    # RECORD SEARCH
    # --------------------------------------------------------

    try:

        await record_search(
            user_id,
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
            user_id,
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

        elapsed = (
            perf_counter()
            - started
        )

        await searching.edit_text(
            (
                "❌ <b>Search failed.</b>\n\n"
                f"⏱️ <b>Time:</b> "
                f"{elapsed:.2f} seconds\n\n"
                "Please try again."
            ),
            parse_mode=ParseMode.HTML
        )

        return

    elapsed = (
        perf_counter()
        - started
    )

    # --------------------------------------------------------
    # NO RESULTS
    # --------------------------------------------------------

    if not results:

        await searching.edit_text(
            (
                "❌ <b>No Results Found</b>\n\n"

                f"🎬 <b>Title:</b> "
                f"{escape_html(query)}\n\n"

                f"⏱️ <b>Results shown in:</b> "
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
        0,
        has_next=has_next
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

        logger.exception(
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

    data = (
        callback_query.data
        or ""
    )

    try:

        parts = data.split("_")

        # search_page_SESSION_PAGE

        if len(parts) < 4:
            raise ValueError

        session_id = parts[2]

        page = int(
            parts[3]
        )

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

    data = (
        callback_query.data
        or ""
    )

    try:

        parts = data.split(
            "_",
            1
        )

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

    filters_data = (
        session.get("filters")
        or {}
    )

    buttons = []

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
        InlineKeyboardMarkup(
            buttons
        )
    )

    await callback_query.answer()


# ============================================================
# SET FILTER CALLBACK
# ============================================================

async def set_filter_callback(
    client,
    callback_query
):

    data = (
        callback_query.data
        or ""
    )

    try:

        parts = data.split(
            "_",
            4
        )

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
# CLEAR ALL FILTERS
# ============================================================

async def clear_filters_callback(
    client,
    callback_query
):

    data = (
        callback_query.data
        or ""
    )

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

    data = (
        callback_query.data
        or ""
    )

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

    data = (
        callback_query.data
        or ""
    )

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
# START DEEP LINK
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

            parts = payload.split(
                "_"
            )

            if len(parts) != 3:
                raise ValueError

            session_id = parts[1]

            page = int(
                parts[2]
            )

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
# NOOP
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
    # DEEP LINK
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            deep_link_start_handler,
            filters.private
            & filters.command("start")
        ),
        group=-1
    )

    # --------------------------------------------------------
    # SEARCH
    #
    # IMPORTANT:
    # NO filters.private HERE.
    #
    # This allows:
    # PM
    # Group
    # Supergroup
    # --------------------------------------------------------

    app.add_handler(
        MessageHandler(
            movie_search_handler,
            filters.text
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
    # CLEAR ALL
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
    # CLEAR SINGLE
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
