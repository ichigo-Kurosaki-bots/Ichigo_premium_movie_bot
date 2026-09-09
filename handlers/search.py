import asyncio
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import json

from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from config import (
    DATABASE_CHANNEL_ID,
    OWNER_ID
)

from database import (
    get_user,
    create_user,
    update_user,
    consume_request,
    restore_request,
    create_search_session,
    get_search_session,
    update_search_session_filters,
    get_search_session_filters,
    record_search
)

from premium import (
    can_use_movie,
    get_remaining_requests
)

from search import (
    search_movies,
    get_filter_options
)

from utils.buttons import (
    search_result_buttons,
    premium_buttons,
    file_sent_buttons,
    filter_menu_buttons,
    language_filter_buttons,
    year_filter_buttons,
    season_filter_buttons,
    episode_filter_buttons
)

from utils.helpers import (
    escape_html
)

from handlers.fsub import (
    check_all_fsubs,
    send_fsub_message
)

logger = logging.getLogger(__name__)

FILE_DELETE_AFTER = 300

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY",
    ""
)


# ============================================================
# FILTER HELPERS
# ============================================================

def normalize_filters(filters_data=None):
    """
    Normalize all search filters.

    Supported:
        language
        year
        season
        episode
    """

    if not isinstance(filters_data, dict):
        return {}

    result = {}

    language = filters_data.get("language")
    year = filters_data.get("year")
    season = filters_data.get("season")
    episode = filters_data.get("episode")

    if language:
        result["language"] = str(language).strip()

    if year not in (None, ""):
        try:
            year = int(year)

            if 1960 <= year <= 2026:
                result["year"] = year

        except (TypeError, ValueError):
            pass

    if season not in (None, ""):
        try:
            season = int(season)

            if 1 <= season <= 20:
                result["season"] = season

        except (TypeError, ValueError):
            pass

    if episode not in (None, ""):
        try:
            episode = int(episode)

            if 1 <= episode <= 50:
                result["episode"] = episode

        except (TypeError, ValueError):
            pass

    return result


def filters_to_text(filters_data):
    """
    Create a small readable filter description.
    """

    filters_data = normalize_filters(
        filters_data
    )

    parts = []

    if filters_data.get("language"):
        parts.append(
            f"Language: {escape_html(str(filters_data['language']))}"
        )

    if filters_data.get("year"):
        parts.append(
            f"Year: {filters_data['year']}"
        )

    if filters_data.get("season"):
        parts.append(
            f"Season: {filters_data['season']}"
        )

    if filters_data.get("episode"):
        parts.append(
            f"Episode: {filters_data['episode']}"
        )

    if not parts:
        return ""

    return " | ".join(parts)


# ============================================================
# TMDB
# ============================================================

def empty_tmdb_metadata(query):

    return {
        "title": query,
        "year": "",
        "language": "",
        "rating": "",
        "genres": []
    }


async def get_tmdb_metadata(query):

    if not TMDB_API_KEY:
        return empty_tmdb_metadata(query)

    try:

        clean_query = re.sub(
            r"\bS\d{1,2}E\d{1,3}\b",
            "",
            query,
            flags=re.IGNORECASE
        )

        clean_query = re.sub(
            r"\b(480p|540p|576p|720p|1080p|2160p|4K|"
            r"WEB[- ]?DL|WEB[- ]?Rip|BluRay|HDRip|HEVC|"
            r"H\.?264|H\.?265)\b",
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

        encoded_query = urllib.parse.quote(
            clean_query
        )

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_API_KEY}"
            f"&query={encoded_query}"
        )

        def fetch():

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "PremiumMovieBot/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=10
            ) as response:

                return response.read().decode(
                    "utf-8"
                )

        raw_data = await asyncio.to_thread(
            fetch
        )

        data = json.loads(
            raw_data
        )

        results = data.get(
            "results",
            []
        )

        if not results:
            return empty_tmdb_metadata(
                clean_query
            )

        item = None

        for result in results:

            if result.get(
                "media_type"
            ) in (
                "movie",
                "tv"
            ):

                item = result
                break

        if not item:
            return empty_tmdb_metadata(
                clean_query
            )

        media_type = item.get(
            "media_type"
        )

        if media_type == "movie":

            title = (
                item.get("title")
                or clean_query
            )

            release_date = (
                item.get("release_date")
                or ""
            )

        else:

            title = (
                item.get("name")
                or clean_query
            )

            release_date = (
                item.get("first_air_date")
                or ""
            )

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
            "ru": "Russian",
            "ar": "Arabic",
            "tr": "Turkish",
            "th": "Thai",
            "id": "Indonesian"
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

        rating = ""

        if rating_value:

            try:

                rating = (
                    f"{float(rating_value):.1f}/10"
                )

            except Exception:

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

        logger.warning(
            "TMDB metadata lookup failed: %s",
            e
        )

        return empty_tmdb_metadata(
            query
        )


