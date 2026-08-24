import asyncio
import logging
import os
import re
import time

from pyrogram import filters
from pyrogram.errors import MessageNotModified

from config import (
    DATABASE_CHANNEL_ID,
    MAX_RESULTS
)

from database import (
    get_user,
    create_user,
    update_user,
    consume_request,
    restore_request,
    create_search_session,
    get_search_session
)

from premium import (
    can_use_movie,
    get_remaining_requests
)

from search import search_movies

from utils.buttons import (
    search_result_buttons,
    premium_buttons
)

from utils.helpers import (
    escape_html
)


logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS
# ============================================================

DELETE_AFTER = 300


# ============================================================
# TMDB
# ============================================================

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    ""
)


async def get_tmdb_metadata(query):

    empty_metadata = {
        "title": query,
        "year": "",
        "language": "",
        "rating": "",
        "genres": []
    }

    if not TMDB_API_KEY:
        return empty_metadata

    try:

        clean_query = re.sub(
            r"\bS\d{1,2}E\d{1,3}\b",
            "",
            query,
            flags=re.IGNORECASE
        )

        clean_query = re.sub(
            r"\b(480p|540p|576p|720p|1080p|2160p|4K|"
            r"WEB[- ]?DL|WEB[- ]?Rip|BluRay|HDRip|"
            r"HEVC|H\.?264|H\.?265)\b",
            "",
            clean_query,
            flags=re.IGNORECASE
        )

        clean_query = re.sub(
            r"\s+",
            " ",
            clean_query
        ).strip()

        if not clean_query:
            clean_query = query

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API_KEY}"
            f"&query={clean_query}"
        )

        # requests is deliberately imported here so that
        # a missing dependency does not crash bot startup.
        try:
            import requests
        except ImportError:

            logger.error(
                "The 'requests' package is missing. "
                "Add requests to requirements.txt."
            )

            return {
                "title": clean_query,
                "year": "",
                "language": "",
                "rating": "",
                "genres": []
            }

        response = await asyncio.to_thread(
            requests.get,
            url,
            timeout=10
        )

        if response.status_code != 200:

            logger.warning(
                "TMDB returned HTTP %s",
                response.status_code
            )

            return {
                "title": clean_query,
                "year": "",
                "language": "",
                "rating": "",
                "genres": []
            }

        data = response.json()

        results = data.get(
            "results",
            []
        )

        if not results:
            return {
                "title": clean_query,
                "year": "",
                "language": "",
                "rating": "",
                "genres": []
            }

        item = None

        for result in results:

            if result.get("media_type") in (
                "movie",
                "tv"
            ):

                item = result
                break

        if not item:
            return {
                "title": clean_query,
                "year": "",
                "language": "",
                "rating": "",
                "genres": []
            }

        media_type = item.get(
            "media_type"
        )

        if media_type == "movie":
            title = item.get("title")
            release_date = item.get("release_date")
        else:
            title = item.get("name")
            release_date = item.get("first_air_date")

        title = title or clean_query
        release_date = release_date or ""

        year = ""

        if release_date:
            year = release_date[:4]

        language_code = (
            item.get("original_language")
            or ""
        )

        language_map = {

            "en": "English",
            "hi": "Hindi",
            "ko": "Korean",
            "ja": "Japanese",
            "zh": "Chinese",
            "ta": "Tamil",
            "te": "Telugu",
            "ml": "Malayalam",
            "kn": "Kannada",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian"
        }

        language = language_map.get(
            language_code,
            language_code.upper()
            if language_code
            else ""
        )

        rating_value = item.get(
            "vote_average"
        )

        if rating_value:
            rating = f"{float(rating_value):.1f}/10"
        else:
            rating = ""

        genre_map = {

            28: "Action",
            12: "Adventure",
            16: "Animation",
            35: "Comedy",
            80: "Crime",
            99: "Documentary",
            18: "Drama",
            10751: "Family",
            14: "Fantasy",
            36: "History",
            27: "Horror",
            10402: "Music",
            9648: "Mystery",
            10749: "Romance",
            878: "Sci-Fi",
            10770: "TV Movie",
            53: "Thriller",
            10752: "War",
            37: "Western",
            10759: "Action & Adventure",
            10762: "Kids",
            10763: "News",
            10764: "Reality",
            10765: "Sci-Fi & Fantasy",
            10766: "Soap",
            10767: "Talk",
            10768: "War & Politics"
        }

        genres = []

        for genre_id in item.get(
            "genre_ids",
            []
        ):

            genre_name = genre_map.get(
                genre_id
            )

            if genre_name:
                genres.append(
                    genre_name
                )

        return {
            "title": title,
            "year": year,
            "language": language,
            "rating": rating,
            "genres": genres
        }

    except Exception as e:

        logger.exception(
            "TMDB metadata lookup failed: %s",
            e
        )

        return {
            "title": query,
            "year": "",
            "language": "",
            "rating": "",
            "genres": []
        }


