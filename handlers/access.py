# handlers/access.py

import logging

from pyrogram import filters, StopPropagation

from config import OWNER_ID, ADMIN_IDS
from database import (
    is_user_banned,
    is_maintenance_enabled
)

logger = logging.getLogger(__name__)


# ============================================================
# ADMIN CHECK
# ============================================================

def is_admin(user_id):
    return user_id == OWNER_ID or user_id in ADMIN_IDS


# ============================================================
# REGISTER ACCESS HANDLERS
# ============================================================

def register_access_handlers(app):

    # ========================================================
    # MESSAGE ACCESS CONTROL
    # ========================================================

    @app.on_message(filters.all, group=-100)
    async def access_control(client, message):

        # Ignore messages without a user
        if not message.from_user:
            return

        user_id = message.from_user.id

        # ----------------------------------------------------
        # OWNER + ADMIN BYPASS
        # ----------------------------------------------------

        if is_admin(user_id):
            return

        # ----------------------------------------------------
        # BAN CHECK
        # ----------------------------------------------------

        try:

            if await is_user_banned(user_id):

                try:
                    await message.reply_text(
                        "🚫 <b>Access Denied</b>\n\n"
                        "You are banned from using this bot."
                    )
                except Exception:
                    pass

                raise StopPropagation

        except StopPropagation:
            raise

        except Exception as e:
            logger.error(
                f"Ban check failed for {user_id}: {e}"
            )

        # ----------------------------------------------------
        # MAINTENANCE CHECK
        # ----------------------------------------------------

        try:

            if await get_maintenance_mode():

                try:
                    await message.reply_text(
                        "🔧 <b>Bot Under Maintenance</b>\n\n"
                        "The bot is currently under maintenance.\n"
                        "Please try again later."
                    )
                except Exception:
                    pass

                raise StopPropagation

        except StopPropagation:
            raise

        except Exception as e:
            logger.error(
                f"Maintenance check failed for {user_id}: {e}"
            )


    # ========================================================
    # CALLBACK QUERY ACCESS CONTROL
    # ========================================================

    @app.on_callback_query(group=-100)
    async def callback_access_control(client, callback_query):

        if not callback_query.from_user:
            return

        user_id = callback_query.from_user.id

        # ----------------------------------------------------
        # OWNER + ADMIN BYPASS
        # ----------------------------------------------------

        if is_admin(user_id):
            return

        # ----------------------------------------------------
        # BAN CHECK
        # ----------------------------------------------------

        try:

            if await is_user_banned(user_id):

                try:
                    await callback_query.answer(
                        "🚫 You are banned from using this bot.",
                        show_alert=True
                    )
                except Exception:
                    pass

                raise StopPropagation

        except StopPropagation:
            raise

        except Exception as e:
            logger.error(
                f"Callback ban check failed for {user_id}: {e}"
            )

        # ----------------------------------------------------
        # MAINTENANCE CHECK
        # ----------------------------------------------------

        try:

            if await get_maintenance_mode():

                try:
                    await callback_query.answer(
                        "🔧 Bot is currently under maintenance.",
                        show_alert=True
                    )
                except Exception:
                    pass

                raise StopPropagation

        except StopPropagation:
            raise

        except Exception as e:
            logger.error(
                f"Callback maintenance check failed for {user_id}: {e}"
            )
