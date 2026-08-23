from pyrogram import filters

from database import (
    get_user,
    create_user,
    consume_request
)

from search import (
    search_movies
)

from premium import (
    can_use_movie,
    get_user_plan_text
)

from utils.buttons import (
    search_result_buttons,
    premium_buttons
)

from config import (
    FREE_REQUESTS,
    DATABASE_CHANNEL_ID,
    RESULTS_PER_PAGE
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
                "id"
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
        # GET / CREATE USER
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

        if not can_use_movie(
            user
        ):

            await message.reply_text(
                "🚫 <b>Your movie request limit "
                "has been reached.</b>\n\n"
                "🆓 Free plan: "
                f"<b>{FREE_REQUESTS}</b> requests\n\n"
                "💎 Choose a Premium plan to "
                "continue searching.",
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

            results = await search_movies(
                query,
                page=0
            )

        except Exception as e:

            print(
                f"Search error: {e}"
            )

            await wait.edit_text(
                "❌ Search failed.\n"
                "Please try again later."
            )

            return


        # ----------------------------------------------------
        # NO RESULTS
        # ----------------------------------------------------

        if not results:

            await wait.edit_text(
                "😕 <b>No results found.</b>\n\n"
                f"Search: <code>{query}</code>"
            )

            return


        # ----------------------------------------------------
        # SHOW RESULTS
        # ----------------------------------------------------

        await wait.edit_text(
            f"🎬 <b>Results for:</b>\n"
            f"<code>{query}</code>\n\n"
            f"Found: <b>{len(results)}</b>\n\n"
            "Select a file below:",
            reply_markup=search_result_buttons(
                results,
                page=0
            )
        )


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
        # CHECK BALANCE AGAIN
        #
        # Important because the user may have opened
        # an old result after their balance changed.
        # ----------------------------------------------------

        if not can_use_movie(
            user
        ):

            await callback.answer(
                "Your movie request limit is finished.",
                show_alert=True
            )

            await callback.message.reply_text(
                "💎 <b>Premium required</b>\n\n"
                "Your available movie requests "
                "have been used.",
                reply_markup=premium_buttons()
            )

            return


        # ----------------------------------------------------
        # CONSUME ONE REQUEST
        #
        # The database function should perform this
        # atomically so two clicks cannot consume the
        # same request incorrectly.
        # ----------------------------------------------------

        consumed = await consume_request(
            user_id
        )

        if not consumed:

            await callback.answer(
                "No requests remaining.",
                show_alert=True
            )

            return


        await callback.answer(
            "🎬 Preparing your file..."
        )


        # ----------------------------------------------------
        # COPY FILE FROM DATABASE CHANNEL
        # ----------------------------------------------------

        try:

            sent = await client.copy_message(
                chat_id=user_id,
                from_chat_id=DATABASE_CHANNEL_ID,
                message_id=message_id
            )

        except Exception as e:

            print(
                f"File delivery error: {e}"
            )

            # ------------------------------------------------
            # IMPORTANT:
            # If delivery fails, restore the request.
            # ------------------------------------------------

            try:

                from database import (
                    restore_request
                )

                await restore_request(
                    user_id
                )

            except Exception as restore_error:

                print(
                    f"Request restore error: "
                    f"{restore_error}"
                )

            await callback.message.reply_text(
                "❌ <b>File delivery failed.</b>\n\n"
                "Your request was not charged."
            )

            return


        # ----------------------------------------------------
        # GET UPDATED BALANCE
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


        # ----------------------------------------------------
        # SEND BALANCE INFO
        # ----------------------------------------------------

        await client.send_message(
            user_id,

            "✅ <b>File sent successfully!</b>\n\n"
            f"🎟 Requests remaining: "
            f"<b>{remaining}</b>"
        )