# ============================================================
# SEARCH TEXT
# ============================================================

def build_search_text(
    query,
    results,
    elapsed,
    metadata,
    filters_data=None
):

    text = ""

    title = (
        metadata.get("title")
        or query
    )

    year = metadata.get(
        "year"
    )

    language = metadata.get(
        "language"
    )

    rating = metadata.get(
        "rating"
    )

    genres = (
        metadata.get("genres")
        or []
    )

    text += (
        f"🎬 <b>Tɪᴛʟᴇ:</b> "
        f"{escape_html(title)}\n"
    )

    if year:

        text += (
            f"📅 <b>Yᴇᴀʀ:</b> "
            f"{escape_html(str(year))}\n"
        )

    if language:

        text += (
            f"🗣 <b>Lᴀɴɢᴜᴀɢᴇ:</b> "
            f"{escape_html(str(language))}\n"
        )

    if rating:

        text += (
            f"⭐ <b>Rᴀᴛɪɴɢs:</b> "
            f"{escape_html(str(rating))}\n"
        )

    if genres:

        text += (
            f"🎭 <b>Gᴇɴʀᴇs:</b> "
            f"{escape_html(', '.join(genres))}\n"
        )

    active_filter_text = filters_to_text(
        filters_data
    )

    if active_filter_text:

        text += (
            f"🔎 <b>Fɪʟᴛᴇʀs:</b> "
            f"{active_filter_text}\n"
        )

    text += (
        f"📦 <b>Rᴇsᴜʟᴛs Sʜᴏᴡɴ:</b> "
        f"{len(results)}\n"
    )

    text += (
        f"⏱ <b>Rᴇsᴜʟᴛs Sʜᴏᴡɴ Iɴ:</b> "
        f"{elapsed:.2f}s\n"
    )

    text += (
        "©️ <b>Pᴏᴡᴇʀᴇᴅ Bʏ: </b>"
        "<b>@Aero_Unity</b>\n\n"
    )

    text += (
        "👇 <b>Hᴇʀᴇ Yᴏᴜʀ "
        "Rᴇǫᴜᴇsᴛᴇᴅ Fɪʟᴇs</b>"
    )

    return text


# ============================================================
# DELETE SINGLE FILE
# ============================================================

async def delete_file_later(
    client,
    chat_id,
    message_id
):

    try:

        await asyncio.sleep(
            FILE_DELETE_AFTER
        )

        await client.delete_messages(
            chat_id=chat_id,
            message_ids=message_id
        )

        logger.info(
            "Deleted delivered file %s from user %s after 5 minutes.",
            message_id,
            chat_id
        )

    except Exception as e:

        logger.warning(
            "Could not delete delivered file %s: %s",
            message_id,
            e
        )


# ============================================================
# SEND DATABASE FILE
# ============================================================

async def send_database_file(
    client,
    user_id,
    message_id
):

    try:

        database_chat = await client.get_chat(
            DATABASE_CHANNEL_ID
        )

        logger.info(
            "Database channel resolved | id=%s | title=%s | username=%s",
            database_chat.id,
            database_chat.title,
            database_chat.username
        )

        source_message = await client.get_messages(
            database_chat.id,
            int(message_id)
        )

        if not source_message:

            raise ValueError(
                f"Database message {message_id} not found."
            )

        original_caption = (
            source_message.caption
            or ""
        )

        if not original_caption:

            return await client.copy_message(
                chat_id=user_id,
                from_chat_id=database_chat.id,
                message_id=int(message_id),
                reply_markup=file_sent_buttons()
            )

        clickable_caption = (
            '<a href="https://t.me/Aero_Unity">'
            f'<b>{escape_html(original_caption)}</b>'
            '</a>'
        )

        sent_message = await client.copy_message(
            chat_id=user_id,
            from_chat_id=database_chat.id,
            message_id=int(message_id),
            caption=clickable_caption,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=file_sent_buttons()
        )

        return sent_message

    except Exception as e:

        logger.exception(
            "Failed to send database file %s to user %s: %s",
            message_id,
            user_id,
            e
        )

        raise


