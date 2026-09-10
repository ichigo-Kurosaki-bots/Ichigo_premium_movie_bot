# ============================================================
# handlers/search.py
# Premium Movie Bot - Search Handler
# ============================================================
#
# Features:
# - Private movie search
# - Group search
# - Force-sub protection
# - Deep-link file delivery
# - FSub Try Again support
# - Search pagination
# - Search filters
# - Send All
# - Search sessions
# - Premium/free request handling
#
# ============================================================

import asyncio
import html
import logging
import os
import re
import urllib.parse
from typing import Optional

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import (
    DATABASE_CHANNEL_ID,
    OWNER_ID,
    ADMIN_IDS,
)

from database import (
    get_user,
    create_user,
    consume_request,
    restore_request,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    record_search,
    search_media,
    get_filter_options,
)

from premium import (
    can_use_movie,
    get_remaining_requests,
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message,
)

logger = logging.getLogger(__name__)


# ============================================================
# BASIC HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    try:
        return (
            int(user_id) == int(OWNER_ID)
            or int(user_id) in [int(x) for x in ADMIN_IDS]
        )
    except Exception:
        return False


def escape_html(text) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def clean_query(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # Remove bot username from commands/messages if present.
    text = re.sub(r"@\w+", "", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_bot_username(client) -> str:
    try:
        me = client.me

        if me and getattr(me, "username", None):
            return me.username

    except Exception:
        pass

    return ""


async def get_bot_username_async(client) -> str:
    try:
        me = await client.get_me()

        if me and me.username:
            return me.username

    except Exception as e:
        logger.warning("Failed to get bot username: %s", e)

    return ""


# ============================================================
# DEEP LINK HELPERS
# ============================================================

def build_file_deep_link(bot_username: str, message_id: int) -> str:
    """
    Creates:

    https://t.me/BOT_USERNAME?start=file_12345
    """

    bot_username = str(bot_username).lstrip("@").strip()

    return (
        f"https://t.me/{bot_username}"
        f"?start=file_{int(message_id)}"
    )


def build_sendall_deep_link(
    bot_username: str,
    session_id: str,
    page: int = 0,
) -> str:
    """
    Creates:

    https://t.me/BOT_USERNAME?start=sendall_SESSION_PAGE
    """

    bot_username = str(bot_username).lstrip("@").strip()

    return (
        f"https://t.me/{bot_username}"
        f"?start=sendall_{session_id}_{int(page)}"
    )


# ============================================================
# SEARCH BUTTONS
# ============================================================

def search_result_buttons(
    results,
    bot_username: str,
):
    buttons = []

    for item in results:
        message_id = item.get("message_id")

        if not message_id:
            continue

        title = (
            item.get("title")
            or item.get("file_name")
            or item.get("filename")
            or item.get("name")
            or "File"
        )

        title = str(title)

        if len(title) > 45:
            title = title[:42] + "..."

        url = build_file_deep_link(
            bot_username,
            int(message_id),
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎬 {title}",
                    url=url,
                )
            ]
        )

    return buttons


def premium_buttons(
    bot_username: str,
    results,
    session_id: Optional[str] = None,
):
    buttons = search_result_buttons(
        results,
        bot_username,
    )

    if session_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    "📦 Send All",
                    url=build_sendall_deep_link(
                        bot_username,
                        session_id,
                        0,
                    ),
                )
            ]
        )

    return buttons


def pagination_buttons(
    page: int,
    has_next: bool,
    session_id: Optional[str] = None,
):
    buttons = []

    row = []

    if page > 0:
        row.append(
            InlineKeyboardButton(
                "⬅️ Previous",
                callback_data=f"search_page_{page - 1}",
            )
        )

    if has_next:
        row.append(
            InlineKeyboardButton(
                "Next ➡️",
                callback_data=f"search_page_{page + 1}",
            )
        )

    if row:
        buttons.append(row)

    if session_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    "🔎 Filters",
                    callback_data=f"search_filters_{session_id}",
                ),
                InlineKeyboardButton(
                    "📦 Send All",
                    callback_data=f"search_sendall_{session_id}_{page}",
                ),
            ]
        )

    return buttons


