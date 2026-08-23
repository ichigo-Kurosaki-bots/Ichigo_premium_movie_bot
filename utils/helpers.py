import re


def clean_title(title):

    if not title:
        return ""

    title = title.lower()

    title = re.sub(
        r"[\[\]\(\)\{\}_\-\.]+",
        " ",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


def get_message_title(message):

    if message.document:

        return (
            message.document.file_name
            or "Unknown File"
        )

    if message.video:

        return (
            message.video.file_name
            or "Unknown Video"
        )

    if message.audio:

        return (
            message.audio.file_name
            or "Unknown Audio"
        )

    if message.caption:

        return message.caption[:200]

    return "Unknown Media"


def is_media_message(message):

    return bool(
        message.document
        or message.video
        or message.audio
    )


def format_file_size(size):

    if not size:
        return "Unknown"

    size = float(size)

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