# ============================================================
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    metadata,
    search_time=None
):

    title = metadata.get(
        "title"
    ) or query

    year = metadata.get(
        "year"
    )

    language = metadata.get(
        "language"
    )

    rating = metadata.get(
        "rating"
    )

    genres = metadata.get(
        "genres"
    ) or []

    text = (
        f"🎬 <b>{escape_html(str(title))}</b>\n"
    )

    if year:

        text += (
            f"📅 <b>Year:</b> "
            f"{escape_html(str(year))}\n"
        )

    if language:

        text += (
            f"🗣 <b>Language:</b> "
            f"{escape_html(str(language))}\n"
        )

    if rating:

        text += (
            f"⭐ <b>Rating:</b> "
            f"{escape_html(str(rating))}\n"
        )

    if genres:

        text += (
            f"🎭 <b>Genres:</b> "
            f"{escape_html(', '.join(genres))}\n"
        )

    if search_time is not None:

        text += (
            f"\n⏱ <b>Results shown in:</b> "
            f"<b>{search_time:.2f}s</b>\n"
        )

    text += (
        f"\n📦 <b>Results shown:</b> "
        f"<b>{len(results)}</b>\n\n"
    )

    text += (
        "📥 <b>Your requested files are here 👇</b>\n\n"
    )

    text += (
        "Powered by "
        "<b>@Aero_Unity</b>"
    )

    return text


# ============================================================
# DELETE FILES AFTER 5 MINUTES
# ============================================================

async def delete_messages_after_delay(
    client,
    chat_id,
    message_ids,
    delay=DELETE_AFTER
):

    await asyncio.sleep(delay)

    try:

        valid_ids = [
            int(message_id)
            for message_id in message_ids
            if message_id
        ]

        if valid_ids:

            await client.delete_messages(
                chat_id=chat_id,
                message_ids=valid_ids
            )

            logger.info(
                "Deleted %s temporary message(s) "
                "from user %s",
                len(valid_ids),
                chat_id
            )

    except Exception as e:

        logger.warning(
            "Could not delete temporary messages "
            "for %s: %s",
            chat_id,
            e
        )


# ============================================================
# SEND FILE WARNING
# ============================================================

