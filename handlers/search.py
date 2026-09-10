import asyncio
import html
import logging
from urllib.parse import quote, unquote

from pyrogram.enums import ParseMode
from pyrogram import filters
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import DATABASE_CHANNEL_ID

from database import (
    create_user,
    consume_request,
    restore_request,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    record_search,
    search_media,
    get_filter_options,
    get_media,
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)

from premium import get_remaining_requests


logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def escape_html(text):
    if text is None:
        return ""

    return html.escape(str(text))


def clean_query(text):
    if not text:
        return ""

    text = str(text).strip()
    text = " ".join(text.split())

    return text.strip()


async def get_bot_username(client):

    me = await client.get_me()

    if not me or not me.username:
        return ""

    return me.username


# ============================================================
# REQUEST CHECK
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
            "Request balance check failed for %s: %s",
            user_id,
            e
        )

        return True


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
        f"?start=sendall_{session_id}_{int(page)}"
    )


# ============================================================
# SEARCH RESULT BUTTONS
# ============================================================

def search_result_buttons(
    results,
    page,
    has_next,
    session_id
):

    buttons = []

    for media in results:

        message_id = media.get(
            "message_id"
        )

        if message_id is None:
            continue

        title = (
            media.get("title")
            or media.get("file_name")
            or media.get("filename")
            or media.get("name")
            or "File"
        )

        title = str(title)

        if len(title) > 45:
            title = title[:42] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📁 {title}",
                    callback_data=(
                        f"file_{session_id}_"
                        f"{int(message_id)}"
                    )
                )
            ]
        )

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "⬅️ Previous",
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
                "Next ➡️",
                callback_data=(
                    f"search_page_"
                    f"{session_id}_"
                    f"{page + 1}"
                )
            )
        )

    if navigation:
        buttons.append(navigation)

    buttons.append(
        [
            InlineKeyboardButton(
                "🔎 Filters",
                callback_data=(
                    f"filters_{session_id}"
                )
            )
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "📦 Send All",
                callback_data=(
                    f"sendall_{session_id}_{page}"
                )
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


# ============================================================
# PREMIUM BUTTONS
# ============================================================

def premium_buttons():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💎 Premium",
                    callback_data="premium"
                )
            ],
            [
                InlineKeyboardButton(
                    "💰 Buy Premium",
                    callback_data="buy_premium"
                )
            ]
        ]
    )


# ============================================================
# PAGINATION BUTTONS
# ============================================================

def pagination_buttons(
    session_id,
    page,
    has_next
):

    buttons = []

    row = []

    if page > 0:

        row.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=(
                    f"search_page_"
                    f"{session_id}_"
                    f"{page - 1}"
                )
            )
        )

    row.append(
        InlineKeyboardButton(
            f"📄 {page + 1}",
            callback_data="noop"
        )
    )

    if has_next:

        row.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=(
                    f"search_page_"
                    f"{session_id}_"
                    f"{page + 1}"
                )
            )
        )

    buttons.append(row)

    return InlineKeyboardMarkup(buttons)


# ============================================================
# FILTER MENU
# ============================================================

def filter_menu_buttons(session_id):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌐 Language",
                    callback_data=f"filter_language_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📅 Year",
                    callback_data=f"filter_year_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎞 Quality",
                    callback_data=f"filter_quality_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📺 Season",
                    callback_data=f"filter_season_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔢 Episode",
                    callback_data=f"filter_episode_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Clear Filters",
                    callback_data=f"clear_filters_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=f"back_search_{session_id}"
                )
            ]
        ]
    )


# ============================================================
# FILTER OPTION BUTTONS
# ============================================================

