from database import media_collection

from utils.helpers import (
    clean_title
)


async def search_movies(
    query,
    limit=10,
    skip=0
):

    query = query.strip()

    if not query:
        return []

    # --------------------------------------------------------
    # First use MongoDB text search.
    # --------------------------------------------------------

    try:

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

        results = await cursor.to_list(
            length=limit
        )

        if results:
            return results

    except Exception as e:

        print(
            f"Text search error: {e}"
        )


    # --------------------------------------------------------
    # Fallback search.
    # --------------------------------------------------------

    title_key = clean_title(
        query
    )

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
                },
                {
                    "caption": regex
                }
            ]
        }
    ).skip(
        skip
    ).limit(
        limit
    )

    return await cursor.to_list(
        length=limit
    )


async def count_search_results(
    query
):

    query = query.strip()

    if not query:
        return 0

    try:

        count = await media_collection.count_documents(
            {
                "$text": {
                    "$search": query
                }
            }
        )

        if count:
            return count

    except Exception:
        pass

    title_key = clean_title(
        query
    )

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
                },
                {
                    "caption": regex
                }
            ]
        }
    )
