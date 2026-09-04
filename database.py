import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

from config import (
    MONGO_URI,
    DB_NAME,
    FREE_REQUESTS,
    STORAGE_LIMIT_MB
)


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
chats_collection = None


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
    global chats_collection

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

    chats_collection = db[
        "chats"
    ]

    # --------------------------------------------------------
    # USER INDEX
    # --------------------------------------------------------

    await users_collection.create_index(
        "user_id",
        unique=True
    )

    await chats_collection.create_index(
        "chat_id",
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

                # TOKEN SYSTEM
                "tokens": 0,
                "last_token_claim": None,

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
# TOKEN SYSTEM
# ============================================================

async def get_token_balance(user_id):

    user = await users_collection.find_one(
        {
            "user_id": user_id
        },
        {
            "_id": 0,
            "tokens": 1
        }
    )

    if not user:
        return 0

    return int(
        user.get(
            "tokens",
            0
        ) or 0
    )


# ============================================================
# DAILY TOKEN CLAIM
# ============================================================

async def claim_daily_tokens(user_id):

    now = datetime.utcnow()

    user = await users_collection.find_one(
        {
            "user_id": user_id
        }
    )

    if not user:

        return {
            "success": False,
            "reason": "user_not_found",
            "tokens": 0
        }

    last_claim = user.get(
        "last_token_claim"
    )

    # --------------------------------------------------------
    # CHECK IF ALREADY CLAIMED TODAY
    # --------------------------------------------------------

    if last_claim:

        if last_claim.date() == now.date():

            return {
                "success": False,
                "reason": "already_claimed",
                "tokens": int(
                    user.get(
                        "tokens",
                        0
                    ) or 0
                )
            }

    # --------------------------------------------------------
    # GIVE 5 TOKENS
    # --------------------------------------------------------

    result = await users_collection.find_one_and_update(

        {
            "user_id": user_id,

            "$or": [
                {
                    "last_token_claim": None
                },
                {
                    "last_token_claim": {
                        "$exists": False
                    }
                },
                {
                    "last_token_claim": {
                        "$lt": datetime(
                            now.year,
                            now.month,
                            now.day
                        )
                    }
                }
            ]
        },

        {
            "$inc": {
                "tokens": 5
            },

            "$set": {
                "last_token_claim": now,
                "updated_at": now
            }
        },

        return_document=ReturnDocument.AFTER
    )

    if not result:

        # Check current balance so the UI can still show it.
        current = await get_token_balance(
            user_id
        )

        return {
            "success": False,
            "reason": "already_claimed",
            "tokens": current
        }

    return {
        "success": True,
        "reason": "claimed",
        "tokens": int(
            result.get(
                "tokens",
                0
            ) or 0
        )
    }


# ============================================================
# REDEEM 100 TOKENS FOR STARTER PREMIUM
# ============================================================

async def redeem_tokens_for_premium(
    user_id
):

    now = datetime.utcnow()

    result = await users_collection.find_one_and_update(

        {
            "user_id": user_id,

            "tokens": {
                "$gte": 100
            }
        },

        {
            "$inc": {
                "tokens": -100
            },

            "$set": {
                "premium": True,
                "plan": "Starter",
                "paid_amount": 0,
                "premium_requests": 20,
                "remaining_requests": 20,
                "updated_at": now
            }
        },

        return_document=ReturnDocument.AFTER
    )

    if not result:

        current = await users_collection.find_one(
            {
                "user_id": user_id
            }
        )

        if not current:

            return {
                "success": False,
                "reason": "user_not_found",
                "tokens": 0
            }

        return {
            "success": False,
            "reason": "insufficient_tokens",
            "tokens": int(
                current.get(
                    "tokens",
                    0
                ) or 0
            )
        }

    return {
        "success": True,
        "reason": "redeemed",
        "tokens": int(
            result.get(
                "tokens",
                0
            ) or 0
        ),
        "plan": "Starter",
        "requests": 20
    }

# ============================================================
# CHAT STATISTICS
# ============================================================

async def register_chat(
    chat_id,
    chat_type=None,
    title=None
):

    if chat_id is None:
        return False

    await chats_collection.update_one(

        {
            "chat_id": chat_id
        },

        {
            "$set": {
                "chat_id": chat_id,
                "chat_type": chat_type or "",
                "title": title or "",
                "updated_at": datetime.utcnow()
            },

            "$setOnInsert": {
                "created_at": datetime.utcnow()
            }
        },

        upsert=True
    )

    return True


async def count_chats():

    return await chats_collection.count_documents(
        {}
    )
    
# ============================================================
# REQUEST SYSTEM
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
                "updated_at": datetime.utcnow()
            }
        }
    )

    return result.matched_count > 0


async def remove_premium(user_id):

    result = await users_collection.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": {
                "premium": False,
                "plan": "Free",
                "paid_amount": 0,
                "premium_requests": 0,
                "remaining_requests": FREE_REQUESTS,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return result.matched_count > 0


async def consume_request(user_id):

    result = await users_collection.update_one(
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
                "updated_at": datetime.utcnow()
            }
        }
    )

    return result.matched_count > 0