def filter_menu_buttons(
    session_id: str,
):
    return [
        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data=f"filter_language_{session_id}",
            ),
            InlineKeyboardButton(
                "📅 Year",
                callback_data=f"filter_year_{session_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎞 Quality",
                callback_data=f"filter_quality_{session_id}",
            ),
            InlineKeyboardButton(
                "📺 Season",
                callback_data=f"filter_season_{session_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🎬 Episode",
                callback_data=f"filter_episode_{session_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Clear Filters",
                callback_data=f"filter_clear_{session_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=f"search_back_{session_id}",
            ),
        ],
    ]


def option_buttons(
    session_id: str,
    filter_name: str,
    options,
):
    buttons = []

    for option in options:
        if option is None:
            continue

        value = str(option).strip()

        if not value:
            continue

        # Callback data must remain reasonably small.
        if len(value) > 40:
            value = value[:40]

        buttons.append(
            [
                InlineKeyboardButton(
                    value,
                    callback_data=(
                        f"setfilter_"
                        f"{filter_name}_"
                        f"{session_id}_"
                        f"{value}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=f"search_filters_{session_id}",
            )
        ]
    )

    return buttons


def language_filter_buttons(
    session_id: str,
    options,
):
    return option_buttons(
        session_id,
        "language",
        options,
    )


def year_filter_buttons(
    session_id: str,
    options,
):
    return option_buttons(
        session_id,
        "year",
        options,
    )


def season_filter_buttons(
    session_id: str,
    options,
):
    return option_buttons(
        session_id,
        "season",
        options,
    )


def quality_filter_buttons(
    session_id: str,
    options,
):
    return option_buttons(
        session_id,
        "quality",
        options,
    )


def episode_filter_buttons(
    session_id: str,
    options,
):
    return option_buttons(
        session_id,
        "episode",
        options,
    )


def file_sent_buttons():
    return [
        [
            InlineKeyboardButton(
                "🏠 Home",
                callback_data="search_home",
            )
        ]
    ]


# ============================================================
# SEARCH TEXT
# ============================================================

def build_search_text(
    query: str,
    results,
    page: int,
    has_next: bool,
    filters_data=None,
):
    query = escape_html(query)

    text = (
        "🔎 <b>Search Results</b>\n\n"
        f"🎬 <b>Query:</b> <code>{query}</code>\n"
        f"📄 <b>Page:</b> {page}"
    )

    if has_next:
        text += "\n➡️ <b>More results are available.</b>"

    if filters_data:
        active = []

        for key, value in filters_data.items():
            if value is None:
                continue

            if isinstance(value, list) and not value:
                continue

            active.append(
                f"{key}: {escape_html(value)}"
            )

        if active:
            text += (
                "\n\n🎛 <b>Active Filters:</b>\n"
                + "\n".join(
                    f"• {x}" for x in active
                )
            )

    text += (
        "\n\n"
        f"📦 <b>Results on this page:</b> {len(results)}"
    )

    return text


# ============================================================
# SEARCH WRAPPER
# ============================================================

async def search_movies(
    query: str,
    page: int = 0,
    filters=None,
):
    """
    Search database.

    Returns:

        results, has_next

    Page is ZERO based.
    """

    if filters is None:
        filters = {}

    try:
        skip = max(0, int(page)) * 10

        results = await search_media(
            query=query,
            skip=skip,
            limit=11,
            filters=filters,
        )

        if not results:
            return [], False

        has_next = len(results) > 10

        if has_next:
            results = results[:10]

        return results, has_next

    except Exception as e:
        logger.exception(
            "search_movies error: %s",
            e,
        )
        return [], False


async def advanced_search(
    query: str,
    page: int = 0,
    filters=None,
):
    """
    Phrase-first / robust search.

    First search the complete query.

    If nothing is found, search individual words so that
    a movie with a slightly different indexed title can still
    be found.
    """

    if filters is None:
        filters = {}

    query = clean_query(query)

    if not query:
        return [], False

    # --------------------------------------------------------
    # 1. Full query
    # --------------------------------------------------------

    results, has_next = await search_movies(
        query=query,
        page=page,
        filters=filters,
    )

    if results:
        return results, has_next

    # --------------------------------------------------------
    # 2. Word-by-word fallback
    # --------------------------------------------------------

    words = [
        word.strip()
        for word in query.split()
        if len(word.strip()) >= 2
    ]

    if not words:
        return [], False

    combined = []
    seen = set()

    # Search words individually.
    for word in words:
        try:
            word_results, _ = await search_movies(
                query=word,
                page=0,
                filters=filters,
            )

            for item in word_results:
                message_id = item.get("message_id")

                if message_id in seen:
                    continue

                seen.add(message_id)
                combined.append(item)

        except Exception as e:
            logger.warning(
                "Word search failed for %s: %s",
                word,
                e,
            )

    # Keep deterministic ordering.
    combined.sort(
        key=lambda x: int(
            x.get("message_id", 0)
        ),
        reverse=True,
    )

    start = max(0, int(page)) * 10
    end = start + 11

    page_results = combined[start:end]

    has_next = len(page_results) > 10

    if has_next:
        page_results = page_results[:10]

    return page_results, has_next


# ============================================================
# SESSION HELPERS
# ============================================================

async def create_session_for_search(
    user_id: int,
    query: str,
    filters_data=None,
):
    if filters_data is None:
        filters_data = {}

    try:
        session_id = await create_search_session(
            user_id=user_id,
            query=query,
            filters=filters_data,
        )

        return session_id

    except TypeError:
        # Compatibility with implementations that use
        # positional parameters.
        try:
            session_id = await create_search_session(
                user_id,
                query,
                filters_data,
            )

            return session_id

        except Exception:
            raise

    except Exception:
        raise


# ============================================================
# SEND DATABASE FILE
# ============================================================

async def send_database_file(
    client,
    message,
    media,
):
    """
    Copy a file from the private database channel.

    The bot sends the original Telegram message so that the
    original media is preserved without downloading/reuploading.
    """

    if not media:
        return False

    message_id = media.get("message_id")

    if not message_id:
        return False

    try:
        copied = await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=DATABASE_CHANNEL_ID,
            message_id=int(message_id),
        )

        return copied is not None

    except FloodWait as e:
        await asyncio.sleep(e.value)

        try:
            copied = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=int(message_id),
            )

            return copied is not None

        except Exception as retry_error:
            logger.exception(
                "Retry copy_message failed: %s",
                retry_error,
            )
            return False

    except Exception as e:
        logger.exception(
            "Database file delivery failed: %s",
            e,
        )
        return False


