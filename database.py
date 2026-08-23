import logging
import secrets
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    MONGO_URI,
    DB_NAME,
    FREE_REQUESTS
)


logger = logging.getLogger(
    "premium_movie_bot.database"
)


# ============================================================
# MONGODB
# ============================================================

mongo_client = None
db = None
users_collection = None
media_collection = None
admins_collection = None
settings_collection = None
search_sessions_collection = None

# ============================================================
# INITIALIZE DATABASE
# ============================================================

async def init_database():

    global mongo_client
    global db
    global users_collection
    global media_collection
    global admins_collection
    global settings_collection
    global search_sessions_collection

    if not MONGO_URI:

        raise RuntimeError(
            "MONGO_URI is missing."
        )

    mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    # Test connection.
    await mongo_client.admin.command(
        "ping"
    )

    db = mongo_client[
        DB_NAME
    ]

    users_collection = db[
        "users"
    ]

    media_collection = db[
        "media"
    ]

    admins_collection = db[
        "admins"
    ]

    settings_collection = db[
        "settings"
    ]

    search_sessions_collection = db[
        "search_sessions"
    ]

    # --------------------------------------------------------
    # USER INDEXES
    # --------------------------------------------------------

    await users_collection.create_index(
        "user_id",
        unique=True
    )

    await users_collection.create_index(
        "username"
    )

    await users_collection.create_index(
        "premium"
    )

    # --------------------------------------------------------
    # MEDIA INDEXES
    # --------------------------------------------------------

    await media_collection.create_index(
        [
            ("title_key", 1)
        ]
    )

    await media_collection.create_index(
        [
            ("search_key", 1)
        ]
    )

    await media_collection.create_index(
        [
            ("message_id", 1)
        ]
    )

    await media_collection.create_index(
        [
            ("channel_id", 1),
            ("message_id", 1)
        ],
        unique=True
    )

    await search_sessions_collection.create_index(
              "session_id",
              unique=True
    )

    await search_sessions_collection.create_index(
              "user_id"
    )

    # --------------------------------------------------------
    # SETTINGS INDEX
    # --------------------------------------------------------

    await settings_collection.create_index(
        "_id",
        unique=True
    )

    logger.info(
        "MongoDB indexes ready."
    )


# ============================================================
# CLOSE DATABASE
# ============================================================

async def close_database():

    global mongo_client

    if mongo_client:

        mongo_client.close()

        mongo_client = None


# ============================================================
# CREATE USER
# ============================================================

async def create_user(
    user_id,
    first_name=None,
    username=None
):

    now = datetime.utcnow()

    document = {

        "user_id": user_id,

        "first_name": (
            first_name or ""
        ),

        "username": (
            username or ""
        ),

        "premium": False,

        "plan": None,

        "paid_amount": 0,

        "premium_requests": 0,

        "remaining_requests": FREE_REQUESTS,

        "total_requests_used": 0,

        "created_at": now,

        "updated_at": now
    }

    await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$setOnInsert": document,

            "$set": {
                "updated_at": now
            }
        },

        upsert=True
    )

    return await get_user(
        user_id
    )


# ============================================================
# GET USER
# ============================================================

async def get_user(
    user_id
):

    return await users_collection.find_one(
        {
            "user_id": user_id
        }
    )


# ============================================================
# UPDATE USER PROFILE
# ============================================================

async def update_user_profile(
    user_id,
    first_name=None,
    username=None
):

    await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$set": {
                "first_name": (
                    first_name or ""
                ),

                "username": (
                    username or ""
                ),

                "updated_at":
                    datetime.utcnow()
            }
        },

        upsert=True
    )


# ============================================================
# ATOMIC REQUEST CONSUMPTION
# ============================================================

async def consume_request(
    user_id
):

    result = await users_collection.find_one_and_update(

        {
            "user_id": user_id,

            "remaining_requests": {
                "$gt": 0
            }
        },

        {
            "$inc": {
                "remaining_requests": -1,

                "total_requests_used": 1
            },

            "$set": {
                "updated_at":
                    datetime.utcnow()
            }
        },

        return_document=True
    )

    return result is not None


# ============================================================
# RESTORE REQUEST
#
# Used if file delivery fails after charging the request.
# ============================================================

async def restore_request(
    user_id
):

    result = await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$inc": {
                "remaining_requests": 1,

                "total_requests_used": -1
            },

            "$set": {
                "updated_at":
                    datetime.utcnow()
            }
        }
    )

    return result.modified_count > 0


