
import re
import logging

from config import (
    RESULTS_PER_PAGE,
    MAX_RESULTS
)

from database import (
    search_media
)


logger = logging.getLogger(__name__)


# ============================================================
# CLEAN SEARCH QUERY
# ============================================================

def clean_query(query):
    """
    Clean the user's search text.
    """

    if not query:
        return ""

    query = str(query).strip()

    # Remove excessive spaces
    query = re.sub(
        r"\s+",
        " ",
        query
    )

    return query


# ============================================================
# NORMALIZE SEARCH QUERY
# ============================================================

def normalize_query(query):
    """
    Create a normalized search string.
    """

    query = clean_query(
        query
    )

    if not query:
        return ""

    return query.lower()


# ============================================================
# ESCAPE REGEX
# ============================================================

def escape_regex(text):
    """
    Prevent special regex characters from
    changing the MongoDB search pattern.
    """

    return re.escape(
        text
    )


# ============================================================
# CREATE SEARCH PATTERNS
# ============================================================

def create_search_patterns(query):
    """
    Creates useful search patterns.

    Example:

        Avengers Endgame

    becomes:

        [
            "Avengers Endgame",
            "Avengers",
            "Endgame"
        ]
    """

    query = normalize_query(
        query
    )

    if not query:
        return []

    patterns = []

    # Full query first
    patterns.append(
        query
    )

    # Individual words
    words = query.split()

    for word in words:

        if (
            len(word) >= 2
            and word not in patterns
        ):

            patterns.append(
                word
            )

    return patterns


# ============================================================
# SEARCH MOVIES
# ============================================================

async def search_movies(
    query,
    page=0
):
    """
    Search indexed media.

    Returns:

        results,
        has_next
    """

    query = clean_query(
        query
    )

    if not query:

        return [], False

    # --------------------------------------------------------
    # PAGE VALIDATION
    # --------------------------------------------------------

    try:

        page = int(
            page
        )

    except (
        TypeError,
        ValueError
    ):

        page = 0

    if page < 0:

        page = 0

    # --------------------------------------------------------
    # LIMIT
    # --------------------------------------------------------

    per_page = max(
        1,
        int(
            RESULTS_PER_PAGE
        )
    )

    max_results = max(
        per_page,
        int(
            MAX_RESULTS
        )
    )

    # Do not allow a single request
    # to retrieve more than MAX_RESULTS.
    max_page = (
        max_results - 1
    ) // per_page

    if page > max_page:

        return [], False

    # --------------------------------------------------------
    # SEARCH DATABASE
    # --------------------------------------------------------

    try:

        results = await search_media(
            query=query,
            skip=page * per_page,
            limit=per_page + 1
        )

    except Exception as e:

        logger.exception(
            "Database search failed: %s",
            e
        )

        raise

    if not results:

        return [], False

    # --------------------------------------------------------
    # DETERMINE NEXT PAGE
    # --------------------------------------------------------

    has_next = (
        len(results)
        > per_page
    )

    # Only return the requested number
    # of results.
    results = results[
        :per_page
    ]

    return (
        results,
        has_next
    )


# ============================================================
# SEARCH WITH MULTIPLE TERMS
# ============================================================

async def advanced_search(
    query,
    page=0
):
    """
    Search using the complete query and
    individual words.

    This function is useful when normal
    search needs broader matching.
    """

    query = clean_query(
        query
    )

    if not query:

        return [], False

    patterns = create_search_patterns(
        query
    )

    if not patterns:

        return [], False

    # --------------------------------------------------------
    # First try exact/full query
    # --------------------------------------------------------

    results, has_next = await search_movies(
        query=query,
        page=page
    )

    if results:

        return (
            results,
            has_next
        )

    # --------------------------------------------------------
    # Try individual words
    # --------------------------------------------------------

    combined = []

    seen_ids = set()

    for pattern in patterns[1:]:

        try:

            found, _ = await search_movies(
                query=pattern,
                page=0
            )

        except Exception:

            continue

        for item in found:

            message_id = item.get(
                "message_id"
            )

            unique_id = (
                message_id
                if message_id is not None
                else str(item.get("_id"))
            )

            if unique_id in seen_ids:

                continue

            seen_ids.add(
                unique_id
            )

            combined.append(
                item
            )

            if len(combined) >= MAX_RESULTS:

                break

        if len(combined) >= MAX_RESULTS:

            break

    # --------------------------------------------------------
    # PAGINATION FOR FALLBACK RESULTS
    # --------------------------------------------------------

    per_page = max(
        1,
        int(
            RESULTS_PER_PAGE
        )
    )

    start = (
        page * per_page
    )

    end = (
        start + per_page + 1
    )

    selected = combined[
        start:end
    ]

    has_next = (
        len(selected)
        > per_page
    )

    selected = selected[
        :per_page
    ]

    return (
        selected,
        has_next
    )


# ============================================================
# SEARCH BY EXACT TITLE
# ============================================================

async def search_exact_title(
    title
):
    """
    Search for an exact title.
    """

    title = clean_query(
        title
    )

    if not title:

        return []

    try:

        results = await search_media(
            query=title,
            skip=0,
            limit=MAX_RESULTS
        )

    except Exception as e:

        logger.exception(
            "Exact title search failed: %s",
            e
        )

        raise

    return results


# ============================================================
# SEARCH RESULT FORMATTER
# ============================================================

def get_result_title(
    result
):
    """
    Get a clean display title from
    an indexed MongoDB document.
    """

    title = (
        result.get("title")
        or result.get("file_name")
        or "Unknown File"
    )

    return str(
        title
    )


def get_result_message_id(
    result
):
    """
    Return the Telegram message ID
    associated with a search result.
    """

    return result.get(
        "message_id"
    )


# ============================================================
# END
# ============================================================
