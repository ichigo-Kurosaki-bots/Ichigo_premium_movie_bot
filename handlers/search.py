import asyncio
import logging
import os
import urllib.parse
import urllib.request
import json

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import DATABASE_CHANNEL_ID

from database import (
    get_user,
    create_user,
    consume_request,
    restore_request,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    record_search,
)

from premium import can_use_movie, get_remaining_requests

from search import (
    search_movies,
    get_filter_options,
)

from utils.buttons import (
    search_result_buttons,
    premium_buttons,
    file_sent_buttons,
    filter_menu_buttons,
    language_filter_buttons,
    year_filter_buttons,
    season_filter_buttons,
    quality_filter_buttons,
    episode_filter_buttons,
)

from utils.helpers import escape_html

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)


logger = logging.getLogger(__name__)


# ============================================================
# CONFIG
# ============================================================

FILE_DELETE_AFTER = 300

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")


# ============================================================
# FILTER HELPERS
# ============================================================

def normalize_filters(filters_data=None):
    """
    Normalize search filters.

    Supported:
        language
        year
        quality
        season
        episode
    """

    if not filters_data:
        return {}

    result = {}

    for key in (
        "language",
        "year",
        "quality",
        "season",
        "episode",
    ):
        value = filters_data.get(key)

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        if value.lower() == "clear":
            continue

        result[key] = value

    return result


def filters_to_text(filters_data=None):
    """
    Convert active filters into readable text.
    """

    filters_data = normalize_filters(filters_data)

    if not filters_data:
        return "No filters applied"

    parts = []

    if filters_data.get("language"):
        parts.append(
            f"Language: {filters_data['language']}"
        )

    if filters_data.get("year"):
        parts.append(
            f"Year: {filters_data['year']}"
        )

    if filters_data.get("quality"):
        parts.append(
            f"Quality: {filters_data['quality']}"
        )

    if filters_data.get("season"):
        parts.append(
            f"Season: {filters_data['season']}"
        )

    if filters_data.get("episode"):
        parts.append(
            f"Episode: {filters_data['episode']}"
        )

    return " • ".join(parts)


# ============================================================
# TMDB
# ============================================================

async def get_tmdb_metadata(title):
    """
    Fetch basic TMDB metadata.
    """

    if not TMDB_API_KEY:
        return None

    if not title:
        return None

    try:

        encoded_title = urllib.parse.quote(title)

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API_KEY}"
            f"&query={encoded_title}"
        )

        def fetch():

            with urllib.request.urlopen(
                url,
                timeout=8,
            ) as response:

                return json.loads(
                    response.read().decode("utf-8")
                )

        data = await asyncio.to_thread(fetch)

        results = data.get(
            "results",
            [],
        )

        if not results:
            return None

        item = results[0]

        return {
            "title": (
                item.get("title")
                or item.get("name")
                or title
            ),
            "overview": item.get(
                "overview",
                "",
            ),
            "poster_path": item.get(
                "poster_path"
            ),
            "vote_average": item.get(
                "vote_average"
            ),
            "release_date": (
                item.get("release_date")
                or item.get("first_air_date")
                or ""
            ),
        }

    except Exception as e:

        logger.warning(
            "TMDB metadata error: %s",
            e,
        )

        return None


# ============================================================
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    total_pages,
    filters_data=None,
):
    """
    Build search result message.
    """

    filters_data = normalize_filters(
        filters_data
    )

    text = ""

    text += (
        "🔎 <b>Search Results</b>\n\n"
    )

    text += (
        f"🎬 <b>Query:</b> "
        f"<code>{escape_html(query)}</code>\n"
    )

    if filters_data:

        text += (
            f"🎛 <b>Filters:</b> "
            f"{escape_html(filters_to_text(filters_data))}\n"
        )

    text += "\n"

    if results:

        text += (
            f"📄 <b>Page:</b> "
            f"{page}/{total_pages}\n\n"
        )

    return text


# ============================================================
# DELETE MESSAGE LATER
# ============================================================

async def delete_file_later(
    client,
    chat_id,
    message_id,
    delay=FILE_DELETE_AFTER,
):
    """
    Delete a sent file after a delay.
    """

    try:

        await asyncio.sleep(delay)

        try:

            await client.delete_messages(
                chat_id,
                message_id,
            )

        except Exception as e:

            logger.warning(
                "Could not delete message %s: %s",
                message_id,
                e,
            )

    except asyncio.CancelledError:

        pass

    except Exception as e:

        logger.exception(
            "delete_file_later error: %s",
            e,
        )


