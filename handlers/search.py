import logging

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
    home_buttons
)

from utils.helpers import (
    escape_html
)


logger = logging.getLogger(__name__)


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
                "id",
                "addpremium",
                "removepremium",
                "stats",
                "index",
                "indexstatus",
                "stopindex"
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

                f"🔎 Search:\n"
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
        # SHOW RESULTS
        # ----------------------------------------------------

        await wait.edit_text(
            "🔎 <b>Search Results</b>\n\n"

            f"Query: "
            f"<code>{escape_html(query)}</code>\n\n"

            f"🎬 Showing "
            f"<b>{len(results)}</b> results.\n\n"

            "👇 Select the file you want:",
            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=0,
                has_next=has_next
            )
        )


    # ========================================================
    # SEARCH PAGINATION
    #
    # callback:
    #
    # searchpage_SESSION_ID_PAGE
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

        user_id = (
            callback.from_user.id
        )

        try:

            parts = callback.data.split(
                "_"
            )

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

        # ----------------------------------------------------
        # GET SEARCH SESSION
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
        # SEARCH REQUESTED PAGE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # NO RESULTS ON PAGE
        # ----------------------------------------------------

        if not results:

            await callback.answer(
                "No more results.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # UPDATE RESULTS
        # ----------------------------------------------------

        await callback.message.edit_text(
            "🔎 <b>Search Results</b>\n\n"

            f"Query: "
            f"<code>{escape_html(query)}</code>\n\n"

            f"📄 Page: <b>{page + 1}</b>\n"
            f"🎬 Results: <b>{len(results)}</b>\n\n"

            "👇 Select the file you want:",
            reply_markup=search_result_buttons(
                results=results,
                session_id=session_id,
                page=page,
                has_next=has_next
            )
        )

        await callback.answer()


    # ========================================================
    # FILE SELECTION
    #
    # callback:
    #
    # file_MESSAGE_ID
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

        user_id = (
            callback.from_user.id
        )

        # ----------------------------------------------------
        # GET MESSAGE ID
        # ----------------------------------------------------

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
        # ATOMICALLY CONSUME ONE REQUEST
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

        # ----------------------------------------------------
        # ANSWER CALLBACK
        # ----------------------------------------------------

        await callback.answer(
            "📤 Sending your file..."
        )

        # ----------------------------------------------------
        # SEND FILE FROM DATABASE CHANNEL
        # ----------------------------------------------------

        try:

            await client.copy_message(
                chat_id=user_id,

                from_chat_id=DATABASE_CHANNEL_ID,

                message_id=message_id
            )

        except Exception as e:

            logger.exception(
                "File delivery failed: %s",
                e
            )

            # ----------------------------------------------
            # RESTORE REQUEST
            # ----------------------------------------------

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
        # GET UPDATED USER BALANCE
        # ----------------------------------------------------

        updated_user = await get_user(
            user_id
        )

        remaining = get_remaining_requests(
            updated_user
        )

        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        await client.send_message(
            user_id,

            "✅ <b>File sent successfully!</b>\n\n"

            f"🎟 Remaining requests: "
            f"<b>{remaining}</b>"
        )


# ============================================================
# END
# ============================================================