# ============================================================
# FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id: int,
):
    """
    Handles:

        /start file_12345

    Flow:

        User clicks result in group
                    ↓
        Bot opens in PM
                    ↓
        FSub check
                    ↓
        If joined → send file
                    ↓
        If not joined → FSub screen
    """

    if not message.from_user:
        return

    if message.chat.type.value != "private":
        return

    user_id = message.from_user.id

    try:
        message_id = int(message_id)
    except Exception:
        await message.reply_text(
            "❌ Invalid file ID."
        )
        return

    # --------------------------------------------------------
    # FSub
    # --------------------------------------------------------

    not_joined = await check_all_fsubs(
        client,
        user_id,
    )

    if not_joined:
        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=f"file_{message_id}",
        )
        return

    # --------------------------------------------------------
    # Database lookup
    # --------------------------------------------------------

    media = None

    try:
        media = await search_media(
            query=str(message_id),
            skip=0,
            limit=100,
            filters={},
        )

        # Exact message ID match.
        exact = None

        for item in media:
            if int(
                item.get("message_id", 0)
            ) == int(message_id):
                exact = item
                break

        media = exact

    except Exception as e:
        logger.warning(
            "Media lookup through search failed: %s",
            e,
        )

    # --------------------------------------------------------
    # Fallback direct Mongo collection
    # --------------------------------------------------------

    if media is None:
        try:
            from database import media_collection

            if media_collection is not None:
                media = await media_collection.find_one(
                    {
                        "channel_id": DATABASE_CHANNEL_ID,
                        "message_id": int(message_id),
                    }
                )

                if media is None:
                    media = await media_collection.find_one(
                        {
                            "message_id": int(message_id),
                        }
                    )

        except Exception as e:
            logger.exception(
                "Direct media lookup failed: %s",
                e,
            )

    if not media:
        await message.reply_text(
            "❌ <b>File not found.</b>\n\n"
            "The requested file may have been removed "
            "from the database.",
        )
        return

    # --------------------------------------------------------
    # Request limit
    # --------------------------------------------------------

    try:
        allowed = await can_use_movie(
            user_id
        )

    except TypeError:
        allowed = await can_use_movie(
            user_id=user_id
        )

    except Exception as e:
        logger.warning(
            "can_use_movie error: %s",
            e,
        )
        allowed = True

    if not allowed:
        await message.reply_text(
            "❌ <b>No requests available.</b>\n\n"
            "Please upgrade your plan or wait for "
            "your requests to reset.",
        )
        return

    # --------------------------------------------------------
    # Consume request
    # --------------------------------------------------------

    consumed = False

    try:
        consumed = await consume_request(
            user_id
        )

    except TypeError:
        try:
            consumed = await consume_request(
                user_id=user_id
            )
        except Exception as e:
            logger.warning(
                "consume_request error: %s",
                e,
            )

    except Exception as e:
        logger.warning(
            "consume_request error: %s",
            e,
        )

    # --------------------------------------------------------
    # Send file
    # --------------------------------------------------------

    sent = await send_database_file(
        client,
        message,
        media,
    )

    if not sent:

        # Restore request if we consumed it.
        if consumed:
            try:
                await restore_request(
                    user_id
                )
            except TypeError:
                try:
                    await restore_request(
                        user_id=user_id
                    )
                except Exception:
                    pass
            except Exception:
                pass

        await message.reply_text(
            "❌ <b>Failed to send the file.</b>\n\n"
            "Please try again later.",
        )
        return

    # --------------------------------------------------------
    # Remaining request information
    # --------------------------------------------------------

    try:
        remaining = await get_remaining_requests(
            user_id
        )

        await message.reply_text(
            f"✅ <b>File sent successfully!</b>\n\n"
            f"🎟 <b>Remaining requests:</b> {remaining}",
            reply_markup=InlineKeyboardMarkup(
                file_sent_buttons()
            ),
        )

    except Exception:
        await message.reply_text(
            "✅ <b>File sent successfully!</b>",
            reply_markup=InlineKeyboardMarkup(
                file_sent_buttons()
            ),
        )


