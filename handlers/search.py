from pyrogram import filters

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
    RESULTS_PER_PAGE
)


# Store the user's latest search.

USER_SEARCHES = {}


def register_search_handlers(app):

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

        # Make sure user exists.
        await create_user(
            user.id,
            user.first_name,
            user.username
        )

        user_data = await get_user(
            user.id
        )

        # Check remaining requests.
        if not can_use_movie(
            user_data
        ):

            await message.reply_text(
                "⚠️ <b>Your movie request limit "
                "has been reached.</b>\n\n"
                "🆓 Your 5 free requests are finished.\n\n"
                "💎 Choose a Premium plan to "
                "continue searching.",
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
                "❌ <b>No results found.</b>\n\n"
                f"🔎 Search: <code>{query}</code>\n\n"
                "Try another movie or series name."
            )

            return

        # Save search for pagination.
        USER_SEARCHES[
            user.id
        ] = query

        # A request is counted when results
        # are successfully returned.
        success = await use_request(
            user.id
        )

        if not success:

            await wait.edit_text(
                "⚠️ Your request limit has "
                "been reached.",
                reply_markup=premium_buttons()
            )

            return

        remaining_user = await get_user(
            user.id
        )

        remaining = remaining_user.get(
            "remaining_requests",
            0
        )

        text = (
            "🎬 <b>Search Results</b>\n\n"
            f"🔎 Query: <code>{query}</code>\n"
            f"📁 Results: <b>{total}</b>\n"
            f"🎟 Requests remaining: "
            f"<b>{remaining}</b>\n\n"
            "👇 Select a file:"
        )

        await wait.edit_text(
            text,
            reply_markup=search_result_buttons(
                results,
                page=0
            )
        )


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
                "Search expired. Search again.",
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