# ============================================================
# ACTIVATE PREMIUM
# ============================================================

async def activate_premium(
    user_id,
    plan_name,
    amount,
    requests
):

    result = await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$set": {

                "premium": True,

                "plan": plan_name,

                "paid_amount": amount,

                "premium_requests": requests,

                "remaining_requests": requests,

                "premium_activated_at":
                    datetime.utcnow(),

                "updated_at":
                    datetime.utcnow()
            }
        }
    )

    return result.modified_count > 0


# ============================================================
# REMOVE PREMIUM
# ============================================================

async def remove_premium(
    user_id
):

    result = await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$set": {

                "premium": False,

                "plan": None,

                "paid_amount": 0,

                "premium_requests": 0,

                "remaining_requests":
                    FREE_REQUESTS,

                "premium_removed_at":
                    datetime.utcnow(),

                "updated_at":
                    datetime.utcnow()
            }
        }
    )

    return result.modified_count > 0


# ============================================================
# ADD MEDIA
# ============================================================

async def add_media(
    data
):

    if not data:

        return False

    channel_id = data.get(
        "channel_id"
    )

    message_id = data.get(
        "message_id"
    )

    if channel_id is None:
        return False

    if message_id is None:
        return False

    await media_collection.update_one(

        {
            "channel_id": channel_id,

            "message_id": message_id
        },

        {
            "$set": data
        },

        upsert=True
    )

    return True


# ============================================================
# GET MEDIA
# ============================================================

async def get_media(
    channel_id,
    message_id
):

    return await media_collection.find_one(

        {
            "channel_id": channel_id,

            "message_id": message_id
        }
    )


# ============================================================
# COUNT USERS
# ============================================================

async def count_users():

    return await users_collection.count_documents(
        {}
    )


# ============================================================
# COUNT PREMIUM USERS
# ============================================================

async def count_premium_users():

    return await users_collection.count_documents(
        {
            "premium": True
        }
    )


# ============================================================
# COUNT MEDIA
# ============================================================

async def count_media():

    return await media_collection.count_documents(
        {}
    )


# ============================================================
# BOT STATS
# ============================================================

async def get_stats():

    total_users = await count_users()

    premium_users = await count_premium_users()

    total_media = await count_media()

    return {

        "users":
            total_users,

        "premium_users":
            premium_users,

        "media":
            total_media
    }


# ============================================================
# INDEXER STATE
# ============================================================

async def get_indexer_state():

    state = await settings_collection.find_one(
        {
            "_id": "indexer"
        }
    )

    if not state:

        return {

            "last_message_id": 0,

            "indexed_count": 0,

            "updated_at": None
        }

    return state


# ============================================================
# SAVE INDEXER STATE
# ============================================================

async def save_indexer_state(
    last_message_id,
    indexed_count
):

    await settings_collection.update_one(

        {
            "_id": "indexer"
        },

        {
            "$set": {

                "last_message_id":
                    last_message_id,

                "indexed_count":
                    indexed_count,

                "updated_at":
                    datetime.utcnow()
            }
        },

        upsert=True
    )


# ============================================================
# RESET INDEXER
# ============================================================

async def reset_indexer():

    await settings_collection.update_one(

        {
            "_id": "indexer"
        },

        {
            "$set": {

                "last_message_id": 0,

                "indexed_count": 0,

                "updated_at":
                    datetime.utcnow()
            }
        },

        upsert=True
    )


# ============================================================
# DELETE MEDIA INDEX
# ============================================================

async def delete_media_index():

    result = await media_collection.delete_many(
        {}
    )

    return result.deleted_count

# ============================================================
# SEARCH SESSIONS
# ============================================================

async def create_search_session(
    user_id,
    query
):

    session_id = secrets.token_hex(
        8
    )

    document = {
        "session_id": session_id,
        "user_id": user_id,
        "query": query,
        "created_at": datetime.utcnow()
    }

    await search_sessions_collection.insert_one(
        document
    )

    return session_id


async def get_search_session(
    session_id,
    user_id
):

    return await search_sessions_collection.find_one(
        {
            "session_id": session_id,
            "user_id": user_id
        }
    )


async def delete_search_session(
    session_id
):

    await search_sessions_collection.delete_one(
        {
            "session_id": session_id
        }
    )
