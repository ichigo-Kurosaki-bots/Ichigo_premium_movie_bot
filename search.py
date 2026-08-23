from database import media_collection
from utils.helpers import clean_title


async def search_movies(
    query,
    limit=10,
    skip=0
):
    """
    Search indexed media in MongoDB.

    Searches:
    - title
    - normalized title
    - filename
    """

    query = query.strip()

    if not query:
        return []

    title_key = clean_title(query)

    # First try exact/prefix-style search
    regex = {
        "$regex": title_key,
        "$options": "i"
    }

    cursor = media_collection.find(
        {
            "$or": [
                {
                    "title": regex
                },
                {
                    "title_key": regex
                },
                {
                    "file_name": regex
                }
            ]
        }
    ).sort(
        "title",
        1
    ).skip(
        skip
    ).limit(
        limit
    )

    return await cursor.to_list(
        length=limit
    )


async def count_search_results(query):
    """
    Return the number of matching files.
    """

    query = query.strip()

    if not query:
        return 0

    title_key = clean_title(query)

    regex = {
        "$regex": title_key,
        "$options": "i"
    }

    return await media_collection.count_documents(
        {
            "$or": [
                {
                    "title": regex
                },
                {
                    "title_key": regex
                },
                {
                    "file_name": regex
                }
            ]
        }
    )