# ============================================================
# SEND ALL
# ============================================================

async def handle_sendall_deep_link(
    client,
    message,
    session_id: str,
    page: int = 0,
):
    """
    Handles:

        /start sendall_SESSION_PAGE
    """

    if not message.from_user:
        return

    if message.chat.type.value != "private":
        return

    user_id = message.from_user.id

    # --------------------------------------------------------
    # FSub
    # --------------------------------------------------------

    not_joined = await check_all_fsubs(
        client,
        user_id,
    )

    if not_joined:
        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=(
                f"sendall_{session_id}_{int(page)}"
            ),
        )
        return

    # --------------------------------------------------------
    # Session
    # --------------------------------------------------------

    session = await get_search_session(
        session_id,
        user_id,
    )

    if not session:
        await message.reply_text(
            "❌ <b>Search session expired.</b>\n\n"
            "Please search again.",
        )
        return

    query = session.get("query", "")
    filters_data = session.get(
        "filters",
        {},
    ) or {}

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    results, has_next = await search_movies(
        query=query,
        page=int(page),
        filters=filters_data,
    )

    if not results:
        await message.reply_text(
            "❌ No files found on this page."
        )
        return

    # --------------------------------------------------------
    # Request check
    # --------------------------------------------------------

    try:
        allowed = await can_use_movie(
            user_id
        )
    except Exception:
        allowed = True

    if not allowed:
        await message.reply_text(
            "❌ <b>No requests available.</b>"
        )
        return

    # --------------------------------------------------------
    # Send files one by one
    # --------------------------------------------------------

    sent_count = 0

    for media in results:

        consumed = False

        try:
            consumed = await consume_request(
                user_id
            )
        except Exception:
            consumed = True

        if not consumed:
            break

        sent = await send_database_file(
            client,
            message,
            media,
        )

        if sent:
            sent_count += 1

        else:
            try:
                await restore_request(
                    user_id
                )
            except Exception:
                pass

    await message.reply_text(
        "📦 <b>Send All Complete</b>\n\n"
        f"✅ Files sent: <b>{sent_count}</b>\n"
        f"📄 Page: <b>{int(page) + 1}</b>",
    )


