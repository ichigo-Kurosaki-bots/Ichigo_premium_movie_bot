from pyrogram import filters
from pyrogram.errors import FloodWait

from database import (
    create_user,
    get_user,
    use_request
)

from search import (
    search_movies,
    count_search_results
)

from premium import (
    can_use_movie
)

from utils.buttons import (
    search_result_buttons,
    premium_buttons
)

from config import (
    DATABASE_CHANNEL_ID,
    RESULTS_PER_PAGE
)


# ============================================================
# USER SEARCH CACHE
# ============================================================

USER_SEARCHES = {}


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
                "plans",
                "premium",
                "myplan",
                "id",
                "stats",
                "about",
                "addpremium",
                "removepremium",
                "premiuminfo",
                "users"
            ]
        )
    )
    async def search_handler(
        client,
        message
    ):

        user = message.from_user

        if not user:
            return

        # Create user if necessary.
        await create_user(
            user.id,
            user.first_name,
            user.username
        )

        user_data = await get_user(
            user.id
        )

        # ----------------------------------------------------
        # CHECK REQUEST LIMIT
        # ----------------------------------------------------

        if not can_use_movie(
            user_data
        ):

            await message.reply_text(
                "⚠️ <b>Movie Request Limit Reached</b>\n\n"
                "You have used all your available "
                "movie requests.\n\n"
                "💎 Choose a Premium plan to continue.",
                reply_markup=premium_buttons()
            )

            return

        query = message.text.strip()

        if len(query) < 2:

            await message.reply_text(
                "❌ Please enter at least "
                "2 characters."
            )

            return

        wait = await message.reply_text(
            "🔎 <b>Searching...</b>"
        )

        # ----------------------------------------------------
        # SEARCH DATABASE
        # ----------------------------------------------------

        results = await search_movies(
            query,
            limit=RESULTS_PER_PAGE,
            skip=0
        )

        total = await count_search_results(
            query
        )

        if not results:

            await wait.edit_text(
                "❌ <b>No Results Found</b>\n\n"
                f"🔎 Search: <code>{query}</code>\n\n"
                "Try another movie or series name."
            )

            return

        # Save search.
        USER_SEARCHES[
            user.id
        ] = query

        remaining = user_data.get(
            "remaining_requests",
            0
        )

        text = (
            "🎬 <b>Search Results</b>\n\n"
            f"🔎 Query: <code>{query}</code>\n"
            f"📁 Results found: <b>{total}</b>\n"
            f"🎟 Requests remaining: "
            f"<b>{remaining}</b>\n\n"
            "👇 Select the movie/file you want:"
        )

        await wait.edit_text(
            text,
            reply_markup=search_result_buttons(
                results,
                page=0
            )
        )


    # ========================================================
    # PAGINATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^page_\d+$"
        )
    )
    async def page_handler(
        client,
        callback
    ):

        user_id = callback.from_user.id

        query = USER_SEARCHES.get(
            user_id
        )

        if not query:

            await callback.answer(
                "Search expired. Please search again.",
                show_alert=True
            )

            return

        page = int(
            callback.data.split("_")[1]
        )

        skip = (
            page * RESULTS_PER_PAGE
        )

        results = await search_movies(
            query,
            limit=RESULTS_PER_PAGE,
            skip=skip
        )

        if not results:

            await callback.answer(
                "No more results.",
                show_alert=True
            )

            return

        text = (
            "🎬 <b>Search Results</b>\n\n"
            f"🔎 Query: <code>{query}</code>\n\n"
            "👇 Select a file:"
        )

        await callback.message.edit_text(
            text,
            reply_markup=search_result_buttons(
                results,
                page=page
            )
        )

        await callback.answer()


    # ========================================================
    # SEND SELECTED FILE
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^file_\d+$"
        )
    )
    async def file_handler(
        client,
        callback
    ):

        user_id = callback.from_user.id

        try:

            message_id = int(
                callback.data.split("_")[1]
            )

        except ValueError:

            await callback.answer(
                "Invalid file.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # CHECK USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id,
                callback.from_user.first_name,
                callback.from_user.username
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # CHECK REQUEST LIMIT AGAIN
        # ----------------------------------------------------

        if not can_use_movie(
            user
        ):

            await callback.answer(
                "Your movie request limit is finished.",
                show_alert=True
            )

            try:

                await callback.message.edit_text(
                    "⚠️ <b>Request Limit Reached</b>\n\n"
                    "💎 Please choose a Premium plan "
                    "to continue.",
                    reply_markup=premium_buttons()
                )

            except Exception:
                pass

            return

        await callback.answer(
            "📤 Sending file..."
        )

        status = await callback.message.reply_text(
            "📤 <b>Preparing your file...</b>"
        )

        # ----------------------------------------------------
        # COPY FILE FROM DATABASE CHANNEL
        # ----------------------------------------------------

        try:

            sent_message = await client.copy_message(
                chat_id=user_id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=message_id
            )

        except FloodWait as e:

            await status.edit_text(
                f"⏳ Telegram requested a wait.\n"
                f"Please try again in {e.value} seconds."
            )

            return

        except Exception as e:

            print(
                f"File delivery error: {e}"
            )

            await status.edit_text(
                "❌ <b>File Delivery Failed</b>\n\n"
                "The requested file could not be sent.\n"
                "Please try again later."
            )

            return

        # ----------------------------------------------------
        # COUNT REQUEST ONLY AFTER SUCCESS
        # ----------------------------------------------------

        used = await use_request(
            user_id
        )

        if not used:

            # The file was already sent, so don't
            # send another file. Inform the user.
            await status.edit_text(
                "⚠️ File sent, but your request "
                "counter could not be updated.\n\n"
                "Please contact the owner."
            )

            return

        # Get updated account.
        updated_user = await get_user(
            user_id
        )

        remaining = updated_user.get(
            "remaining_requests",
            0
        )

        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        await status.edit_text(
            "✅ <b>File Sent Successfully!</b>\n\n"
            f"🎬 Requests remaining: "
            f"<b>{remaining}</b>\n\n"
            "🍿 Enjoy!"
        )

        print(
            f"Delivered message {message_id} "
            f"to user {user_id}. "
            f"Remaining: {remaining}"
        )