async def restore_request(user_id):

    result = await users_collection.update_one(
        {
            "user_id": user_id,
            "total_requests_used": {
                "$gt": 0
            }
        },
        {
            "$inc": {
                "remaining_requests": 1,
                "total_requests_used": -1
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
    )

    return result.matched_count > 0

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
# MEDIA STORAGE STATISTICS
# ============================================================

async def get_media_storage_stats():

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_files": {
                    "$sum": 1
                },
                "total_size": {
                    "$sum": {
                        "$ifNull": [
                            "$file_size",
                            0
                        ]
                    }
                }
            }
        }
    ]

    result = await media_collection.aggregate(
        pipeline
    ).to_list(
        length=1
    )

    if not result:
        return {
            "total_files": 0,
            "total_size": 0
        }

    data = result[0]

    return {
        "total_files": data.get(
            "total_files",
            0
        ),
        "total_size": data.get(
            "total_size",
            0
        )
    }


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


async def count_media():

    return await media_collection.count_documents(
        {}
    )


async def count_chats():

    return await chats_collection.count_documents(
        {}
    )


async def get_total_file_size():

    pipeline = [

        {
            "$match": {
                "file_size": {
                    "$exists": True,
                    "$type": "number"
                }
            }
        },

        {
            "$group": {

                "_id": None,

                "total_size": {
                    "$sum": "$file_size"
                }
            }
        }
    ]

    result = await media_collection.aggregate(
        pipeline
    ).to_list(
        length=1
    )

    if not result:

        return 0

    return result[0].get(
        "total_size",
        0
    )


async def get_stats():

    users = await count_users()

    chats = await count_chats()

    premium_users = (
        await count_premium_users()
    )

    media = await count_media()

    total_size_bytes = (
        await get_total_file_size()
    )

    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    used_storage_mb = (
        total_size_bytes
        / (1024 * 1024)
    )

    free_storage_mb = max(
        STORAGE_LIMIT_MB
        - used_storage_mb,
        0
    )

    return {

        "users":
            users,

        "chats":
            chats,

        "premium_users":
            premium_users,

        "media":
            media,

        "total_size":
            total_size_bytes,

        "used_storage":
            used_storage_mb,

        "free_storage":
            free_storage_mb,

        "used_storage_text":
            f"{used_storage_mb:.2f} MB",

        "free_storage_text":
            f"{free_storage_mb:.2f} MB"
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

# ============================================================
# BROADCAST
# ============================================================

async def get_all_user_ids():
    """
    Get all registered Telegram user IDs.
    """

    cursor = users_collection.find(
        {},
        {
            "_id": 0,
            "user_id": 1
        }
    )

    users = await cursor.to_list(
        length=None
    )

    return [
        user["user_id"]
        for user in users
        if user.get("user_id") is not None
    ]

# ============================================================
# FORCE SUBSCRIBE
# ============================================================

async def get_fsub_channels():

    document = await settings_collection.find_one(
        {
            "_id": "fsub"
        }
    )

    if not document:
        return []

    return document.get(
        "channels",
        []
    )


async def add_fsub_channel(
    channel_data
):

    if not channel_data:
        return False

    chat_id = channel_data.get(
        "chat_id"
    )

    if chat_id is None:
        return False

    existing = await settings_collection.find_one(
        {
            "_id": "fsub",
            "channels.chat_id": chat_id
        }
    )

    if existing:

        return False

    await settings_collection.update_one(
        {
            "_id": "fsub"
        },
        {
            "$push": {
                "channels": channel_data
            }
        },
        upsert=True
    )

    return True


async def remove_fsub_channel(
    chat_id
):

    result = await settings_collection.update_one(
        {
            "_id": "fsub"
        },
        {
            "$pull": {
                "channels": {
                    "chat_id": chat_id
                }
            }
        }
    )

    return result.modified_count > 0

# ============================================================
# TRENDING SEARCHES
# ============================================================

async def record_search(query):
    """
    Record only real user search queries for /trendlist.

    Telegram commands starting with "/" are ignored.
    """

    if not query:
        return False

    query = str(query).strip()

    if not query:
        return False

    # --------------------------------------------------------
    # NEVER RECORD TELEGRAM COMMANDS
    # --------------------------------------------------------

    if query.startswith("/"):
        return False

    # --------------------------------------------------------
    # RECORD REAL SEARCH
    # --------------------------------------------------------

    await settings_collection.update_one(
        {
            "_id": "search_trends"
        },
        {
            "$inc": {
                f"queries.{query}": 1
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return True


async def get_trending_searches(limit=29):
    """
    Return the most searched real queries.

    Command-like entries starting with "/" are ignored.
    """

    document = await settings_collection.find_one(
        {
            "_id": "search_trends"
        }
    )

    if not document:
        return []

    queries = document.get(
        "queries",
        {}
    )

    if not queries:
        return []

    # --------------------------------------------------------
    # REMOVE COMMANDS FROM TRENDING RESULTS
    # --------------------------------------------------------

    valid_queries = {
        query: count
        for query, count in queries.items()
        if str(query).strip()
        and not str(query).strip().startswith("/")
    }

    if not valid_queries:
        return []

    sorted_queries = sorted(
        valid_queries.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return sorted_queries[:limit]