# ============================================================
# FILTERED RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    callback_query,
    session_id: str,
    page: int = 0,
):
    user_id = callback_query.from_user.id

    session = await get_search_session(
        session_id,
        user_id,
    )

    if not session:
        await callback_query.answer(
            "❌ Search session expired.",
            show_alert=True,
        )
        return

    query = session.get(
        "query",
        "",
    )

    filters_data = session.get(
        "filters",
        {},
    ) or {}

    # IMPORTANT:
    #
    # search_movies returns:
    #
    #     results, has_next
    #
    # NOT:
    #
    #     results, total_pages
    #

    results, has_next = await search_movies(
        query=query,
        page=int(page),
        filters=filters_data,
    )

    if not results:
        await callback_query.message.edit_text(
            "❌ <b>No results found with these filters.</b>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎛 Filters",
                            callback_data=(
                                f"search_filters_{session_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Clear Filters",
                            callback_data=(
                                f"filter_clear_{session_id}"
                            ),
                        )
                    ],
                ]
            ),
        )
        return

    bot_username = await get_bot_username_async(
        client
    )

    text = build_search_text(
        query,
        results,
        int(page) + 1,
        has_next,
        filters_data,
    )

    buttons = search_result_buttons(
        results,
        bot_username,
    )

    buttons.extend(
        pagination_buttons(
            int(page),
            has_next,
            session_id,
        )
    )

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# ============================================================
# PRIVATE MOVIE SEARCH
# ============================================================

@app_search_handler = None


