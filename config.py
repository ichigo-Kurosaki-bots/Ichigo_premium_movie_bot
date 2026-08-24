import os


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Your Telegram private database channel ID.
# Example: -1001234567890
DATABASE_CHANNEL_ID = int(os.getenv("DATABASE_CHANNEL_ID", "0"))


# ============================================================
# OWNER / ADMINS
# ============================================================

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Optional additional admins.
# Example:
# ADMIN_IDS=123456789,987654321
ADMIN_IDS = set()

for admin_id in os.getenv("ADMIN_IDS", "").split(","):
    admin_id = admin_id.strip()

    if admin_id.isdigit():
        ADMIN_IDS.add(int(admin_id))

if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)


LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# ============================================================
# STORAGE
# ============================================================

STORAGE_LIMIT_MB = float(
    os.getenv(
        "STORAGE_LIMIT_MB",
        "512"
    )
)


# ============================================================
# DATABASE
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "")

DB_NAME = os.getenv(
    "DB_NAME",
    "premium_movie_bot"
)


# ============================================================
# BOT SETTINGS
# ============================================================

BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    ""
)

UPDATES_CHANNEL = os.getenv(
    "UPDATES_CHANNEL",
    ""
)

PORT = int(
    os.getenv("PORT", "8080")
)


# ============================================================
# FREE PLAN
# ============================================================

FREE_REQUESTS = 5


# ============================================================
# PREMIUM PLANS
# ============================================================

PREMIUM_PLANS = {
    10: {
        "name": "Starter",
        "requests": 20
    },

    20: {
        "name": "Basic",
        "requests": 30
    },

    50: {
        "name": "Plus",
        "requests": 75
    },

    100: {
        "name": "Pro",
        "requests": 150
    },

    200: {
        "name": "Premium",
        "requests": 300
    },

    500: {
        "name": "Ultra",
        "requests": 600
    },

    1000: {
        "name": "Ultimate",
        "requests": 1000
    }
}


# ============================================================
# SEARCH
# ============================================================

RESULTS_PER_PAGE = int(
    os.getenv("RESULTS_PER_PAGE", "10")
)

MAX_RESULTS = int(
    os.getenv("MAX_RESULTS", "50")
)


# ============================================================
# FILE DELIVERY
# ============================================================

# Files sent by the bot can optionally be automatically
# deleted after this many seconds.
#
# Set 0 to disable automatic deletion.

DELETE_AFTER = int(
    os.getenv("DELETE_AFTER", "0")
)


# ============================================================
# INDEXER
# ============================================================

# Number of Telegram messages processed per indexing batch.

INDEX_BATCH_SIZE = int(
    os.getenv("INDEX_BATCH_SIZE", "100")
)


# ============================================================
# LOGGING
# ============================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)
