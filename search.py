import re

from database import (
    media_collection
)

from config import (
    MAX_RESULTS,
    RESULTS_PER_PAGE
)


# ============================================================
# NORMALIZE QUERY
# ============================================================

def normalize_query(text):

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# SEARCH MOVIES
# ============================================================

async def search_movies(
    query,
    page=0
):

    query = normalize_query(
        query
    )

    if not query:
        return [], False

    if page < 0:
        page = 0

    # --------------------------------------------------------
    # Escape query for MongoDB regex.
    # --------------------------------------------------------

    pattern = re.escape(
        query
    )

    # --------------------------------------------------------
    # Search title + original filename.
    # --------------------------------------------------------

    search_filter = {
        "$or": [
            {
                "title": {
                    "$regex": pattern,
                    "$options": "i"
                }
            },
            {
                "file_name": {
                    "$regex": pattern,
                    "$options": "i"
                }
            }
        ]
    }

    # --------------------------------------------------------
    # Calculate pagination.
    # --------------------------------------------------------

    skip = (
        page * RESULTS_PER_PAGE
    )

    # Don't allow extremely large offsets.
    if skip >= MAX_RESULTS:

        return [], False

    # We request one extra result.
    # This tells us whether a next page exists.
    limit = RESULTS_PER_PAGE + 1

    cursor = (
        media_collection
        .find(search_filter)
        .sort(
            "message_id",
            -1
        )
        .skip(skip)
        .limit(limit)
    )

    results = []

    async for item in cursor:

        results.append(
            item
        )

    has_next = (
        len(results)
        > RESULTS_PER_PAGE
    )

    results = results[
        :RESULTS_PER_PAGE
    ]

    return (
        results,
        has_next
    )