async def send_file_warning(
    client,
    user_id,
    file_message_ids
):

    warning = await client.send_message(

        user_id,

        "⚠️ <b>Your requested file is here 👇</b>\n\n"

        "🗑 <b>This file will be deleted "
        "automatically after 5 minutes.</b>\n\n"

        "💾 Please save it before it is deleted."
    )

    all_message_ids = list(
        file_message_ids
    )

    all_message_ids.append(
        warning.id
    )

    asyncio.create_task(
        delete_messages_after_delay(
            client=client,
            chat_id=user_id,
            message_ids=all_message_ids
        )
    )

    return warning


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # NORMAL TEXT SEARCH
    # ========================================================

    @app.on_message(
        filters.text
        & ~filters.command(
            [
                "start",
                "help",
                "premium",
                "plans",
                "myplan",
                "user",
                "premiumuser",
                "activate",
                "deactivate",
                "id",
                "addpremium",
                "removepremium",
                "stats",
                "index",
                "indexstatus",
                "resetindex",
                "broadcast"
            ]
        )
    )
    async def movie_search_handler(
        client,
        message
    ):

        user_id = message.from_user.id

        query = (
            message.text
            or ""
        ).strip()

        if not query:
            return

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    message.from_user.first_name
                    or "User"
                ),
                username=(
                    message.from_user.username
                    or ""
                )
            )

        else:

            await update_user(
                user_id=user_id,
                first_name=(
                    message.from_user.first_name
                    or ""
                ),
                username=(
                    message.from_user.username
                    or ""
                )
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        if not can_use_movie(user):

            await message.reply_text(
                "🚫 <b>Your movie request limit "
                "has been reached.</b>\n\n"
                "💎 Please activate a Premium plan "
                "to continue receiving files.",
                reply_markup=premium_buttons()
            )

            return

        # ----------------------------------------------------
        # SEARCHING
        # ----------------------------------------------------

        wait = await message.reply_text(
            "🔎 <b>Searching...</b>"
        )

        search_start = time.monotonic()

        try:

            results, has_next = await search_movies(
                query=query,
                page=0
            )

        except Exception as e:

            logger.exception(
                "Movie search failed: %s",
                e
            )

            try:

                await wait.edit_text(
                    "❌ <b>Search failed.</b>\n\n"
                    "Please try again."
                )

            except MessageNotModified:
                pass

            return

        search_time = (
            time.monotonic()
            - search_start
        )

        # ----------------------------------------------------
        # NO RESULTS
        # ----------------------------------------------------

        if not results:

            try:

                await wait.edit_text(
                    "😕 <b>No results found.</b>\n\n"
                    f"🔎 Search:\n"
                    f"<code>{escape_html(query)}</code>\n\n"
                    "Try another movie or series."
                )

            except MessageNotModified:
                pass

            return

        # ----------------------------------------------------
        # SEARCH SESSION
        # ----------------------------------------------------

        try:

            session_id = await create_search_session(
                user_id=user_id,
                query=query
            )

        except Exception as e:

            logger.exception(
                "Could not create search session: %s",
                e
            )

            try:

                await wait.edit_text(
                    "❌ <b>Could not create "
                    "search session.</b>\n"
                    "Please try again."
                )

            except MessageNotModified:
                pass

            return

        # ----------------------------------------------------
        # TMDB
        # ----------------------------------------------------

        metadata = await get_tmdb_metadata(
            query
        )

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        try:

            await wait.edit_text(

                build_search_text(
                    query=query,
                    results=results,
                    page=0,
                    metadata=metadata,
                    search_time=search_time
                ),

                reply_markup=search_result_buttons(
                    results=results,
                    session_id=session_id,
                    page=0,
                    has_next=has_next
                )
            )

        except MessageNotModified:

            pass


    # ========================================================
    # PAGINATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^searchpage_[a-fA-F0-9]+_\d+$"
        )
    )
    async def search_page_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        try:

            parts = callback.data.split("_")

            session_id = parts[1]

            page = int(
                parts[2]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid search page.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=user_id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        query = (
            session.get(
                "query",
                ""
            )
        ).strip()

        if not query:

            await callback.answer(
                "Search query not found.",
                show_alert=True
            )

            return

        search_start = time.monotonic()

        try:

            results, has_next = await search_movies(
                query=query,
                page=page
            )

        except Exception as e:

            logger.exception(
                "Pagination search failed: %s",
                e
            )

            await callback.answer(
                "Search failed.",
                show_alert=True
            )

            return

        search_time = (
            time.monotonic()
            - search_start
        )

        if not results:

            await callback.answer(
                "No more results.",
                show_alert=True
            )

            return

        metadata = await get_tmdb_metadata(
            query
        )

        try:

            await callback.message.edit_text(

                build_search_text(
                    query=query,
                    results=results,
                    page=page,
                    metadata=metadata,
                    search_time=search_time
                ),

                reply_markup=search_result_buttons(
                    results=results,
                    session_id=session_id,
                    page=page,
                    has_next=has_next
                )
            )

        except MessageNotModified:

            pass

        await callback.answer()


    # ========================================================
    # SEND ALL
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^sendall_[a-fA-F0-9]+_\d+$"
        )
    )
    async def send_all_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        try:

            parts = callback.data.split("_")

            session_id = parts[1]

            page = int(
                parts[2]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid request.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=user_id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        query = (
            session.get(
                "query",
                ""
            )
        ).strip()

        if not query:

            await callback.answer(
                "Search query not found.",
                show_alert=True
            )

            return

        try:

            results, has_next = await search_movies(
                query=query,
                page=page
            )

        except Exception as e:

            logger.exception(
                "SEND ALL search failed: %s",
                e
            )

            await callback.answer(
                "Search failed.",
                show_alert=True
            )

            return

        if not results:

            await callback.answer(
                "No files found.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    callback.from_user.first_name
                    or "User"
                ),
                username=(
                    callback.from_user.username
                    or ""
                )
            )

        remaining = get_remaining_requests(
            user
        )

        required = len(results)

        if remaining < required:

            await callback.answer(
                f"SEND ALL needs {required} "
                f"requests. You have {remaining}.",
                show_alert=True
            )

            await callback.message.reply_text(
                "💎 <b>Not enough requests</b>\n\n"
                f"📦 Files: <b>{required}</b>\n"
                f"🎟 Remaining: <b>{remaining}</b>\n\n"
                "Please activate Premium.",
                reply_markup=premium_buttons()
            )

            return

        await callback.answer(
            "📤 Sending all files..."
        )

        # ----------------------------------------------------
        # SEND FILES
        # ----------------------------------------------------

        sent_ids = []

        sent_count = 0

        failed_count = 0

        for item in results:

            message_id = item.get(
                "message_id"
            )

            if not message_id:

                failed_count += 1

                continue

            consumed = await consume_request(
                user_id
            )

            if not consumed:

                failed_count += 1

                break

            try:

                sent_file = await client.copy_message(

                    chat_id=user_id,

                    from_chat_id=DATABASE_CHANNEL_ID,

                    message_id=int(message_id)
                )

                sent_ids.append(
                    sent_file.id
                )

                sent_count += 1

            except Exception as e:

                logger.exception(
                    "SEND ALL failed for message %s: %s",
                    message_id,
                    e
                )

                await restore_request(
                    user_id
                )

                failed_count += 1

        # ----------------------------------------------------
        # NOTHING SENT
        # ----------------------------------------------------

        if not sent_ids:

            await client.send_message(
                user_id,
                "❌ <b>No files could be sent.</b>\n\n"
                "Your requests were restored for "
                "the failed files."
            )

            return

        # ----------------------------------------------------
        # WARNING + DELETE TIMER
        # ----------------------------------------------------

        warning = await client.send_message(

            user_id,

            "⚠️ <b>Your requested files are here 👇</b>\n\n"

            f"✅ <b>{sent_count}</b> file(s) sent.\n\n"

            "🗑 <b>These files will be deleted "
            "automatically after 5 minutes.</b>\n\n"

            "💾 Please save them before they are deleted."
        )

        delete_ids = list(
            sent_ids
        )

        delete_ids.append(
            warning.id
        )

        asyncio.create_task(
            delete_messages_after_delay(
                client=client,
                chat_id=user_id,
                message_ids=delete_ids
            )
        )


    # ========================================================
    # FILE SELECTION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_\d+$"
        )
    )
    async def file_callback(
        client,
        callback
    ):

        user_id = callback.from_user.id

        try:

            message_id = int(
                callback.data.split("_")[1]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid file.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            user = await create_user(
                user_id=user_id,
                first_name=(
                    callback.from_user.first_name
                    or "User"
                ),
                username=(
                    callback.from_user.username
                    or ""
                )
            )

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        if not can_use_movie(user):

            await callback.answer(
                "Your request limit is finished.",
                show_alert=True
            )

            await callback.message.reply_text(
                "💎 <b>Premium Required</b>\n\n"
                "Your available movie requests "
                "have been used.\n\n"
                "Choose a Premium plan to continue.",
                reply_markup=premium_buttons()
            )

            return

        # ----------------------------------------------------
        # CONSUME
        # ----------------------------------------------------

        consumed = await consume_request(
            user_id
        )

        if not consumed:

            await callback.answer(
                "No requests remaining.",
                show_alert=True
            )

            await callback.message.reply_text(
                "💎 <b>Premium Required</b>\n\n"
                "Please activate a Premium plan.",
                reply_markup=premium_buttons()
            )

            return

        await callback.answer(
            "📤 Sending your file..."
        )

        # ----------------------------------------------------
        # COPY FILE
        # ----------------------------------------------------

        try:

            sent_file = await client.copy_message(

                chat_id=user_id,

                from_chat_id=DATABASE_CHANNEL_ID,

                message_id=message_id
            )

        except Exception as e:

            logger.exception(
                "File delivery failed: %s",
                e
            )

            await restore_request(
                user_id
            )

            await callback.message.reply_text(
                "❌ <b>File delivery failed.</b>\n\n"
                "Your movie request has been restored.\n"
                "Please try again."
            )

            return

        # ----------------------------------------------------
        # WARNING
        # ----------------------------------------------------

        warning = await client.send_message(

            user_id,

            "⚠️ <b>Your requested file is here 👇</b>\n\n"

            "🗑 <b>This file will be deleted "
            "automatically after 5 minutes.</b>\n\n"

            "💾 Please save it before it is deleted."
        )

        # ----------------------------------------------------
        # DELETE TIMER
        # ----------------------------------------------------

        asyncio.create_task(
            delete_messages_after_delay(

                client=client,

                chat_id=user_id,

                message_ids=[
                    sent_file.id,
                    warning.id
                ]
            )
        )