# ============================================================
# DELETE FILES + WARNING
# ============================================================

async def delete_files_and_warning_later(
    client,
    chat_id,
    message_ids,
    warning_message_id
):

    try:

        await asyncio.sleep(
            FILE_DELETE_AFTER
        )

        if message_ids:

            await client.delete_messages(
                chat_id=chat_id,
                message_ids=message_ids
            )

        if warning_message_id:

            await client.delete_messages(
                chat_id=chat_id,
                message_ids=warning_message_id
            )

        logger.info(
            "Deleted %s delivered files + warning from user %s after 5 minutes.",
            len(message_ids),
            chat_id
        )

    except Exception as e:

        logger.warning(
            "Could not delete files/warning for user %s: %s",
            chat_id,
            e
        )


# ============================================================
# PM FILE DEEP LINK
# ============================================================

async def handle_file_deep_link(
    client,
    message,
    message_id
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if message.chat.type != enums.ChatType.PRIVATE:

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        await message.reply_text(
            "📩 <b>Please open me in PM to receive this file.</b>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Oᴘᴇɴ Bᴏᴛ •",
                            url=(
                                f"https://t.me/{bot_username}"
                                f"?start=file_{message_id}"
                            )
                        )
                    ]
                ]
            )
        )

        return

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

    if not can_use_movie(user):

        await message.reply_text(
            "💎 <b>Premium Required</b>\n\n"
            "Your available movie requests have been used.\n\n"
            "Choose a Premium plan to continue.",
            reply_markup=premium_buttons()
        )

        return

    consumed = await consume_request(
        user_id
    )

    if not consumed:

        await message.reply_text(
            "💎 <b>Premium Required</b>\n\n"
            "Please activate a Premium plan.",
            reply_markup=premium_buttons()
        )

        return

    status_message = await message.reply_text(
        "›› sᴇɴᴅɪɴɢ ғɪʟᴇs..."
    )

    try:

        sent_message = await send_database_file(
            client=client,
            user_id=user_id,
            message_id=message_id
        )

    except Exception as e:

        logger.exception(
            "Deep-link file delivery failed | user=%s | file=%s: %s",
            user_id,
            message_id,
            e
        )

        await restore_request(
            user_id
        )

        try:

            await status_message.edit_text(
                "❌ <b>File delivery failed.</b>\n\n"
                "Your movie request has been restored.\n"
                "Please try again."
            )

        except Exception:

            await message.reply_text(
                "❌ <b>File delivery failed.</b>\n\n"
                "Your movie request has been restored.\n"
                "Please try again."
            )

        return

    try:

        await status_message.delete()

    except Exception:

        pass

    updated_user = await get_user(
        user_id
    )

    remaining = get_remaining_requests(
        updated_user
    )

    logger.info(
        "Deep-link file sent | user=%s | source_message=%s | sent_message=%s | remaining=%s",
        user_id,
        message_id,
        sent_message.id,
        remaining
    )

    warning_message = await client.send_message(
        chat_id=user_id,
        text=(
            "<blockquote>"
            "<b><i>❗️❗️❗️ ɪᴍᴘᴏʀᴛᴀɴᴛ ❗️❗️❗️</i></b>"
            "</blockquote>\n\n"

            "<b>⏳️ ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs...</b>\n"
            "<b>›› ʏᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 5 min,"
            "sᴏ ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ᴏʀ"
            "sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ</b>\n\n"
            "<b>›› ɴᴏᴛᴇ : ᴜsᴇ ᴠʟᴄ ᴘʟᴀʏᴇʀ ᴏʀ ᴍx ᴘʟᴀʏᴇʀ ᴛᴏ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇs"
            "ᴡɪᴛʜ ɢᴏᴏᴅ ᴇxᴘᴇʀɪᴇɴᴄᴇ.</b>"
        )
    )

    asyncio.create_task(
        delete_files_and_warning_later(
            client=client,
            chat_id=user_id,
            message_ids=[
                sent_message.id
            ],
            warning_message_id=warning_message.id
        )
    )


# ============================================================
# PM SEND ALL DEEP LINK
# ============================================================