# ============================================================
# SEND DATABASE FILE
# ============================================================

async def send_database_file(
    client,
    chat_id,
    database_message_id,
):
    """
    Copy a file from the private database channel
    to the requested user's PM.
    """

    try:

        sent = await client.copy_message(
            chat_id=chat_id,
            from_chat_id=DATABASE_CHANNEL_ID,
            message_id=int(database_message_id),
        )

        if sent:

            asyncio.create_task(
                delete_file_later(
                    client,
                    chat_id,
                    sent.id,
                )
            )

        return sent

    except Exception as e:

        logger.exception(
            "Failed to send database file: %s",
            e,
        )

        return None


# ============================================================
# DELETE MULTIPLE FILES
# ============================================================

async def delete_files_and_warning_later(
    client,
    chat_id,
    message_ids,
    delay=FILE_DELETE_AFTER,
):
    """
    Delete multiple delivered files after delay.
    """

    try:

        await asyncio.sleep(delay)

        for message_id in message_ids:

            try:

                await client.delete_messages(
                    chat_id,
                    message_id,
                )

            except Exception:

                pass

    except asyncio.CancelledError:

        pass

    except Exception as e:

        logger.warning(
            "Delete multiple files error: %s",
            e,
        )


# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    file_id,
):
    """
    Handle:

        /start file_<message_id>
    """

    if not message.from_user:
        return

    user_id = message.from_user.id

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    joined = await check_all_fsubs(
        client,
        user_id,
    )

    if not joined:

        await send_fsub_message(
            client,
            message,
            deep_link=f"file_{file_id}",
        )

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    user = await get_user(
        user_id
    )

    if not user:

        await create_user(
            user_id=user_id,
            username=(
                message.from_user.username
                if message.from_user
                else None
            ),
        )

    # --------------------------------------------------------
    # PREMIUM / FREE REQUEST
    # --------------------------------------------------------

    allowed = await can_use_movie(
        user_id
    )

    if not allowed:

        remaining = await get_remaining_requests(
            user_id
        )

        await message.reply_text(
            "❌ <b>Request limit reached.</b>\n\n"
            f"🎬 Remaining requests: <b>{remaining}</b>\n\n"
            "⭐ Upgrade to Premium for more access.",
            reply_markup=premium_buttons(),
        )

        return

    # --------------------------------------------------------
    # CONSUME REQUEST
    # --------------------------------------------------------

    consumed = await consume_request(
        user_id
    )

    if not consumed:

        await message.reply_text(
            "❌ You cannot request this file right now."
        )

        return

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    sent = await send_database_file(
        client,
        message.chat.id,
        file_id,
    )

    if not sent:

        try:

            await restore_request(
                user_id
            )

        except Exception:

            pass

        await message.reply_text(
            "❌ <b>File delivery failed.</b>\n"
            "Please try again later."
        )

        return

    # --------------------------------------------------------
    # RECORD
    # --------------------------------------------------------

    try:

        await record_search(
            user_id,
            str(file_id),
        )

    except Exception:

        pass

    remaining = await get_remaining_requests(
        user_id
    )

    try:

        await message.reply_text(
            "✅ <b>File sent successfully!</b>\n\n"
            f"⏳ Auto-delete: "
            f"<b>{FILE_DELETE_AFTER // 60} minutes</b>\n"
            f"🎬 Remaining requests: "
            f"<b>{remaining}</b>",
            reply_markup=file_sent_buttons(),
        )

    except Exception:

        pass


# ============================================================
# SEND ALL DEEP LINK
# ============================================================

