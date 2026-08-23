import re

from pyrogram.types import Message


# ============================================================
# VIDEO / DOCUMENT / AUDIO CHECK
# ============================================================

def is_media_message(message: Message):

    if message.document:
        return True

    if message.video:
        return True

    if message.audio:
        return True

    return False


# ============================================================
# GET ORIGINAL FILE NAME
# ============================================================

def get_original_filename(message):

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

def remove_extension(
    filename
):

    if not filename:
        return ""

    return re.sub(
        r"\.(mkv|mp4|avi|mov|webm|flv|wmv|mp3|m4a|aac|flac|wav|zip|rar|7z)$",
        "",
        filename,
        flags=re.IGNORECASE
    )


# ============================================================
# CLEAN TITLE
# ============================================================

def clean_title(
    title
):

    if not title:
        return ""

    title = str(
        title
    )

    title = remove_extension(
        title
    )

    # Replace separators with spaces.
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

    # Remove common technical tags.
    title = re.sub(
        r"\b(2160p|1440p|1080p|720p|576p|480p|360p)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\b(4k|2k|uhd|fhd|hd)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\b(web[- ]?dl|web[- ]?rip|bluray|blu[- ]?ray|bdrip|brrip|dvdrip)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\b(x264|x265|h264|h265|hevc|av1)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\b(aac|ac3|ddp|dd5\.1|dts|atmos)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Remove season/episode technical markers only
    # from the searchable title when appropriate.
    title = re.sub(
        r"\bS\d{1,2}E\d{1,3}\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    # Remove repeated whitespace.
    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ============================================================
# GET MESSAGE TITLE
# ============================================================

def get_message_title(
    message: Message
):

    filename = get_original_filename(
        message
    )

    if filename:

        return clean_title(
            filename
        )

    if message.caption:

        first_line = (
            message.caption
            .split("\n")[0]
            .strip()
        )

        if first_line:

            return clean_title(
                first_line
            )

    return "Untitled Media"


# ============================================================
# SEARCH NORMALIZATION
# ============================================================

def normalize_search_text(
    text
):

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
# GET SEARCH KEY
# ============================================================

def get_search_key(
    title
):

    return normalize_search_text(
        clean_title(title)
    )


# ============================================================
# FORMAT FILE SIZE
# ============================================================

def human_size(
    size
):

    if not size:
        return "Unknown"

    size = float(
        size
    )

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    for unit in units:

        if size < 1024:

            return (
                f"{size:.2f} {unit}"
            )

        size /= 1024

    return (
        f"{size:.2f} PB"
    )


# ============================================================
# SHORTEN TEXT
# ============================================================

def shorten(
    text,
    length=50
):

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