async def handle_sendall_deep_link(
    client,
    message,
    session_id,
    page
):

    if not message.from_user:
        return

    user_id = message.from_user.id

    if message.chat.type != enums.ChatType.PRIVATE:

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        await message.reply_text(
            "📩 <b>Please open me in PM to receive these files.</b>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Oᴘᴇɴ Bᴏᴛ •",
                            url=(
                                f"https://t.me/{bot_username}"
                                f"?start=sendall_{session_id}_{page}"
                            )
                        )
                    ]
                ]
            )
        )

        return

    session = await get_search_session(
        session_id=session_id,
        user_id=user_id
    )

    if not session:

        await message.reply_text(
            "❌ <b>This search session has expired.</b>\n\n"
            "Please search for the movie again."
        )

        return

    query = (
        session.get("query", "")
        .strip()
    )

    if not query:

        await message.reply_text(
            "❌ <b>Search query not found.</b>\n\n"
            "Please search again."
        )

        return

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

    not_joined = await check_all_fsubs(
        client,
        user_id
    )

    if not_joined:

        await send_fsub_message(
            client,
            message,
            not_joined,
            deep_link=f"sendall_{session_id}_{page}"
        )

        return

    # --------------------------------------------------------
    # GET SAVED FILTERS
    # --------------------------------------------------------

    filters_data = normalize_filters(
        session.get(
            "filters",
            {}
        )
    )

    try:

        results, has_next = await search_movies(
            query=query,
            page=page,
            filters=filters_data
        )

    except Exception as e:

        logger.exception(
            "Deep-link SEND ALL search failed: %s",
            e
        )

        await message.reply_text(
            "❌ <b>Search failed.</b>\n\n"
            "Please try again."
        )

        return

    if not results:

        await message.reply_text(
            "❌ <b>No files found.</b>"
        )

        return

    remaining = get_remaining_requests(
        user
    )

    required = len(results)

    if remaining < required:

        await message.reply_text(
            f"💎 <b>Not enough requests.</b>\n\n"
            f"SEND ALL needs <b>{required}</b> requests.\n"
            f"You currently have <b>{remaining}</b>.",
            reply_markup=premium_buttons()
        )

        return

    status_message = await message.reply_text(
        "›› sᴇɴᴅɪɴɢ ғɪʟᴇs..."
    )

    sent_count = 0
    failed_count = 0

    sent_message_ids = []

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

            sent_message = await send_database_file(
                client=client,
                user_id=user_id,
                message_id=message_id
            )

            sent_message_ids.append(
                sent_message.id
            )

            sent_count += 1

        except Exception as e:

            logger.exception(
                "Deep-link SEND ALL failed for message %s: %s",
                message_id,
                e
            )

            await restore_request(
                user_id
            )

            failed_count += 1

    try:

        await status_message.delete()

    except Exception:

        pass

    if sent_message_ids:

        warning_message = await client.send_message(
            chat_id=user_id,
            text=(
                "<blockquote>"
                "<b><i>❗️❗️❗️ ɪᴍᴘᴏʀᴛᴀɴᴛ ❗️❗️❗️</i></b>"
                "</blockquote>\n\n"

                "<b>⏳️ ᴅᴜᴇ ᴛᴏ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs...</b>\n"
                "<b>›› ʏᴏᴜʀ ғɪʟᴇs ᴡɪʟʟ ʙ ᴅᴇʟᴇᴛᴇᴅ ᴡɪᴛʜɪɴ 5 min,"
                "sᴏ ᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇᴍ ᴛᴏ ᴀɴʏ ᴏᴛʜᴇʀ ᴘʟᴀᴄᴇ ᴏʀ"
                "sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ғᴏʀ ғᴜᴛᴜʀᴇ ᴀᴠᴀɪʟᴀʙɪʟɪᴛʏ</b>\n\n"
                "<b>›› ɴᴏᴛᴇ : ᴜsᴇ ᴠʟᴄ ᴘʟᴀʏᴇʀ ᴏʀ ᴍx ᴘʟᴀʏᴇʀ ᴛᴏ ᴡᴀᴛᴄʜ ᴛʜᴇ ᴇᴘɪsᴏᴅᴇs"
                "ᴡɪᴛʜ ɢᴏᴏᴅ ᴇxᴘᴇʀɪᴇɴᴄᴇ.</b>"
            )
        )

        asyncio.create_task(
            delete_files_and_warning_later(
                client=client,
                chat_id=user_id,
                message_ids=sent_message_ids,
                warning_message_id=warning_message.id
            )
        )

    logger.info(
        "Deep-link SEND ALL finished | user=%s | sent=%s | failed=%s",
        user_id,
        sent_count,
        failed_count
    )


