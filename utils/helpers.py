import re
from datetime import datetime

from pyrogram.types import Message


# ============================================================
# MEDIA CHECK
# ============================================================

def is_media_message(message: Message) -> bool:
    """
    Check whether a Telegram message contains
    a supported media/file type.
    """

    if message.document:
        return True

    if message.video:
        return True

    if message.audio:
        return True

    return False


# ============================================================
# GET FILE NAME
# ============================================================

def get_original_filename(message: Message) -> str:
    """
    Get the original filename from Telegram media.
    """

    if message.document:

        return (
            message.document.file_name
            or ""
        )

    if message.video:

        return (
            message.video.file_name
            or ""
        )

    if message.audio:

        return (
            message.audio.file_name
            or ""
        )

    return ""


# ============================================================
# REMOVE FILE EXTENSION
# ============================================================

def remove_extension(filename: str) -> str:

    if not filename:
        return ""

    return re.sub(
        r"\.(mkv|mp4|avi|mov|webm|flv|wmv|"
        r"mp3|m4a|aac|flac|wav|zip|rar|7z)$",
        "",
        filename,
        flags=re.IGNORECASE
    )


# ============================================================
# CLEAN TITLE
# ============================================================

def clean_title(title: str) -> str:
    """
    Convert a filename into a cleaner searchable title.
    """

    if not title:
        return ""

    title = str(title)

    # Remove extension.
    title = remove_extension(
        title
    )

    # Replace common separators.
    title = re.sub(
        r"[._]+",
        " ",
        title
    )

    title = re.sub(
        r"[-]+",
        " ",
        title
    )

    # Resolution.
    title = re.sub(
        r"\b(2160p|1440p|1080p|720p|576p|480p|360p)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Quality names.
    title = re.sub(
        r"\b(4k|2k|uhd|fhd|hd)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Release sources.
    title = re.sub(
        r"\b("
        r"web[- ]?dl|"
        r"web[- ]?rip|"
        r"bluray|"
        r"blu[- ]?ray|"
        r"bdrip|"
        r"brrip|"
        r"dvdrip|"
        r"hdtv"
        r")\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Video codecs.
    title = re.sub(
        r"\b("
        r"x264|"
        r"x265|"
        r"h264|"
        r"h265|"
        r"hevc|"
        r"av1"
        r")\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Audio codecs.
    title = re.sub(
        r"\b("
        r"aac|"
        r"ac3|"
        r"ddp|"
        r"dd5\.1|"
        r"dts|"
        r"atmos"
        r")\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Remove S01E01 style markers.
    title = re.sub(
        r"\bS\d{1,2}E\d{1,3}\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Remove excessive spaces.
    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ============================================================
# GET MESSAGE TITLE
# ============================================================

def get_message_title(message: Message) -> str:
    """
    Determine the searchable title for a Telegram media message.
    """

    filename = get_original_filename(
        message
    )

    if filename:

        title = clean_title(
            filename
        )

        if title:
            return title

    # If no filename exists, use the first caption line.
    if message.caption:

        first_line = (
            message.caption
            .split("\n")[0]
            .strip()
        )

        if first_line:

            title = clean_title(
                first_line
            )

            if title:
                return title

    return "Untitled Media"


# ============================================================
# SEARCH NORMALIZATION
# ============================================================

def normalize_search_text(text: str) -> str:
    """
    Normalize user search input.

    Example:

        Avengers: Endgame!
        
    becomes:

        avengers endgame
    """

    if not text:
        return ""

    text = str(
        text
    ).lower()

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
# SEARCH KEY
# ============================================================

def get_search_key(title: str) -> str:
    """
    Create a normalized search key for MongoDB.
    """

    return normalize_search_text(
        clean_title(title)
    )


# ============================================================
# FILE SIZE
# ============================================================

def human_size(size) -> str:
    """
    Convert bytes into a readable size.
    """

    if not size:
        return "Unknown"

    try:
        size = float(size)
    except (TypeError, ValueError):
        return "Unknown"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    for unit in units:

        if size < 1024:

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} PB"


# ============================================================
# SHORTEN TEXT
# ============================================================

def shorten(
    text,
    length=50
) -> str:

    if not text:
        return ""

    text = str(
        text
    )

    if len(text) <= length:
        return text

    return (
        text[:length - 3]
        + "..."
    )


# ============================================================
# ESCAPE HTML
# ============================================================

def escape_html(text) -> str:
    """
    Safely escape text before putting it into
    Telegram HTML messages.
    """

    if text is None:
        return ""

    text = str(
        text
    )

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ============================================================
# CURRENT UTC TIME
# ============================================================

def utc_now():
    """
    Return current UTC datetime.
    """

    return datetime.utcnow()
