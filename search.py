import re

from database import (
    media_collection
)

from config import (
    MAX_RESULTS,
    RESULTS_PER_PAGE
)


# ============================================================
# CLEAN SEARCH QUERY
# ============================================================

def normalize_query(text):

    text = text.lower()

    # Remove common punctuation.
    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    # Remove extra spaces.
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
        return []


    # --------------------------------------------------------
    # MongoDB text-style regex search
    # --------------------------------------------------------

    pattern = re.escape(
        query
    )

    cursor = media_collection.find(
        {
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
    ).sort(
        "message_id",
        -1
    )


    # Maximum number of results.
    skip = page * RESULTS_PER_PAGE

    results = []

    async for item in cursor:

        if len(results) >= RESULTS_PER_PAGE:

            break

        if len(results) >= MAX_RESULTS:

            break

        results.append(
            item
        )

    return results