async def handle_sendall_deep_link(
    client,
    message,
    session_id,
    page=0,
):
    """
    Handle:

        /start sendall_<session_id>_<page>
    """

    if not message.from_user:
        return

    user_id = message.from_user.id

    # --------------------------------------------------------
    # FORCE SUB
    # --------------------------------------------------------

    joined = await check_all_fsubs(
        client,
        user_id,
    )

    if not joined:

        await send_fsub_message(
            client,
            message,
            deep_link=(
                f"sendall_{session_id}_{page}"
            ),
        )

        return

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session = await get_search_session(
        session_id
    )

    if not session:

        await message.reply_text(
            "❌ <b>Search session expired.</b>\n\n"
            "Please search again."
        )

        return

    query = session.get(
        "query",
        "",
    )

    filters_data = normalize_filters(
        session.get(
            "filters",
            {},
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    try:

        results, total_pages = await search_movies(
            query,
            page=int(page) + 1,
            filters=filters_data,
        )

    except Exception as e:

        logger.exception(
            "SEND ALL search error: %s",
            e,
        )

        await message.reply_text(
            "❌ Could not load search results."
        )

        return

    if not results:

        await message.reply_text(
            "❌ No files found."
        )

        return

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    user = await get_user(
        user_id
    )

    if not user:

        await create_user(
            user_id=user_id,
            username=(
                message.from_user.username
                if message.from_user
                else None
            ),
        )

    # --------------------------------------------------------
    # SEND FILES
    # --------------------------------------------------------

    sent_ids = []

    for item in results:

        database_message_id = (
            item.get("message_id")
            or item.get("telegram_message_id")
            or item.get("_id")
        )

        if not database_message_id:
            continue

        allowed = await can_use_movie(
            user_id
        )

        if not allowed:
            break

        consumed = await consume_request(
            user_id
        )

        if not consumed:
            break

        sent = await send_database_file(
            client,
            message.chat.id,
            database_message_id,
        )

        if sent:

            sent_ids.append(
                sent.id
            )

        else:

            try:

                await restore_request(
                    user_id
                )

            except Exception:

                pass

    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    if sent_ids:

        asyncio.create_task(
            delete_files_and_warning_later(
                client,
                message.chat.id,
                sent_ids,
            )
        )

    # --------------------------------------------------------
    # RESULT MESSAGE
    # --------------------------------------------------------

    if not sent_ids:

        await message.reply_text(
            "❌ No files could be delivered."
        )

        return

    remaining = await get_remaining_requests(
        user_id
    )

    await message.reply_text(
        "✅ <b>Files sent successfully!</b>\n\n"
        f"📦 Files sent: <b>{len(sent_ids)}</b>\n"
        f"⏳ Auto-delete: "
        f"<b>{FILE_DELETE_AFTER // 60} minutes</b>\n"
        f"🎬 Remaining requests: "
        f"<b>{remaining}</b>",
        reply_markup=file_sent_buttons(),
    )


# ============================================================
# FILTER MENU
# ============================================================

async def show_filter_menu(
    client,
    callback_query,
    session_id,
    page=0,
):
    """
    Show the main filter menu.
    """

    session = await get_search_session(
        session_id
    )

    if not session:

        await callback_query.answer(
            "Search session expired.",
            show_alert=True,
        )

        return

    query = session.get(
        "query",
        "",
    )

    current_filters = normalize_filters(
        session.get(
            "filters",
            {},
        )
    )

    filters_data = await get_filter_options(
        query,
        filters=current_filters,
    )

    text = (
        "🎛 <b>Search Filters</b>\n\n"
        f"🔎 <b>Query:</b> "
        f"<code>{escape_html(query)}</code>\n\n"
    )

    if current_filters:

        text += (
            "✅ <b>Active Filters</b>\n"
            f"{escape_html(filters_to_text(current_filters))}\n\n"
        )

    else:

        text += (
            "ℹ️ No filters selected.\n\n"
        )

    text += "Select a filter:"

    await callback_query.message.edit_text(
        text,
        reply_markup=filter_menu_buttons(
            session_id,
            page=page,
            available=filters_data,
        ),
    )

    await callback_query.answer()


# ============================================================
# REFRESH FILTERED RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    callback_query,
    session_id,
    page=0,
):
    """
    Refresh search results after changing filters.
    """

    session = await get_search_session(
        session_id
    )

    if not session:

        await callback_query.answer(
            "Search session expired.",
            show_alert=True,
        )

        return

    query = session.get(
        "query",
        "",
    )

    filters_data = normalize_filters(
        session.get(
            "filters",
            {},
        )
    )

    try:

        results, total_pages = await search_movies(
            query,
            page=int(page) + 1,
            filters=filters_data,
        )

    except Exception as e:

        logger.exception(
            "Filtered search error: %s",
            e,
        )

        await callback_query.answer(
            "Search failed.",
            show_alert=True,
        )

        return

    # --------------------------------------------------------
    # NO RESULTS
    # --------------------------------------------------------

    if not results:

        available = await get_filter_options(
            query,
            filters=filters_data,
        )

        text = (
            "❌ <b>No results found.</b>\n\n"
            f"🔎 <b>Query:</b> "
            f"<code>{escape_html(query)}</code>\n"
        )

        if filters_data:

            text += (
                f"🎛 <b>Filters:</b> "
                f"{escape_html(filters_to_text(filters_data))}\n"
            )

        text += (
            "\nTry changing or clearing your filters."
        )

        await callback_query.message.edit_text(
            text,
            reply_markup=filter_menu_buttons(
                session_id,
                page=0,
                available=available,
            ),
        )

        await callback_query.answer()

        return

    # --------------------------------------------------------
    # BUILD TEXT
    # --------------------------------------------------------

    text = build_search_text(
        query,
        results,
        int(page) + 1,
        total_pages,
        filters_data,
    )

    # --------------------------------------------------------
    # BOT USERNAME
    # --------------------------------------------------------

    try:

        bot_username = (
            client.me.username
            if client.me
            else None
        )

    except Exception:

        bot_username = None

    # --------------------------------------------------------
    # BUTTONS
    # --------------------------------------------------------

    has_next = (
        int(page) + 1 < int(total_pages)
    )

    keyboard = search_result_buttons(
        results,
        session_id,
        page=int(page),
        has_next=has_next,
        bot_username=bot_username,
    )

    await callback_query.message.edit_text(
        text,
        reply_markup=keyboard,
    )

    await callback_query.answer()


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # SEARCH COMMAND / TEXT
    # ========================================================

    @app.on_message(
        filters.private
        & filters.text
        & ~filters.command(
            [
                "start",
                "help",
                "premium",
                "account",
            ]
        )
    )
    async def movie_search_handler(
        client,
        message,
    ):

        if not message.from_user:
            return

        query = message.text.strip()

        if not query:
            return

        user_id = message.from_user.id

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id=user_id,
                username=(
                    message.from_user.username
                    if message.from_user
                    else None
                ),
            )

        # ----------------------------------------------------
        # FORCE SUB
        # ----------------------------------------------------

        joined = await check_all_fsubs(
            client,
            user_id,
        )

        if not joined:

            await send_fsub_message(
                client,
                message,
            )

            return

        # ----------------------------------------------------
        # PREMIUM / FREE
        # ----------------------------------------------------

        allowed = await can_use_movie(
            user_id
        )

        if not allowed:

            remaining = await get_remaining_requests(
                user_id
            )

            await message.reply_text(
                "❌ <b>Request limit reached.</b>\n\n"
                f"🎬 Remaining requests: "
                f"<b>{remaining}</b>\n\n"
                "⭐ Upgrade to Premium.",
                reply_markup=premium_buttons(),
            )

            return

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        try:

            results, total_pages = await search_movies(
                query,
                page=1,
                filters={},
            )

        except Exception as e:

            logger.exception(
                "Search error: %s",
                e,
            )

            await message.reply_text(
                "❌ Search failed. Please try again."
            )

            return

        if not results:

            await message.reply_text(
                "❌ <b>No results found.</b>\n\n"
                f"🔎 <code>{escape_html(query)}</code>"
            )

            return

        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        session_id = await create_search_session(
            user_id=user_id,
            query=query,
            filters={},
        )

        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        text = build_search_text(
            query,
            results,
            1,
            total_pages,
            {},
        )

        # ----------------------------------------------------
        # BOT USERNAME
        # ----------------------------------------------------

        try:

            bot_username = (
                client.me.username
                if client.me
                else None
            )

        except Exception:

            bot_username = None

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        has_next = (
            int(total_pages) > 1
        )

        keyboard = search_result_buttons(
            results,
            session_id,
            page=0,
            has_next=has_next,
            bot_username=bot_username,
        )

        await message.reply_text(
            text,
            reply_markup=keyboard,
        )

        try:

            await record_search(
                user_id,
                query,
            )

        except Exception:

            pass

    # ========================================================
    # FILTER MENU
    # Supports:
    #
    # filter_menu_SESSION
    # filter_menu_SESSION_PAGE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_menu_[a-fA-F0-9]+(?:_\d+)?$"
        )
    )
    async def filter_menu_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]

        if len(parts) >= 4:

            try:
                page = int(parts[3])

            except ValueError:
                page = 0

        else:

            page = 0

        await show_filter_menu(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # LANGUAGE FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_lang_[a-fA-F0-9]+_\d+$"
        )
    )
    async def language_filter_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]
        page = int(parts[3])

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        query = session.get(
            "query",
            "",
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        options = await get_filter_options(
            query,
            filters=current_filters,
        )

        languages = options.get(
            "languages",
            [],
        )

        await callback_query.message.edit_text(
            "🌐 <b>Select Language</b>\n\n"
            "Choose a language:",
            reply_markup=language_filter_buttons(
                session_id,
                languages,
                page=page,
                current_language=current_filters.get(
                    "language"
                ),
            ),
        )

        await callback_query.answer()

    # ========================================================
    # YEAR FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_year_[a-fA-F0-9]+_\d+$"
        )
    )
    async def year_filter_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]
        page = int(parts[3])

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        query = session.get(
            "query",
            "",
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        options = await get_filter_options(
            query,
            filters=current_filters,
        )

        years = options.get(
            "years",
            [],
        )

        await callback_query.message.edit_text(
            "📅 <b>Select Year</b>\n\n"
            "Choose a year:",
            reply_markup=year_filter_buttons(
                session_id,
                years,
                page=page,
                current_year=current_filters.get(
                    "year"
                ),
            ),
        )

        await callback_query.answer()

    # ========================================================
    # QUALITY FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_quality_[a-fA-F0-9]+_\d+$"
        )
    )
    async def quality_filter_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]
        page = int(parts[3])

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        query = session.get(
            "query",
            "",
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        options = await get_filter_options(
            query,
            filters=current_filters,
        )

        qualities = options.get(
            "qualities",
            [],
        )

        if not qualities:

            await callback_query.answer(
                "No quality options available.",
                show_alert=True,
            )

            return

        await callback_query.message.edit_text(
            "🎥 <b>Select Quality</b>\n\n"
            "Choose a quality:",
            reply_markup=quality_filter_buttons(
                session_id,
                qualities,
                page=page,
                current_quality=current_filters.get(
                    "quality"
                ),
            ),
        )

        await callback_query.answer()

    # ========================================================
    # SEASON FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_season_[a-fA-F0-9]+_\d+$"
        )
    )
    async def season_filter_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]
        page = int(parts[3])

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        query = session.get(
            "query",
            "",
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        options = await get_filter_options(
            query,
            filters=current_filters,
        )

        seasons = options.get(
            "seasons",
            [],
        )

        await callback_query.message.edit_text(
            "📺 <b>Select Season</b>\n\n"
            "Choose a season:",
            reply_markup=season_filter_buttons(
                session_id,
                seasons,
                page=page,
                current_season=current_filters.get(
                    "season"
                ),
            ),
        )

        await callback_query.answer()

    # ========================================================
    # EPISODE FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_episode_[a-fA-F0-9]+_\d+$"
        )
    )
    async def episode_filter_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split("_")

        session_id = parts[2]
        page = int(parts[3])

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        query = session.get(
            "query",
            "",
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        options = await get_filter_options(
            query,
            filters=current_filters,
        )

        episodes = options.get(
            "episodes",
            [],
        )

        await callback_query.message.edit_text(
            "🎞 <b>Select Episode</b>\n\n"
            "Choose an episode:",
            reply_markup=episode_filter_buttons(
                session_id,
                episodes,
                page=page,
                current_episode=current_filters.get(
                    "episode"
                ),
            ),
        )

        await callback_query.answer()

    # ========================================================
    # SET LANGUAGE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setlang_[a-fA-F0-9]+_\d+_.+$"
        )
    )
    async def set_language_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_",
            3,
        )

        session_id = parts[1]
        page = int(parts[2])
        language = parts[3].strip()

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        if language.lower() == "clear":

            current_filters.pop(
                "language",
                None,
            )

        else:

            current_filters["language"] = language

        await update_search_session_filters(
            session_id,
            current_filters,
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # SET YEAR
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setyear_[a-fA-F0-9]+_\d+_.+$"
        )
    )
    async def set_year_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_",
            3,
        )

        session_id = parts[1]
        page = int(parts[2])
        year = parts[3].strip()

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        if year.lower() == "clear":

            current_filters.pop(
                "year",
                None,
            )

        else:

            current_filters["year"] = year

        await update_search_session_filters(
            session_id,
            current_filters,
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # SET QUALITY
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setquality_[a-fA-F0-9]+_\d+_.+$"
        )
    )
    async def set_quality_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_",
            3,
        )

        session_id = parts[1]
        page = int(parts[2])
        quality = parts[3].strip()

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        if quality.lower() == "clear":

            current_filters.pop(
                "quality",
                None,
            )

        else:

            if not quality:

                await callback_query.answer(
                    "Invalid quality.",
                    show_alert=True,
                )

                return

            current_filters["quality"] = quality

        await update_search_session_filters(
            session_id,
            current_filters,
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # SET SEASON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setseason_[a-fA-F0-9]+_\d+_.+$"
        )
    )
    async def set_season_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_",
            3,
        )

        session_id = parts[1]
        page = int(parts[2])
        season = parts[3].strip()

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        if season.lower() == "clear":

            current_filters.pop(
                "season",
                None,
            )

        else:

            current_filters["season"] = season

        await update_search_session_filters(
            session_id,
            current_filters,
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # SET EPISODE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setepisode_[a-fA-F0-9]+_\d+_.+$"
        )
    )
    async def set_episode_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_",
            3,
        )

        session_id = parts[1]
        page = int(parts[2])
        episode = parts[3].strip()

        session = await get_search_session(
            session_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True,
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {},
            )
        )

        if episode.lower() == "clear":

            current_filters.pop(
                "episode",
                None,
            )

        else:

            current_filters["episode"] = episode

        await update_search_session_filters(
            session_id,
            current_filters,
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # CLEAR ALL FILTERS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_clear_[a-fA-F0-9]+_\d+$"
        )
    )
    async def clear_filters_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_"
        )

        session_id = parts[2]
        page = int(parts[3])

        await update_search_session_filters(
            session_id,
            {},
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0,
        )

    # ========================================================
    # FILTER BACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^(?:filter_back|filters)_[a-fA-F0-9]+_\d+$"
        )
    )
    async def filter_back_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_"
        )

        session_id = parts[1]
        page = int(parts[2])

        await show_filter_menu(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # PAGINATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^page_[a-fA-F0-9]+_\d+$"
        )
    )
    async def pagination_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_"
        )

        session_id = parts[1]
        page = int(parts[2])

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )

    # ========================================================
    # LEGACY SEND ALL
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^sendall_[a-fA-F0-9]+_\d+$"
        )
    )
    async def send_all_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_"
        )

        session_id = parts[1]
        page = int(parts[2])

        try:

            bot_username = (
                client.me.username
                if client.me
                else None
            )

        except Exception:

            bot_username = None

        if not bot_username:

            await callback_query.answer(
                "Bot username unavailable.",
                show_alert=True,
            )

            return

        deep_link = (
            f"https://t.me/{bot_username}"
            f"?start=sendall_{session_id}_{page}"
        )

        await callback_query.answer(
            "Opening bot...",
            show_alert=False,
        )

        await callback_query.message.reply_text(
            "📦 <b>Send all files</b>\n\n"
            "Tap the button below to continue in PM.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 SEND ALL",
                            url=deep_link,
                        )
                    ]
                ]
            ),
        )

    # ========================================================
    # LEGACY FILE CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_\d+$"
        )
    )
    async def file_callback(
        client,
        callback_query,
    ):

        parts = callback_query.data.split(
            "_"
        )

        file_id = parts[1]

        try:

            bot_username = (
                client.me.username
                if client.me
                else None
            )

        except Exception:

            bot_username = None

        if not bot_username:

            await callback_query.answer(
                "Bot username unavailable.",
                show_alert=True,
            )

            return

        deep_link = (
            f"https://t.me/{bot_username}"
            f"?start=file_{file_id}"
        )

        await callback_query.answer(
            "Opening bot...",
            show_alert=False,
        )

        await callback_query.message.reply_text(
            "🎬 <b>Get File</b>\n\n"
            "Tap the button below to receive the file in PM.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📥 GET FILE",
                            url=deep_link,
                        )
                    ]
                ]
            ),
        )