# ============================================================
# SHOW FILTER MENU
# ============================================================

async def show_filter_menu(
    callback,
    session_id,
    page,
    filters_data
):

    filters_data = normalize_filters(
        filters_data
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=filter_menu_buttons(
                session_id=session_id,
                page=page,
                filters=filters_data
            )
        )

    except Exception as e:

        logger.warning(
            "Could not show filter menu: %s",
            e
        )

    await callback.answer()


# ============================================================
# REFRESH SEARCH RESULTS
# ============================================================

async def refresh_filtered_results(
    client,
    callback,
    session_id,
    page,
    filters_data,
    answer_text="Filter applied."
):

    session = await get_search_session(
        session_id=session_id,
        user_id=callback.from_user.id
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
        .strip()
    )

    if not query:

        await callback.answer(
            "Search query not found.",
            show_alert=True
        )

        return

    filters_data = normalize_filters(
        filters_data
    )

    # Always return to page 0 when a filter changes.
    page = 0

    started = time.perf_counter()

    try:

        results, has_next = await search_movies(
            query=query,
            page=page,
            filters=filters_data
        )

    except Exception as e:

        logger.exception(
            "Filtered search failed: %s",
            e
        )

        await callback.answer(
            "Search failed.",
            show_alert=True
        )

        return

    elapsed = (
        time.perf_counter()
        - started
    )

    me = await client.get_me()

    bot_username = (
        me.username
        or ""
    )

    metadata = await get_tmdb_metadata(
        query
    )

    if not results:

        text = (
            f"🎬 <b>Tɪᴛʟᴇ:</b> "
            f"{escape_html(metadata.get('title') or query)}\n\n"
            "❌ <b>Nᴏ Fɪʟᴇs Fᴏᴜɴᴅ Wɪᴛʜ Tʜᴇ Sᴇʟᴇᴄᴛᴇᴅ Fɪʟᴛᴇʀs.</b>\n\n"
            "Try another filter."
        )

        active_filter_text = filters_to_text(
            filters_data
        )

        if active_filter_text:

            text += (
                f"\n🔎 <b>Fɪʟᴛᴇʀs:</b> "
                f"{active_filter_text}"
            )

        text += (
            "\n\n©️ <b>Pᴏᴡᴇʀᴇᴅ Bʏ: "
            "<b>@Aero_Unity</b>"
        )

        try:

            await callback.message.edit_text(
                text,
                reply_markup=filter_menu_buttons(
                    session_id=session_id,
                    page=0,
                    filters=filters_data
                )
            )

        except Exception as e:

            logger.warning(
                "Could not show empty filtered result: %s",
                e
            )

        await callback.answer(
            "No files found.",
            show_alert=True
        )

        return

    try:

        await callback.message.edit_text(
            build_search_text(
                query=query,
                results=results,
                elapsed=elapsed,
                metadata=metadata,
                filters_data=filters_data
            ),
            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=0,
                has_next=has_next,
                bot_username=bot_username
            )
        )

    except Exception as e:

        if "MESSAGE_NOT_MODIFIED" not in str(e):

            logger.exception(
                "Could not refresh filtered results: %s",
                e
            )

    await callback.answer(
        answer_text
    )


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # MOVIE SEARCH
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
                "token",
                "gentoken",
                "font",
                "trendlist",
                "alive",
                "user",
                "channel",
                "premiumuser",
                "activate",
                "deactivate",
                "id",
                "addpremium",
                "removepremium",
                "stats",
                "generatecode",
                "codes",
                "redeem",
                "ban",
                "unban",
                "banlist",
                "maintenance",
                "index",
                "indexstatus",
                "resetindex",
                "broadcast",
                "addfsub",
                "delfsub",
                "fsublist"
            ]
        )
    )
    async def movie_search_handler(
        client,
        message
    ):

        if not message.from_user:
            return

        user_id = message.from_user.id

        query = (
            message.text
            or ""
        ).strip()

        if not query:
            return

        if not query.startswith("/"):

            try:

                await record_search(
                    query
                )

            except Exception as e:

                logger.warning(
                    "Could not record search '%s': %s",
                    query,
                    e
                )

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

        if not can_use_movie(user):

            await message.reply_text(
                "🚫 <b>Your movie request limit has been reached.</b>\n\n"
                "💎 Please activate a Premium plan to continue receiving files.",
                reply_markup=premium_buttons()
            )

            return

        wait = await message.reply_text(
            f"🔎<b><i>Sᴇᴀʀᴄʜɪɴɢ "
            f"{escape_html(query)}...</i></b>"
        )

        search_started = time.perf_counter()

        try:

            results, has_next = await search_movies(
                query=query,
                page=0,
                filters={}
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

        elapsed = (
            time.perf_counter()
            - search_started
        )

        if not results:

            google_url = (
                "https://www.google.com/search?q="
                + urllib.parse.quote(query)
            )

            admin_url = (
                "https://t.me/Mr_Mohammed_29"
            )

            not_found_text = (

                f"<b>Your Sᴇᴀʀᴄʜ:</b> "
                f"<code>{escape_html(query)}</code>\n\n"

                "<b>Tʜɪs Mᴏᴠɪᴇ Nᴏᴛ Fᴏᴜɴᴅ "
                "Iɴ Mʏ Dᴀᴛᴀʙᴀsᴇ</b>\n\n"

                "<b>Pʟᴇᴀsᴇ Cʜᴇᴄᴋ Yᴏᴜʀ "
                "Sᴘᴇʟʟɪɴɢ Oɴ Gᴏᴏɢʟᴇ & Tʀʏ Aɢᴀɪɴ</b>\n\n"

                "<b>○ 𝖭𝗈𝗍𝖾 1 :</b> "
                "𝖣𝗈𝗇'𝗍 𝖲𝖾𝗇𝖽 𝖠𝗇𝗒 𝖪𝗂𝗇𝖽 𝖮𝖿 𝖯𝗁𝗈𝗍𝗈𝗌, "
                "𝖵𝗂𝖽𝖾𝗈𝗌, 𝖣𝗈𝖼𝗎𝗆𝖾𝗇𝗍𝗌, "
                "𝖴𝗋𝗅𝗌 𝖤𝗍𝖼.\n"

                "<b>○ 𝖭𝗈𝗍𝖾 2 :</b> "
                "𝖣𝗈𝗇'𝗍 𝖴𝗌𝖾 ➠ ':(!,./)'"
            )

            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "• Rᴇǫᴜᴇsᴛ Tᴏ Oᴡɴᴇʀ •",
                            url=admin_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "• Cʜᴇᴄᴋ Sᴘᴇʟʟɪɴɢ Oɴ Gᴏᴏɢʟᴇ •",
                            url=google_url
                        )
                    ]
                ]
            )

            await wait.edit_text(
                not_found_text,
                reply_markup=buttons
            )

            return

        try:

            session_id = await create_search_session(
                user_id=user_id,
                query=query,
                filters={}
            )

        except TypeError:

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

        metadata = await get_tmdb_metadata(
            query
        )

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        await wait.edit_text(
            build_search_text(
                query=query,
                results=results,
                elapsed=elapsed,
                metadata=metadata,
                filters_data={}
            ),
            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=0,
                has_next=has_next,
                bot_username=bot_username
            )
        )


    # ========================================================
    # FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filters_[a-fA-F0-9]+_\d+$"
        )
    )
    async def filter_menu_callback(
        client,
        callback
    ):

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
                "Invalid filter request.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        filters_data = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        await show_filter_menu(
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=filters_data
        )


    # ========================================================
    # LANGUAGE FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_lang_[a-fA-F0-9]+_\d+$"
        )
    )
    async def language_filter_menu_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(
                parts[3]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid language filter.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
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
            .strip()
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        try:

            options = await get_filter_options(
                query=query,
                filters=current_filters
            )

        except Exception as e:

            logger.exception(
                "Could not get language options: %s",
                e
            )

            await callback.answer(
                "Could not load languages.",
                show_alert=True
            )

            return

        languages = options.get(
            "languages",
            []
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=language_filter_buttons(
                    session_id=session_id,
                    page=page,
                    languages=languages,
                    current_language=current_filters.get(
                        "language"
                    )
                )
            )

        except Exception as e:

            logger.warning(
                "Could not display language menu: %s",
                e
            )

        await callback.answer()


    # ========================================================
    # YEAR FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_year_[a-fA-F0-9]+_\d+$"
        )
    )
    async def year_filter_menu_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(
                parts[3]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid year filter.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
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
            .strip()
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        try:

            options = await get_filter_options(
                query=query,
                filters=current_filters
            )

        except Exception as e:

            logger.exception(
                "Could not get year options: %s",
                e
            )

            await callback.answer(
                "Could not load years.",
                show_alert=True
            )

            return

        years = options.get(
            "years",
            []
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=year_filter_buttons(
                    session_id=session_id,
                    page=page,
                    years=years,
                    current_year=current_filters.get(
                        "year"
                    )
                )
            )

        except Exception as e:

            logger.warning(
                "Could not display year menu: %s",
                e
            )

        await callback.answer()


    # ========================================================
    # SEASON FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_season_[a-fA-F0-9]+_\d+$"
        )
    )
    async def season_filter_menu_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(
                parts[3]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid season filter.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
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
            .strip()
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        try:

            options = await get_filter_options(
                query=query,
                filters=current_filters
            )

        except Exception as e:

            logger.exception(
                "Could not get season options: %s",
                e
            )

            await callback.answer(
                "Could not load seasons.",
                show_alert=True
            )

            return

        seasons = options.get(
            "seasons",
            []
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=season_filter_buttons(
                    session_id=session_id,
                    page=page,
                    seasons=seasons,
                    current_season=current_filters.get(
                        "season"
                    )
                )
            )

        except Exception as e:

            logger.warning(
                "Could not display season menu: %s",
                e
            )

        await callback.answer()


    # ========================================================
    # EPISODE FILTER MENU
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_episode_[a-fA-F0-9]+_\d+$"
        )
    )
    async def episode_filter_menu_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(
                parts[3]
            )

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid episode filter.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
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
            .strip()
        )

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        try:

            options = await get_filter_options(
                query=query,
                filters=current_filters
            )

        except Exception as e:

            logger.exception(
                "Could not get episode options: %s",
                e
            )

            await callback.answer(
                "Could not load episodes.",
                show_alert=True
            )

            return

        episodes = options.get(
            "episodes",
            []
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=episode_filter_buttons(
                    session_id=session_id,
                    page=page,
                    episodes=episodes,
                    current_episode=current_filters.get(
                        "episode"
                    )
                )
            )

        except Exception as e:

            logger.warning(
                "Could not display episode menu: %s",
                e
            )

        await callback.answer()


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
        callback
    ):

        parts = callback.data.split(
            "_",
            3
        )

        if len(parts) != 4:

            await callback.answer(
                "Invalid language.",
                show_alert=True
            )

            return

        session_id = parts[1]

        try:

            page = int(parts[2])

        except ValueError:

            await callback.answer(
                "Invalid page.",
                show_alert=True
            )

            return

        language = (
            parts[3]
            .strip()
        )

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        if language:

            current_filters["language"] = language

        else:

            current_filters.pop(
                "language",
                None
            )

        await update_search_session_filters(
            session_id=session_id,
            user_id=callback.from_user.id,
            filters=current_filters
        )

        await refresh_filtered_results(
            client=client,
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=current_filters,
            answer_text=f"Language: {language}"
        )


    # ========================================================
    # SET YEAR
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setyear_[a-fA-F0-9]+_\d+_\d+$"
        )
    )
    async def set_year_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[1]

            page = int(parts[2])

            year = int(parts[3])

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid year.",
                show_alert=True
            )

            return

        if not 1960 <= year <= 2026:

            await callback.answer(
                "Year must be between 1960 and 2026.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        current_filters["year"] = year

        await update_search_session_filters(
            session_id=session_id,
            user_id=callback.from_user.id,
            filters=current_filters
        )

        await refresh_filtered_results(
            client=client,
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=current_filters,
            answer_text=f"Year: {year}"
        )


    # ========================================================
    # SET SEASON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setseason_[a-fA-F0-9]+_\d+_\d+$"
        )
    )
    async def set_season_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[1]

            page = int(parts[2])

            season = int(parts[3])

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid season.",
                show_alert=True
            )

            return

        if not 1 <= season <= 20:

            await callback.answer(
                "Season must be between 1 and 20.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        current_filters["season"] = season

        # If season changes, old episode may no longer exist.
        current_filters.pop(
            "episode",
            None
        )

        await update_search_session_filters(
            session_id=session_id,
            user_id=callback.from_user.id,
            filters=current_filters
        )

        await refresh_filtered_results(
            client=client,
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=current_filters,
            answer_text=f"Season: {season}"
        )


    # ========================================================
    # SET EPISODE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^setepisode_[a-fA-F0-9]+_\d+_\d+$"
        )
    )
    async def set_episode_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[1]

            page = int(parts[2])

            episode = int(parts[3])

        except (
            ValueError,
            IndexError
        ):

            await callback.answer(
                "Invalid episode.",
                show_alert=True
            )

            return

        if not 1 <= episode <= 50:

            await callback.answer(
                "Episode must be between 1 and 50.",
                show_alert=True
            )

            return

        session = await get_search_session(
            session_id=session_id,
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        current_filters = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        if not current_filters.get("season"):

            await callback.answer(
                "Select a season first.",
                show_alert=True
            )

            return

        current_filters["episode"] = episode

        await update_search_session_filters(
            session_id=session_id,
            user_id=callback.from_user.id,
            filters=current_filters
        )

        await refresh_filtered_results(
            client=client,
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=current_filters,
            answer_text=f"Episode: {episode}"
        )


    # ========================================================
    # CLEAR FILTERS
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_clear_[a-fA-F0-9]+_\d+$"
        )
    )
    async def clear_filters_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(parts[3])

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
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        await update_search_session_filters(
            session_id=session_id,
            user_id=callback.from_user.id,
            filters={}
        )

        await refresh_filtered_results(
            client=client,
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data={},
            answer_text="Filters cleared."
        )


    # ========================================================
    # FILTER BACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^filter_back_[a-fA-F0-9]+_\d+$"
        )
    )
    async def filter_back_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split("_")

            session_id = parts[2]

            page = int(parts[3])

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
            user_id=callback.from_user.id
        )

        if not session:

            await callback.answer(
                "This search session has expired.",
                show_alert=True
            )

            return

        filters_data = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        await show_filter_menu(
            callback=callback,
            session_id=session_id,
            page=page,
            filters_data=filters_data
        )


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
            .strip()
        )

        if not query:

            await callback.answer(
                "Search query not found.",
                show_alert=True
            )

            return

        filters_data = normalize_filters(
            session.get(
                "filters",
                {}
            )
        )

        page_started = time.perf_counter()

        try:

            results, has_next = await search_movies(
                query=query,
                page=page,
                filters=filters_data
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

        elapsed = (
            time.perf_counter()
            - page_started
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

        me = await client.get_me()

        bot_username = (
            me.username
            or ""
        )

        try:

            await callback.message.edit_text(
                build_search_text(
                    query=query,
                    results=results,
                    elapsed=elapsed,
                    metadata=metadata,
                    filters_data=filters_data
                ),
                reply_markup=search_result_buttons(
                    results=results,
                    session_id=session_id,
                    page=page,
                    has_next=has_next,
                    bot_username=bot_username
                )
            )

        except Exception as e:

            if "MESSAGE_NOT_MODIFIED" not in str(e):

                logger.exception(
                    "Could not update search page: %s",
                    e
                )

        await callback.answer()


    # ========================================================
    # LEGACY SEND ALL CALLBACK
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

        if callback.message.chat.type in (
            enums.ChatType.GROUP,
            enums.ChatType.SUPERGROUP
        ):

            me = await client.get_me()

            bot_username = (
                me.username
                or ""
            )

            await callback.answer(
                "Opening PM...",
                show_alert=False
            )

            try:

                await callback.message.reply_text(
                    "📩 <b>Send All is available in PM.</b>",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "• Oᴘᴇɴ Bᴏᴛ •",
                                    url=(
                                        f"https://t.me/{bot_username}"
                                        f"?start=sendall_{session_id}_{page}"
                                    )
                                )
                            ]
                        ]
                    )
                )

            except Exception as e:

                logger.warning(
                    "Could not send PM redirect: %s",
                    e
                )

            return

        await handle_sendall_deep_link(
            client=client,
            message=callback.message,
            session_id=session_id,
            page=page
        )

        await callback.answer()


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
        callback
    ):

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

        if callback.message.chat.type in (
            enums.ChatType.GROUP,
            enums.ChatType.SUPERGROUP
        ):

            me = await client.get_me()

            bot_username = (
                me.username
                or ""
            )

            await callback.answer(
                "Opening PM...",
                show_alert=False
            )

            try:

                await callback.message.reply_text(
                    "📩 <b>Open the bot in PM to receive this file.</b>",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "• Oᴘᴇɴ Bᴏᴛ •",
                                    url=(
                                        f"https://t.me/{bot_username}"
                                        f"?start=file_{message_id}"
                                    )
                                )
                            ]
                        ]
                    )
                )

            except Exception as e:

                logger.warning(
                    "Could not send PM redirect: %s",
                    e
                )

            return

        await handle_file_deep_link(
            client=client,
            message=callback.message,
            message_id=message_id
        )

        await callback.answer()
