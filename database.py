import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

from config import MONGO_URI, DB_NAME, FREE_REQUESTS


logger = logging.getLogger(__name__)


# ============================================================
# MONGODB CONNECTION
# ============================================================

mongo_client = None
db = None

users_collection = None
media_collection = None
search_sessions_collection = None
settings_collection = None


# ============================================================
# CONNECT DATABASE
# ============================================================

async def init_database():

    global mongo_client
    global db
    global users_collection
    global media_collection
    global search_sessions_collection
    global settings_collection

    if not MONGO_URI:
        raise RuntimeError(
            "MONGO_URI is not configured."
        )

    mongo_client = AsyncIOMotorClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    # Test MongoDB connection.
    await mongo_client.admin.command("ping")

    db = mongo_client[DB_NAME]

    users_collection = db["users"]

    media_collection = db["media"]

    search_sessions_collection = db[
        "search_sessions"
    ]

    settings_collection = db[
        "settings"
    ]

    # --------------------------------------------------------
    # USER INDEX
    # --------------------------------------------------------

    await users_collection.create_index(
        "user_id",
        unique=True
    )

    # --------------------------------------------------------
    # MEDIA INDEXES
    # --------------------------------------------------------

    await media_collection.create_index(
        "message_id"
    )

    await media_collection.create_index(
        "title_key"
    )

    await media_collection.create_index(
        "search_key"
    )

    await media_collection.create_index(
        [
            ("channel_id", 1),
            ("message_id", 1)
        ],
        unique=True
    )

    # --------------------------------------------------------
    # SEARCH SESSION INDEX
    # --------------------------------------------------------

    await search_sessions_collection.create_index(
        "session_id",
        unique=True
    )

    await search_sessions_collection.create_index(
        "user_id"
    )

    logger.info(
        "MongoDB connected successfully."
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

        logger.info(
            "MongoDB connection closed."
        )


# ============================================================
# USER
# ============================================================

async def create_user(
    user_id,
    first_name="",
    username=""
):
    now = datetime.utcnow()

    first_name = first_name or ""
    username = username or ""

    await users_collection.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": {
                "first_name": first_name,
                "username": username,
                "updated_at": now
            },

            "$setOnInsert": {
                "user_id": user_id,
                "premium": False,
                "plan": None,
                "paid_amount": 0,
                "premium_requests": 0,
                "remaining_requests": FREE_REQUESTS,
                "total_requests_used": 0,
                "created_at": now
            }
        },
        upsert=True
    )

    return await get_user(user_id)
    

async def get_user(user_id):

    return await users_collection.find_one(
        {
            "user_id": user_id
        }
    )


async def update_user(
    user_id,
    first_name=None,
    username=None
):

    update = {
        "updated_at": datetime.utcnow()
    }

    if first_name is not None:
        update["first_name"] = first_name

    if username is not None:
        update["username"] = username

    await users_collection.update_one(

        {
            "user_id": user_id
        },

        {
            "$set": update
        }
    )


# ============================================================
# REQUEST SYSTEM
# ============================================================

async def consume_request(user_id):

    """
    Atomically consume exactly one request.

    Returns:
        True  -> request consumed
        False -> no requests available
    """

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

        return_document=ReturnDocument.AFTER
    )

    return result is not None


async def restore_request(user_id):

    """
    Restore one request if Telegram file delivery fails.
    """

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
# PREMIUM
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


async def remove_premium(user_id):

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
# MEDIA INDEX
# ============================================================

async def add_media(data):

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


async def count_media():

    return await media_collection.count_documents(
        {}
    )


# ============================================================
# SEARCH SESSIONS
# ============================================================

async def create_search_session(
    user_id,
    query
):

    import secrets

    session_id = secrets.token_hex(8)

    document = {

        "session_id": session_id,

        "user_id": user_id,

        "query": query,

        "created_at":
            datetime.utcnow()
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


# ============================================================
# STATISTICS
# ============================================================

async def count_users():

    return await users_collection.count_documents(
        {}
    )


async def count_premium_users():

    return await users_collection.count_documents(
        {
            "premium": True
        }
    )


async def get_stats():

    users = await count_users()

    premium_users = await count_premium_users()

    media = await count_media()

    return {

        "users": users,

        "premium_users":
            premium_users,

        "media": media
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
# SEARCH MEDIA
# ============================================================

async def search_media(
    query,
    skip=0,
    limit=10
):
    """
    Search indexed media by title, filename,
    search key, or caption.
    """

    if not query:
        return []

    query = str(query).strip()

    if not query:
        return []

    import re

    # Escape user input so it is treated as normal
    # search text rather than a raw regular expression.
    pattern = re.escape(query)

    regex = {
        "$regex": pattern,
        "$options": "i"
    }

    cursor = media_collection.find(
        {
            "$or": [
                {
                    "title": regex
                },
                {
                    "file_name": regex
                },
                {
                    "search_key": regex
                },
                {
                    "caption": regex
                }
            ]
        }
    ).sort(
        "message_id",
        -1
    ).skip(
        int(skip)
    ).limit(
        int(limit)
    )

    return await cursor.to_list(
        length=int(limit)
    )