def register_search_handlers(app):

    global app_search_handler
    app_search_handler = app

    # ========================================================
    # START / DEEP LINK HANDLER
    # ========================================================

    @app.on_message(
        filters.private
        & filters.command("start")
    )
    async def search_start_deep_link(
        client,
        message,
    ):
        """
        Deep links are normally handled by fsub.py.

        This handler exists only as a safe fallback for file
        and sendall payloads.
        """

        text = message.text or ""

        parts = text.split(
            maxsplit=1
        )

        if len(parts) < 2:
            return

        payload = parts[1].strip()

        if payload.startswith("file_"):

            try:
                message_id = int(
                    payload.split(
                        "_",
                        1,
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
                message_id,
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
                page,
            )

            return

    # ========================================================
    # MOVIE SEARCH
    # ========================================================
    #
    # IMPORTANT:
    #
    # Do NOT allow this handler to process slash commands.
    #
    # The old:
    #
    # ~filters.command([
    #     "start",
    #     "help",
    #     "premium",
    #     "account"
    # ])
    #
    # was unsafe because every other command could still
    # reach movie_search_handler.
    #
    # This custom filter rejects ANY message beginning with /.
    # ========================================================

    non_command_private_text = filters.create(
        lambda _, __, message: (
            message is not None
            and message.from_user is not None
            and message.chat is not None
            and getattr(
                message.chat.type,
                "value",
                str(message.chat.type),
            ) == "private"
            and bool(
                message.text
            )
            and not message.text.strip().startswith("/")
        )
    )

    @app.on_message(
        filters.private
        & filters.text
        & non_command_private_text
    )
    async def movie_search_handler(
        client,
        message,
    ):
        user = message.from_user

        if not user:
            return

        user_id = user.id

        query = clean_query(
            message.text or ""
        )

        if not query:
            return

        # ----------------------------------------------------
        # User
        # ----------------------------------------------------

        try:
            existing_user = await get_user(
                user_id
            )

            if not existing_user:
                await create_user(
                    user_id
                )

        except Exception as e:
            logger.warning(
                "User initialization error: %s",
                e,
            )

        # ----------------------------------------------------
        # FSub
        # ----------------------------------------------------

        try:
            not_joined = await check_all_fsubs(
                client,
                user_id,
            )

            if not_joined:
                await send_fsub_message(
                    client,
                    message,
                    not_joined,
                    deep_link=None,
                )
                return

        except Exception as e:
            logger.exception(
                "FSub search check failed: %s",
                e,
            )

        # ----------------------------------------------------
        # Request permission
        # ----------------------------------------------------

        try:
            allowed = await can_use_movie(
                user_id
            )

        except TypeError:
            try:
                allowed = await can_use_movie(
                    user_id=user_id
                )
            except Exception:
                allowed = True

        except Exception as e:
            logger.warning(
                "can_use_movie error: %s",
                e,
            )
            allowed = True

        if not allowed:
            try:
                remaining = await get_remaining_requests(
                    user_id
                )
            except Exception:
                remaining = 0

            await message.reply_text(
                "❌ <b>No movie requests available.</b>\n\n"
                f"🎟 Remaining: <b>{remaining}</b>\n\n"
                "Upgrade your plan to continue.",
            )
            return

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        try:
            results, has_next = await advanced_search(
                query=query,
                page=0,
                filters={},
            )

        except Exception as e:
            logger.exception(
                "Advanced search failed: %s",
                e,
            )

            await message.reply_text(
                "❌ <b>Search failed.</b>\n\n"
                "Please try again.",
            )
            return

        if not results:
            await message.reply_text(
                "❌ <b>No results found.</b>\n\n"
                f"🔎 Search: <code>"
                f"{escape_html(query)}"
                f"</code>"
            )
            return

        # ----------------------------------------------------
        # Record search
        # ----------------------------------------------------

        try:
            await record_search(
                user_id,
                query,
            )
        except TypeError:
            try:
                await record_search(
                    user_id=user_id,
                    query=query,
                )
            except Exception:
                pass
        except Exception:
            pass

        # ----------------------------------------------------
        # Create session
        # ----------------------------------------------------

        try:
            session_id = await create_session_for_search(
                user_id,
                query,
                {},
            )

        except Exception as e:
            logger.exception(
                "Search session creation failed: %s",
                e,
            )
            session_id = None

        # ----------------------------------------------------
        # Build result text
        # ----------------------------------------------------

        text = build_search_text(
            query,
            results,
            1,
            has_next,
            {},
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        bot_username = await get_bot_username_async(
            client
        )

        buttons = search_result_buttons(
            results,
            bot_username,
        )

        buttons.extend(
            pagination_buttons(
                page=0,
                has_next=has_next,
                session_id=session_id,
            )
        )

        # ----------------------------------------------------
        # Send results
        # ----------------------------------------------------

        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
            disable_web_page_preview=True,
        )


    # ========================================================
    # SEARCH PAGINATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_page_-?\d+$"
        )
    )
    async def search_page_callback(
        client,
        callback_query,
    ):
        user_id = callback_query.from_user.id

        try:
            page = int(
                callback_query.data.split(
                    "_"
                )[-1]
            )
        except Exception:
            await callback_query.answer(
                "Invalid page.",
                show_alert=True,
            )
            return

        # We need session ID from message.
        #
        # Pagination callback normally needs the session.
        # If session ID was not embedded in old callback,
        # attempt to use stored session mapping.
        #
        # Current buttons use search_page_<page>, so recover
        # the latest user session.

        session = None

        try:
            from database import search_sessions_collection

            if search_sessions_collection is not None:
                session = await search_sessions_collection.find_one(
                    {
                        "user_id": user_id,
                    },
                    sort=[
                        (
                            "created_at",
                            -1,
                        )
                    ],
                )

        except Exception:
            pass

        if not session:
            await callback_query.answer(
                "❌ Search session expired.",
                show_alert=True,
            )
            return

        session_id = str(
            session.get("_id")
        )

        await callback_query.answer()

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            page,
        )


    # ========================================================
    # FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_filters_.+"
        )
    )
    async def search_filters_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "search_filters_".__len__():
        ]

        session = await get_search_session(
            session_id,
            callback_query.from_user.id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        await callback_query.answer()

        await callback_query.message.edit_text(
            "🎛 <b>Search Filters</b>\n\n"
            "Choose a filter:",
            reply_markup=InlineKeyboardMarkup(
                filter_menu_buttons(
                    session_id
                )
            ),
        )


    # ========================================================
    # BACK TO SEARCH
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_back_.+"
        )
    )
    async def search_back_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "search_back_".__len__():
        ]

        await callback_query.answer()

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0,
        )


    # ========================================================
    # LANGUAGE FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_language_.+"
        )
    )
    async def language_filter_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_language_".__len__():
        ]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        options = []

        try:
            data = await get_filter_options(
                session.get("query", ""),
                session.get("filters", {}) or {},
            )

            options = (
                data.get("languages")
                or data.get("language")
                or []
            )

        except Exception as e:
            logger.warning(
                "Language options error: %s",
                e,
            )

        await callback_query.answer()

        await callback_query.message.edit_text(
            "🌐 <b>Select Language</b>",
            reply_markup=InlineKeyboardMarkup(
                language_filter_buttons(
                    session_id,
                    options,
                )
            ),
        )


    # ========================================================
    # YEAR FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_year_.+"
        )
    )
    async def year_filter_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_year_".__len__():
        ]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        options = []

        try:
            data = await get_filter_options(
                session.get("query", ""),
                session.get("filters", {}) or {},
            )

            options = (
                data.get("years")
                or data.get("year")
                or []
            )

        except Exception:
            pass

        await callback_query.answer()

        await callback_query.message.edit_text(
            "📅 <b>Select Year</b>",
            reply_markup=InlineKeyboardMarkup(
                year_filter_buttons(
                    session_id,
                    options,
                )
            ),
        )


    # ========================================================
    # QUALITY FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_quality_.+"
        )
    )
    async def quality_filter_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_quality_".__len__():
        ]

        session = await get_search_session(
            session_id,
            callback_query.from_user.id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        options = []

        try:
            data = await get_filter_options(
                session.get("query", ""),
                session.get("filters", {}) or {},
            )

            options = (
                data.get("qualities")
                or data.get("quality")
                or []
            )

        except Exception:
            pass

        await callback_query.answer()

        await callback_query.message.edit_text(
            "🎞 <b>Select Quality</b>",
            reply_markup=InlineKeyboardMarkup(
                quality_filter_buttons(
                    session_id,
                    options,
                )
            ),
        )


    # ========================================================
    # SEASON FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_season_.+"
        )
    )
    async def season_filter_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_season_".__len__():
        ]

        session = await get_search_session(
            session_id,
            callback_query.from_user.id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        options = []

        try:
            data = await get_filter_options(
                session.get("query", ""),
                session.get("filters", {}) or {},
            )

            options = (
                data.get("seasons")
                or data.get("season")
                or []
            )

        except Exception:
            pass

        await callback_query.answer()

        await callback_query.message.edit_text(
            "📺 <b>Select Season</b>",
            reply_markup=InlineKeyboardMarkup(
                season_filter_buttons(
                    session_id,
                    options,
                )
            ),
        )


    # ========================================================
    # EPISODE FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_episode_.+"
        )
    )
    async def episode_filter_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_episode_".__len__():
        ]

        session = await get_search_session(
            session_id,
            callback_query.from_user.id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        options = []

        try:
            data = await get_filter_options(
                session.get("query", ""),
                session.get("filters", {}) or {},
            )

            options = (
                data.get("episodes")
                or data.get("episode")
                or []
            )

        except Exception:
            pass

        await callback_query.answer()

        await callback_query.message.edit_text(
            "🎬 <b>Select Episode</b>",
            reply_markup=InlineKeyboardMarkup(
                episode_filter_buttons(
                    session_id,
                    options,
                )
            ),
        )


    # ========================================================
    # SET FILTER
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setfilter_.+"
        )
    )
    async def set_filter_callback(
        client,
        callback_query,
    ):
        parts = callback_query.data.split(
            "_",
            3,
        )

        if len(parts) < 4:
            await callback_query.answer(
                "Invalid filter.",
                show_alert=True,
            )
            return

        filter_name = parts[1]
        session_id = parts[2]
        value = parts[3]

        user_id = callback_query.from_user.id

        session = await get_search_session(
            session_id,
            user_id,
        )

        if not session:
            await callback_query.answer(
                "❌ Session expired.",
                show_alert=True,
            )
            return

        filters_data = session.get(
            "filters",
            {},
        ) or {}

        # Convert numeric values.
        if filter_name in (
            "year",
            "season",
            "episode",
        ):
            try:
                value = int(value)
            except Exception:
                pass

        filters_data[
            filter_name
        ] = value

        try:
            await update_search_session_filters(
                session_id,
                user_id,
                filters_data,
            )

        except TypeError:
            try:
                await update_search_session_filters(
                    session_id=session_id,
                    user_id=user_id,
                    filters=filters_data,
                )
            except Exception as e:
                logger.warning(
                    "Session filter update failed: %s",
                    e,
                )

        except Exception as e:
            logger.warning(
                "Session filter update failed: %s",
                e,
            )

        await callback_query.answer(
            f"✅ {filter_name.title()} set."
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0,
        )


    # ========================================================
    # CLEAR FILTERS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_clear_.+"
        )
    )
    async def clear_filters_callback(
        client,
        callback_query,
    ):
        session_id = callback_query.data[
            "filter_clear_".__len__():
        ]

        user_id = callback_query.from_user.id

        try:
            await update_search_session_filters(
                session_id,
                user_id,
                {},
            )

        except TypeError:
            try:
                await update_search_session_filters(
                    session_id=session_id,
                    user_id=user_id,
                    filters={},
                )
            except Exception:
                pass

        except Exception:
            pass

        await callback_query.answer(
            "✅ Filters cleared."
        )

        await refresh_filtered_results(
            client,
            callback_query,
            session_id,
            0,
        )


    # ========================================================
    # SEND ALL CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^search_sendall_.+"
        )
    )
    async def search_sendall_callback(
        client,
        callback_query,
    ):
        data = callback_query.data

        payload = data[
            "search_sendall_".__len__():
        ]

        parts = payload.rsplit(
            "_",
            1,
        )

        if len(parts) != 2:
            await callback_query.answer(
                "Invalid send-all request.",
                show_alert=True,
            )
            return

        session_id = parts[0]

        try:
            page = int(parts[1])
        except Exception:
            page = 0

        await callback_query.answer()

        bot_username = await get_bot_username_async(
            client
        )

        url = build_sendall_deep_link(
            bot_username,
            session_id,
            page,
        )

        await callback_query.message.reply_text(
            "📦 <b>Send All</b>\n\n"
            "Open the bot in private chat to receive "
            "all files from this page.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 Open Send All",
                            url=url,
                        )
                    ]
                ]
            ),
        )


    # ========================================================
    # FILE CALLBACK
    # ========================================================
    #
    # If your old result buttons used callback_data instead
    # of URLs, this keeps them working.
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_.+"
        )
    )
    async def file_callback(
        client,
        callback_query,
    ):
        try:
            message_id = int(
                callback_query.data.split(
                    "_",
                    1,
                )[1]
            )

        except Exception:
            await callback_query.answer(
                "❌ Invalid file.",
                show_alert=True,
            )
            return

        # A callback in a group MUST NOT perform FSub or send
        # the file there.
        #
        # Instead provide a PM deep link.

        bot_username = await get_bot_username_async(
            client
        )

        url = build_file_deep_link(
            bot_username,
            message_id,
        )

        await callback_query.answer(
            "Open the bot in private chat.",
            show_alert=False,
        )

        try:
            await callback_query.message.reply_text(
                "🎬 <b>Open Private Chat</b>\n\n"
                "Please open the bot in private chat "
                "to receive your file.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📥 Get File",
                                url=url,
                            )
                        ]
                    ]
                ),
            )

        except Exception as e:
            logger.warning(
                "Failed to send PM button: %s",
                e,
            )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "register_search_handlers",
    "search_movies",
    "advanced_search",
    "build_search_text",
    "handle_file_deep_link",
    "handle_sendall_deep_link",
    "refresh_filtered_results",
]