def option_buttons(
    filter_name,
    session_id,
    options
):

    buttons = []

    for value in options:

        text = str(value)

        if len(text) > 50:
            text = text[:47] + "..."

        encoded_value = quote(
            str(value),
            safe=""
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text,
                    callback_data=(
                        f"setfilter_"
                        f"{filter_name}_"
                        f"{session_id}_"
                        f"{encoded_value}"
                    )
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=(
                    f"filters_{session_id}"
                )
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


# ============================================================
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    has_next,
    filters_data=None
):

    filters_data = filters_data or {}

    lines = [
        "🔎 <b>SEARCH RESULTS</b>",
        "",
        f"🎬 <b>Query:</b> "
        f"<code>{escape_html(query)}</code>",
    ]

    active_filters = []

    for key in [
        "language",
        "year",
        "quality",
        "season",
        "episode"
    ]:

        value = filters_data.get(key)

        if value is not None and str(value).strip():

            active_filters.append(
                f"{key.title()}: "
                f"{escape_html(value)}"
            )

    if active_filters:

        lines.append(
            "⚙️ <b>Filters:</b> "
            + " • ".join(active_filters)
        )

    lines.append("")

    if not results:

        lines.extend(
            [
                "❌ <b>No results found.</b>",
                "",
                "Try another movie, series, "
                "anime or drama name."
            ]
        )

        return "\n".join(lines)

    lines.append(
        f"📄 <b>Page:</b> {page + 1}"
    )

    lines.append("")

    for index, media in enumerate(
        results,
        start=1
    ):

        title = (
            media.get("title")
            or media.get("file_name")
            or media.get("filename")
            or media.get("name")
            or "Unknown File"
        )

        lines.append(
            f"<b>{index}.</b> "
            f"{escape_html(title)}"
        )

    lines.append("")

    if has_next:

        lines.append(
            "➡️ More results are available."
        )

    else:

        lines.append(
            "✅ End of results."
        )

    return "\n".join(lines)


# ============================================================
# SEARCH MOVIES
# ============================================================

async def search_movies(
    query,
    page=0,
    filters=None
):

    page = max(
        0,
        int(page)
    )

    filters = filters or {}

    try:

        results = await search_media(
            query=query,
            skip=page * 10,
            limit=11,
            filters=filters
        )

    except Exception as e:

        logger.exception(
            "search_media failed: %s",
            e
        )

        return [], False

    has_next = len(results) > 10

    results = results[:10]

    return results, has_next


# ============================================================
# ADVANCED SEARCH
# ============================================================

async def advanced_search(
    query,
    page=0,
    filters=None
):

    query = clean_query(query)

    filters = filters or {}

    if not query:
        return [], False

    results, has_next = await search_movies(
        query=query,
        page=page,
        filters=filters
    )

    if results:
        return results, has_next

    words = [
        word
        for word in query.split()
        if len(word) >= 2
    ]

    if len(words) <= 1:

        return [], False

    unique = {}

    for word in words:

        try:

            word_results = await search_media(
                query=word,
                skip=0,
                limit=50,
                filters=filters
            )

        except Exception as e:

            logger.warning(
                "Fallback search failed for %s: %s",
                word,
                e
            )

            continue

        for media in word_results:

            message_id = media.get(
                "message_id"
            )

            if message_id is None:
                continue

            unique[str(message_id)] = media

    combined = list(unique.values())

    combined.sort(
        key=lambda item: int(
            item.get("message_id", 0) or 0
        ),
        reverse=True
    )

    start = page * 10
    end = start + 11

    page_results = combined[start:end]

    has_next = len(page_results) > 10

    return page_results[:10], has_next


# ============================================================
# SEARCH SESSION
# ============================================================

async def create_session_for_search(
    user_id,
    query,
    filters=None
):

    return await create_search_session(
        user_id=user_id,
        query=query,
        filters=filters or {}
    )


# ============================================================
# COPY FILE FROM DATABASE CHANNEL
# ============================================================

async def send_database_file(
    client,
    message,
    message_id
):

    attempts = 0

    while attempts < 3:

        try:

            return await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=int(message_id)
            )

        except FloodWait as e:

            attempts += 1

            await asyncio.sleep(
                int(e.value) + 1
            )

        except RPCError:

            raise

        except Exception:

            raise

    return None


# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id
):

    if not message.chat:
        return

    if message.chat.type != "private":

        await message.reply_text(
            "⚠️ Please open me in private chat."
        )

        return

    user = message.from_user

    if not user:
        return

    user_id = user.id

    await create_user(
        user_id=user_id,
        first_name=user.first_name or "",
        username=user.username or ""
    )

    not_joined = await check_all_fsubs(
        client,
        user_id
    )

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=f"file_{int(message_id)}"
        )

        return

    media = await get_media(
        DATABASE_CHANNEL_ID,
        int(message_id)
    )

    if not media:

        try:

            results = await search_media(
                query=str(message_id),
                skip=0,
                limit=1
            )

            if results:
                media = results[0]

        except Exception as e:

            logger.warning(
                "Media fallback failed: %s",
                e
            )

    if not media:

        await message.reply_text(
            "❌ <b>File not found.</b>",
            parse_mode=ParseMode.HTML
        )

        return

    allowed = await has_requests(
        user_id
    )

    if not allowed:

        await message.reply_text(
            "❌ <b>No requests remaining.</b>\n\n"
            "💎 Upgrade your plan to continue.",
            parse_mode=ParseMode.HTML,
            reply_markup=premium_buttons()
        )

        return

    consumed = await consume_request(
        user_id
    )

    if not consumed:

        await message.reply_text(
            "❌ <b>No requests remaining.</b>\n\n"
            "💎 Please upgrade your plan.",
            parse_mode="HTML",
            reply_markup=premium_buttons()
        )

        return

    try:

        sent = await send_database_file(
            client,
            message,
            int(message_id)
        )

        if not sent:

            raise RuntimeError(
                "File was not copied."
            )

    except Exception as e:

        logger.exception(
            "Failed to send file %s: %s",
            message_id,
            e
        )

        await restore_request(
            user_id
        )

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n"
            "Your request has been restored.",
            parse_mode="HTML"
        )

        return

    try:

        remaining = await get_remaining_requests(
            user_id
        )

    except Exception:

        remaining = None

    if remaining is not None:

        try:

            await message.reply_text(
                "✅ <b>File sent successfully.</b>\n\n"
                f"🎟 Remaining requests: "
                f"<b>{remaining}</b>",
                parse_mode="HTML"
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
    page
):

    if not message.chat:
        return

    if message.chat.type != "private":

        await message.reply_text(
            "⚠️ Please open me in private chat."
        )

        return

    user = message.from_user

    if not user:
        return

    user_id = user.id

    await create_user(
        user_id=user_id,
        first_name=user.first_name or "",
        username=user.username or ""
    )

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
                f"sendall_{session_id}_{int(page)}"
            )
        )

        return

    session = await get_search_session(
        session_id,
        user_id
    )

    if not session:

        await message.reply_text(
            "❌ <b>Search session expired.</b>\n"
            "Please search again.",
            parse_mode=ParseMode.HTML
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
        page=int(page),
        filters=filters_data
    )

    if not results:

        await message.reply_text(
            "❌ No files found on this page.",
            parse_mode=ParseMode.HTML
        )

        return

    sent_count = 0
    failed_count = 0

    for media in results:

        message_id = media.get(
            "message_id"
        )

        if message_id is None:

            failed_count += 1
            continue

        allowed = await has_requests(
            user_id
        )

        if not allowed:
            break

        consumed = await consume_request(
            user_id
        )

        if not consumed:
            break

        try:

            sent = await send_database_file(
                client,
                message,
                int(message_id)
            )

            if not sent:

                raise RuntimeError(
                    "Copy failed."
                )

            sent_count += 1

        except Exception as e:

            failed_count += 1

            logger.exception(
                "Send-all failed for %s: %s",
                message_id,
                e
            )

            await restore_request(
                user_id
            )

    try:

        remaining = await get_remaining_requests(
            user_id
        )

    except Exception:

        remaining = None

    text = (
        "📦 <b>SEND ALL COMPLETED</b>\n\n"
        f"✅ Sent: <b>{sent_count}</b>\n"
        f"❌ Failed: <b>{failed_count}</b>"
    )

    if remaining is not None:

        text += (
            f"\n\n🎟 Remaining requests: "
            f"<b>{remaining}</b>"
        )

    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# REFRESH RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    callback_query,
    session_id,
    page
):

    user_id = callback_query.from_user.id

    session = await get_search_session(
        session_id,
        user_id
    )

    if not session:

        await callback_query.answer(
            "Search session expired.",
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
        page=int(page),
        filters=filters_data
    )

    text = build_search_text(
        query=query,
        results=results,
        page=int(page),
        has_next=has_next,
        filters_data=filters_data
    )

    markup = search_result_buttons(
        results=results,
        page=int(page),
        has_next=has_next,
        session_id=session_id
    )

    try:

        await callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML
            reply_markup=markup
        )

    except Exception as e:

        logger.warning(
            "Could not edit search result: %s",
            e
        )

    await callback_query.answer()


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # START DEEP LINK
    # ========================================================

    @app.on_message(
        filters.private
        & filters.command("start")
    )
    async def search_start_deep_link(
        client,
        message
    ):

        if not message.command:
            return

        if len(message.command) < 2:
            return

        payload = message.command[1].strip()

        if payload.startswith("file_"):

            try:

                message_id = int(
                    payload.split(
                        "_",
                        1
                    )[1]
                )

            except Exception:

                await message.reply_text(
                    "❌ Invalid file link."
                )

                return

            await handle_file_deep_link(
                client,
                message,
                message_id
            )

            return

        if payload.startswith("sendall_"):

            parts = payload.split("_")

            if len(parts) < 3:

                await message.reply_text(
                    "❌ Invalid send-all link."
                )

                return

            session_id = parts[1]

            try:

                page = int(parts[2])

            except Exception:

                page = 0

            await handle_sendall_deep_link(
                client,
                message,
                session_id,
                page
            )

            return

    # ========================================================
    # PRIVATE SEARCH
    # ========================================================

    @app.on_message(
        filters.private
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

        if not message.text:
            return

        query = clean_query(
            message.text
        )

        if not query:
            return

        if query.startswith("/"):
            return

        user = message.from_user

        if not user:
            return

        user_id = user.id

        await create_user(
            user_id=user_id,
            first_name=user.first_name or "",
            username=user.username or ""
        )

        not_joined = await check_all_fsubs(
            client,
            user_id
        )

        if not_joined:

            await send_fsub_message(
                client,
                message,
                not_joined,
                deep_link=None
            )

            return

        try:

            results, has_next = await advanced_search(
                query=query,
                page=0,
                filters={}
            )

        except Exception as e:

            logger.exception(
                "Search failed for %r: %s",
                query,
                e
            )

            await message.reply_text(
                "❌ Search error occurred.\n"
                "Please try again."
            )

            return

        try:

            await record_search(query)

        except Exception:

            pass

        try:

            session_id = await create_session_for_search(
                user_id=user_id,
                query=query,
                filters={}
            )

        except Exception as e:

            logger.exception(
                "Could not create search session: %s",
                e
            )

            await message.reply_text(
                "❌ Could not create search session."
            )

            return

        text = build_search_text(
            query=query,
            results=results,
            page=0,
            has_next=has_next,
            filters_data={}
        )

        markup = search_result_buttons(
            results=results,
            page=0,
            has_next=has_next,
            session_id=session_id
        )

        await message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )

    # ========================================================
    # PAGINATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_page_.+_-?\d+$"
        )
    )
    async def search_page_callback(
        client,
        callback_query
    ):

        data = callback_query.data

        try:

            payload = data[
                len("search_page_"):
            ]

            session_id, page_text = (
                payload.rsplit(
                    "_",
                    1
                )
            )

            page = int(page_text)

        except Exception:

            await callback_query.answer(
                "Invalid page.",
                show_alert=True
            )

            return

        page = max(0, page)

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page
        )

    # ========================================================
    # FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filters_.+$"
        )
    )
    async def filters_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filters_"):
        ]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        try:

            await callback_query.message.edit_reply_markup(
                reply_markup=filter_menu_buttons(
                    session_id
                )
            )

        except Exception:
            pass

        await callback_query.answer()

    # ========================================================
    # SHOW FILTER OPTIONS
    # ========================================================

    async def show_filter_options(
        callback_query,
        filter_name,
        session_id
    ):

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
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

        try:

            options = await get_filter_options(
                query,
                filters_data
            )

        except Exception as e:

            logger.exception(
                "Filter options failed: %s",
                e
            )

            await callback_query.answer(
                "Could not load filters.",
                show_alert=True
            )

            return

        key_map = {
            "language": "languages",
            "year": "years",
            "quality": "qualities",
            "season": "seasons",
            "episode": "episodes"
        }

        values = options.get(
            key_map[filter_name],
            []
        )

        if not values:

            await callback_query.answer(
                "No options found.",
                show_alert=True
            )

            return

        await callback_query.message.edit_reply_markup(
            reply_markup=option_buttons(
                filter_name,
                session_id,
                values
            )
        )

        await callback_query.answer()

    # ========================================================
    # LANGUAGE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_language_.+$"
        )
    )
    async def language_filter_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filter_language_"):
        ]

        await show_filter_options(
            callback_query,
            "language",
            session_id
        )

    # ========================================================
    # YEAR
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_year_.+$"
        )
    )
    async def year_filter_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filter_year_"):
        ]

        await show_filter_options(
            callback_query,
            "year",
            session_id
        )

    # ========================================================
    # QUALITY
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_quality_.+$"
        )
    )
    async def quality_filter_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filter_quality_"):
        ]

        await show_filter_options(
            callback_query,
            "quality",
            session_id
        )

    # ========================================================
    # SEASON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_season_.+$"
        )
    )
    async def season_filter_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filter_season_"):
        ]

        await show_filter_options(
            callback_query,
            "season",
            session_id
        )

    # ========================================================
    # EPISODE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_episode_.+$"
        )
    )
    async def episode_filter_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("filter_episode_"):
        ]

        await show_filter_options(
            callback_query,
            "episode",
            session_id
        )

    # ========================================================
    # SET FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setfilter_.+_.+_.+$"
        )
    )
    async def set_filter_callback(
        client,
        callback_query
    ):

        data = callback_query.data

        try:

            payload = data[
                len("setfilter_"):
            ]

            parts = payload.split(
                "_",
                2
            )

            filter_name = parts[0]
            session_id = parts[1]
            value = parts[2]

        except Exception:

            await callback_query.answer(
                "Invalid filter.",
                show_alert=True
            )

            return

        value = unquote(value)

        if filter_name not in [
            "language",
            "year",
            "quality",
            "season",
            "episode"
        ]:

            await callback_query.answer(
                "Invalid filter.",
                show_alert=True
            )

            return

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        filters_data = session.get(
            "filters",
            {}
        ) or {}

        if filter_name in [
            "year",
            "season",
            "episode"
        ]:

            try:

                value = int(value)

            except Exception:

                await callback_query.answer(
                    "Invalid value.",
                    show_alert=True
                )

                return

        filters_data[filter_name] = value

        await update_search_session_filters(
            session_id=session_id,
            user_id=user_id,
            filters=filters_data
        )

        await callback_query.answer(
            f"{filter_name.title()} selected."
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0
        )

    # ========================================================
    # CLEAR FILTERS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^clear_filters_.+$"
        )
    )
    async def clear_filters_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("clear_filters_"):
        ]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        await update_search_session_filters(
            session_id=session_id,
            user_id=user_id,
            filters={}
        )

        await callback_query.answer(
            "Filters cleared."
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0
        )

    # ========================================================
    # BACK TO SEARCH
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^back_search_.+$"
        )
    )
    async def back_search_callback(
        client,
        callback_query
    ):

        session_id = callback_query.data[
            len("back_search_"):
        ]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0
        )

    # ========================================================
    # FILE BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_.+_.+$"
        )
    )
    async def file_callback(
        client,
        callback_query
    ):

        data = callback_query.data

        try:

            payload = data[
                len("file_"):
            ]

            session_id, message_id = (
                payload.rsplit(
                    "_",
                    1
                )
            )

            message_id = int(message_id)

        except Exception:

            await callback_query.answer(
                "Invalid file.",
                show_alert=True
            )

            return

        try:

            bot_username = await get_bot_username(
                client
            )

            if not bot_username:

                await callback_query.answer(
                    "Bot username unavailable.",
                    show_alert=True
                )

                return

            deep_link = build_file_deep_link(
                bot_username,
                message_id
            )

            await callback_query.message.reply_text(
                "📥 <b>Get File</b>\n\n"
                "Tap the button below to "
                "continue in private chat.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📥 Get File",
                                url=deep_link
                            )
                        ]
                    ]
                )
            )

            await callback_query.answer()

        except Exception as e:

            logger.exception(
                "File callback failed: %s",
                e
            )

            await callback_query.answer(
                "Could not create file link.",
                show_alert=True
            )

    # ========================================================
    # SEND ALL BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^sendall_.+_\d+$"
        )
    )
    async def sendall_callback(
        client,
        callback_query
    ):

        data = callback_query.data

        try:

            payload = data[
                len("sendall_"):
            ]

            session_id, page_text = (
                payload.rsplit(
                    "_",
                    1
                )
            )

            page = int(page_text)

        except Exception:

            await callback_query.answer(
                "Invalid request.",
                show_alert=True
            )

            return

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id
        )

        if not session:

            await callback_query.answer(
                "Search session expired.",
                show_alert=True
            )

            return

        try:

            bot_username = await get_bot_username(
                client
            )

            if not bot_username:

                await callback_query.answer(
                    "Bot username unavailable.",
                    show_alert=True
                )

                return

            deep_link = build_sendall_deep_link(
                bot_username,
                session_id,
                page
            )

            await callback_query.message.reply_text(
                "📦 <b>Send All Files</b>\n\n"
                "Open the bot in private chat "
                "to receive the files.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📦 Send All",
                                url=deep_link
                            )
                        ]
                    ]
                )
            )

            await callback_query.answer()

        except Exception as e:

            logger.exception(
                "Send-all callback failed: %s",
                e
            )

            await callback_query.answer(
                "Could not create link.",
                show_alert=True
            )

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
        callback_query
    ):

        await callback_query.answer()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "register_search_handlers",
    "search_movies",
    "advanced_search",
    "handle_file_deep_link",
    "handle_sendall_deep_link",
    "refresh_filtered_results",
]
