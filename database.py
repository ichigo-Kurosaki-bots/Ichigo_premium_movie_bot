from motor.motor_asyncio import AsyncIOMotorClient

from config import (
    MONGO_URI,
    DB_NAME
)


# ============================================================
# MONGODB CONNECTION
# ============================================================

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI environment variable is missing."
    )


mongo_client = AsyncIOMotorClient(
    MONGO_URI
)

db = mongo_client[DB_NAME]


# ============================================================
# COLLECTIONS
# ============================================================

users_collection = db["users"]

media_collection = db["media"]

admins_collection = db["admins"]

settings_collection = db["settings"]


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

async def init_database():

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    await users_collection.create_index(
        "user_id",
        unique=True
    )

    # --------------------------------------------------------
    # MEDIA
    # --------------------------------------------------------

    await media_collection.create_index(
        [
            ("title", "text"),
            ("file_name", "text"),
            ("caption", "text")
        ],
        name="media_text_search"
    )

    await media_collection.create_index(
        "title_key"
    )

    await media_collection.create_index(
        "message_id"
    )

    await media_collection.create_index(
        "channel_id"
    )

    # --------------------------------------------------------
    # ADMINS
    # --------------------------------------------------------

    await admins_collection.create_index(
        "user_id",
        unique=True
    )

    print("MongoDB indexes ready.")


# ============================================================
# USER FUNCTIONS
# ============================================================

async def create_user(
    user_id,
    first_name="",
    username=""
):

    existing = await users_collection.find_one(
        {
            "user_id": user_id
        }
    )

    if existing:
        return existing

    user = {
        "user_id": user_id,

        "first_name": first_name or "",

        "username": username or "",

        # Free requests
        "free_requests": 5,

        # Request tracking
        "used_requests": 0,

        "total_requests": 0,

        "remaining_requests": 5,

        # Premium
        "premium": False,

        "plan": None,

        "paid_amount": 0,

        "premium_requests": 0,

        "activated_at": None
    }

    await users_collection.insert_one(
        user
    )

    return user


async def get_user(user_id):

    return await users_collection.find_one(
        {
            "user_id": user_id
        }
    )


async def update_user_info(
    user_id,
    first_name=None,
    username=None
):

    update = {}

    if first_name is not None:
        update["first_name"] = first_name

    if username is not None:
        update["username"] = username

    if not update:
        return

    await users_collection.update_one(
        {
            "user_id": user_id
        },
        {
            "$set": update
        }
    )


# ============================================================
# REQUEST COUNTER
# ============================================================

async def use_request(user_id):

    result = await users_collection.update_one(
        {
            "user_id": user_id,

            "remaining_requests": {
                "$gt": 0
            }
        },
        {
            "$inc": {
                "used_requests": 1,
                "total_requests": 1,
                "remaining_requests": -1
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

    from datetime import datetime

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

                "used_requests": 0,

                "total_requests": 0,

                "activated_at": datetime.utcnow()
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

                "remaining_requests": 0
            }
        }
    )

    return result.modified_count > 0


# ============================================================
# MEDIA
# ============================================================

async def add_media(media):

    await media_collection.update_one(
        {
            "channel_id": media["channel_id"],

            "message_id": media["message_id"]
        },
        {
            "$set": media
        },
        upsert=True
    )


async def search_media(
    query,
    limit=10,
    skip=0
):

    cursor = media_collection.find(
        {
            "$text": {
                "$search": query
            }
        },
        {
            "score": {
                "$meta": "textScore"
            }
        }
    ).sort(
        [
            (
                "score",
                {
                    "$meta": "textScore"
                }
            )
        ]
    ).skip(
        skip
    ).limit(
        limit
    )

    return await cursor.to_list(
        length=limit
    )


# ============================================================
# STATISTICS
# ============================================================

async def count_users():

    return await users_collection.count_documents(
        {}
    )


async def count_media():

    return await media_collection.count_documents(
        {}
    )


async def count_premium_users():

    return await users_collection.count_documents(
        {
            "premium": True
        }
    )
