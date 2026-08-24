import asyncio
import logging
import os
import re

from pyrogram import filters

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
    premium_buttons,
    home_buttons,
    file_sent_buttons
)

from utils.helpers import (
    escape_html
)


logger = logging.getLogger(__name__)


# ============================================================
# SETTINGS
# ============================================================

FILE_DELETE_SECONDS = 300


# ============================================================
# AUTO DELETE SENT FILE
# ============================================================

async def delete_after_five_minutes(
    client,
    chat_id,
    message_id
):

    try:

        await asyncio.sleep(
            FILE_DELETE_SECONDS
        )

        await client.delete_messages(
            chat_id=chat_id,
            message_ids=message_id
        )

        logger.info(
            "Deleted sent file message %s "
            "from user %s after 5 minutes.",
            message_id,
            chat_id
        )

    except Exception as e:

        logger.warning(
            "Could not delete sent file %s "
            "from user %s: %s",
            message_id,
            chat_id,
            e
        )


# ============================================================
# TMDB
# ============================================================

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    ""
)


async def get_tmdb_metadata(query):

    if not TMDB_API_KEY:

        return {
            "title": query,
            "year": "",
            "language": "",
            "rating": "",
            "genres": []
        }

    try:

        clean_query = re.sub(
            r"\bS\d{1,2}E\d{1,3}\b",
            "",
            query,
            flags=re.IGNORECASE
        )

        clean_query = re.sub(
            r"\b(480p|540p|576p|720p|1080p|2160p|4K|WEB[- ]?DL|WEB[- ]?Rip|BluRay|HDRip|HEVC|H\.?264|H\.?265)\b",
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

        import requests

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

        title = (
            item.get("title")
            if media_type == "movie"
            else item.get("name")
        ) or clean_query

        release_date = (
            item.get("release_date")
            if media_type == "movie"
            else item.get("first_air_date")
        ) or ""

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

        rating = item.get(
            "vote_average"
        )

        if rating:

            rating = f"{float(rating):.1f}/10"

        else:

            rating = ""

        genres = []

        genre_ids = item.get(
            "genre_ids",
            []
        )

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

        for genre_id in genre_ids:

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
# FORMAT SEARCH RESULT TEXT
# ============================================================

def build_search_text(
    query,
    results,
    page,
    metadata
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
        "🔎 <b>Search Results</b>\n\n"
    )

    text += (
        f"🎬 <b>{escape_html(title)}</b>\n"
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

    text += "\n"

    text += (
        f"📦 <b>Results shown:</b> "
        f"{len(results)}\n\n"
    )

    text += (
        "👇 <b>Select the file you want:</b>\n\n"
    )

    text += (
        "Powered by "
        "<b>@Aero_Unity</b>"
    )

    return text


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
        # GET / CREATE USER
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
        # CHECK REQUEST BALANCE
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
        # SEARCHING MESSAGE
        # ----------------------------------------------------

        wait = await message.reply_text(
            "🔎 <b>Searching...</b>"
        )

        # ----------------------------------------------------
        # SEARCH DATABASE
        # ----------------------------------------------------

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

            await wait.edit_text(
                "❌ <b>Search failed.</b>\n\n"
                "Please try again."
            )

            return

        # ----------------------------------------------------
        # NO RESULTS
        # ----------------------------------------------------

        if not results:

            await wait.edit_text(
                "😕 <b>No results found.</b>\n\n"
                "🔎 Search:\n"
                f"<code>{escape_html(query)}</code>\n\n"
                "Try another movie or series name."
            )

            return

        # ----------------------------------------------------
        # CREATE SEARCH SESSION
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

            await wait.edit_text(
                "❌ <b>Could not create search session.</b>\n"
                "Please try again."
            )

            return

        # ----------------------------------------------------
        # TMDB METADATA
        # ----------------------------------------------------

        metadata = await get_tmdb_metadata(
            query
        )

        # ----------------------------------------------------
        # SHOW RESULTS
        # ----------------------------------------------------

        await wait.edit_text(

            build_search_text(
                query=query,
                results=results,
                page=0,
                metadata=metadata
            ),

            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=0,
                has_next=has_next
            )
        )


    # ========================================================
    # SEARCH PAGINATION
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

        if not results:

            await callback.answer(
                "No more results.",
                show_alert=True
            )

            return

        metadata = await get_tmdb_metadata(
            query
        )

        await callback.message.edit_text(

            build_search_text(
                query=query,
                results=results,
                page=page,
                metadata=metadata
            ),

            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=page,
                has_next=has_next
            )
        )

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

        # ----------------------------------------------------
        # GET SESSION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SEARCH CURRENT PAGE
        # ----------------------------------------------------

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
        # GET USER
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
        # CHECK BALANCE
        # ----------------------------------------------------

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
                f"📦 Files to send: <b>{required}</b>\n"
                f"🎟 Remaining requests: "
                f"<b>{remaining}</b>\n\n"
                "Please activate Premium to get "
                "more requests.",
                reply_markup=premium_buttons()
            )

            return

        # ----------------------------------------------------
        # ANSWER CALLBACK
        # ----------------------------------------------------

        await callback.answer(
            "📤 Sending all files..."
        )

        # ----------------------------------------------------
        # SEND FILES
        # ----------------------------------------------------

        for item in results:

            message_id = item.get(
                "message_id"
            )

            if not message_id:
                continue

            # ------------------------------------------------
            # CONSUME REQUEST
            # ------------------------------------------------

            consumed = await consume_request(
                user_id
            )

            if not consumed:
                break

            try:

                sent_message = await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=DATABASE_CHANNEL_ID,
                    message_id=int(message_id)
                )

                # --------------------------------------------
                # ADD UPDATES BUTTON
                # --------------------------------------------

                try:

                    await sent_message.edit_reply_markup(
                        reply_markup=file_sent_buttons()
                    )

                except Exception as e:

                    logger.warning(
                        "Could not add Updates button "
                        "to sent file: %s",
                        e
                    )

                # --------------------------------------------
                # DELETE AFTER 5 MINUTES
                # --------------------------------------------

                asyncio.create_task(
                    delete_after_five_minutes(
                        client=client,
                        chat_id=user_id,
                        message_id=sent_message.id
                    )
                )

            except Exception as e:

                logger.exception(
                    "SEND ALL failed for message %s: %s",
                    message_id,
                    e
                )

                await restore_request(
                    user_id
                )

        # ----------------------------------------------------
        # DO NOT SEND COMPLETED MESSAGE
        # ----------------------------------------------------


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
        # GET USER
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
        # CHECK REQUEST BALANCE
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
        # CONSUME REQUEST
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
        # SEND FILE
        # ----------------------------------------------------

        try:

            sent_message = await client.copy_message(
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
        # ADD UPDATES BUTTON
        # ----------------------------------------------------

        try:

            await sent_message.edit_reply_markup(
                reply_markup=file_sent_buttons()
            )

        except Exception as e:

            logger.warning(
                "Could not add Updates button "
                "to sent file: %s",
                e
            )

        # ----------------------------------------------------
        # DELETE AFTER 5 MINUTES
        # ----------------------------------------------------

        asyncio.create_task(
            delete_after_five_minutes(
                client=client,
                chat_id=user_id,
                message_id=sent_message.id
            )
        )
