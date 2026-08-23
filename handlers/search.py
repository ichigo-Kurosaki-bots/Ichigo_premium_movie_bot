from pyrogram import filters

from database import (
    get_user,
    create_user,
    consume_request,
    restore_request
)

from search import (
    search_movies
)

from premium import (
    can_use_movie
)

from utils.buttons import (
    search_result_buttons,
    premium_buttons
)

from config import (
    FREE_REQUESTS,
    DATABASE_CHANNEL_ID
)


# ============================================================
# REGISTER SEARCH HANDLERS
# ============================================================

def register_search_handlers(app):

    # ========================================================
    # TEXT SEARCH
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

        user_id = (
            message.from_user.id
        )

        query = (
            message.text.strip()
        )

        if not query:
            return

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        user = await get_user(
            user_id
        )

        if not user:

            await create_user(
                user_id,
                message.from_user.first_name,
                message.from_user.username
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # CHECK REQUEST BALANCE
        # ----------------------------------------------------

        if not can_use_movie(user):

            await message.reply_text(
                "🚫 <b>Movie request limit reached.</b>\n\n"
                f"🆓 Free requests: "
                f"<b>{FREE_REQUESTS}</b>\n\n"
                "💎 Choose a Premium plan "
                "to continue.",
                reply_markup=premium_buttons()
            )

            return

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        wait = await message.reply_text(
            "🔎 <b>Searching...</b>"
        )

        try:

            results, has_next = (
                await search_movies(
                    query,
                    page=0
                )
            )

        except Exception as e:

            print(
                f"Search error: {e}"
            )

            await wait.edit_text(
                "❌ Search failed.\n"
                "Please try again."
            )

            return

        # ----------------------------------------------------
        # NO RESULTS
        # ----------------------------------------------------

        if not results:

            await wait.edit_text(
                "😕 <b>No results found.</b>\n\n"
                f"🔎 Search: "
                f"<code>{query}</code>"
            )

            return

        # ----------------------------------------------------
        # SHOW RESULTS
        # ----------------------------------------------------

        await wait.edit_text(
            f"🔎 <b>Search:</b> "
            f"<code>{query}</code>\n\n"
            f"🎬 Results: "
            f"<b>{len(results)}</b>\n\n"
            "Select the file you want:",
            reply_markup=search_result_buttons(
                results,
                query,
                page=0,
                has_next=has_next
            )
        )


    # ========================================================
    # SEARCH PAGINATION
    #
    # callback:
    #
    # searchpage_PAGE_QUERY
    #
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^searchpage_\d+_.+$"
        )
    )
    async def search_page_callback(
        client,
        callback
    ):

        try:

            parts = callback.data.split(
                "_",
                2
            )

            page = int(
                parts[1]
            )

            query = parts[2].strip()

        except (ValueError, IndexError):

            await callback.answer(
                "Invalid page.",
                show_alert=True
            )

            return

        if not query:

            await callback.answer(
                "Invalid search.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # SEARCH PAGE
        # ----------------------------------------------------

        try:

            results, has_next = (
                await search_movies(
                    query,
                    page=page
                )
            )

        except Exception as e:

            print(
                f"Pagination error: {e}"
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

        # ----------------------------------------------------
        # UPDATE MESSAGE
        # ----------------------------------------------------

        await callback.message.edit_text(
            f"🔎 <b>Search:</b> "
            f"<code>{query}</code>\n\n"
            f"📄 Page: <b>{page + 1}</b>\n"
            f"🎬 Results: "
            f"<b>{len(results)}</b>\n\n"
            "Select a file:",
            reply_markup=search_result_buttons(
                results,
                query,
                page=page,
                has_next=has_next
            )
        )

        await callback.answer()


    # ========================================================
    # FILE BUTTON
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

        try:

            message_id = int(
                callback.data.split("_")[1]
            )

        except (ValueError, IndexError):

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

            await create_user(
                user_id,
                callback.from_user.first_name,
                callback.from_user.username
            )

            user = await get_user(
                user_id
            )

        # ----------------------------------------------------
        # ATOMICALLY CONSUME REQUEST
        # ----------------------------------------------------

        consumed = await consume_request(
            user_id
        )

        if not consumed:

            await callback.answer(
                "Your request limit is finished.",
                show_alert=True
            )

            await callback.message.reply_text(
                "💎 <b>Premium required</b>\n\n"
                "Your available requests are finished.",
                reply_markup=premium_buttons()
            )

            return

        await callback.answer(
            "🎬 Sending file..."
        )

        # ----------------------------------------------------
        # COPY AUTHORIZED MEDIA
        # ----------------------------------------------------

        try:

            await client.copy_message(
                chat_id=user_id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=message_id
            )

        except Exception as e:

            print(
                f"Delivery error: {e}"
            )

            # Restore the consumed request.
            await restore_request(
                user_id
            )

            await callback.message.reply_text(
                "❌ <b>File delivery failed.</b>\n\n"
                "Your request has been restored."
            )

            return

        # ----------------------------------------------------
        # UPDATED BALANCE
        # ----------------------------------------------------

        updated_user = await get_user(
            user_id
        )

        remaining = (
            updated_user.get(
                "remaining_requests",
                0
            )
            if updated_user
            else 0
        )

        await client.send_message(
            user_id,
            "✅ <b>File sent successfully!</b>\n\n"
            f"🎟 Remaining requests: "
            f"<b>{remaining}</b>"
            )
