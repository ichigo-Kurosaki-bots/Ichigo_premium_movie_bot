# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

import os
import re
import glob
import asyncio
import logging
from urllib.parse import urlparse

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

import yt_dlp
from pyrogram import filters
from pyrogram.types import Message

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# URL CHECK
# ============================================================

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
        )

    except Exception:
        return False

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# TELEGRAM PUBLIC POST
# ============================================================

TELEGRAM_PUBLIC_RE = re.compile(
    r"^(?:https?://)?t\.me/([A-Za-z0-9_]+)/(\d+)(?:\?.*)?$",
    re.IGNORECASE
)


def parse_telegram_public_post(url: str):
    match = TELEGRAM_PUBLIC_RE.match(url.strip())

    if not match:
        return None

    username = match.group(1)
    message_id = int(match.group(2))

    return username, message_id

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# FIND DOWNLOADED FILE
# ============================================================

def find_downloaded_file(prefix: str):
    files = []

    for path in glob.glob(
        os.path.join(
            DOWNLOAD_DIR,
            f"{prefix}.*"
        )
    ):
        if os.path.isfile(path):
            files.append(path)

    if not files:
        return None

    files.sort(
        key=lambda x: os.path.getsize(x),
        reverse=True
    )

    return files[0]

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# ------------------------ #

# ============================================================
# DOWNLOAD USING YT-DLP
# ============================================================

async def download_media(url: str, prefix: str):

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{prefix}.%(ext)s"
    )

    # Detect YouTube URLs including /live/ URLs
    parsed = urlparse(url)
    hostname = parsed.netloc.lower().split(":")[0]

    is_youtube = (
        hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
        or hostname == "youtu.be"
        or hostname.endswith(".youtu.be")
    )

    ydl_opts = {
        # Try normal combined formats first, then separate
        # video/audio streams and finally best available.
        "format": (
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/"
            "bestvideo+bestaudio/"
            "best"
        ),

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "noplaylist": True,

        "quiet": True,
        "no_warnings": True,

        "restrictfilenames": True,

        # Better network reliability.
        "socket_timeout": 60,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "extractor_retries": 5,

        "concurrent_fragment_downloads": 4,

        # Continue when an individual fragment is unavailable.
        "skip_unavailable_fragments": True,

        # Never expand playlists.
        "extract_flat": False,

        # No login/cookies.
        "cookiefile": None,
    }

    # --------------------------------------------------------
    # YouTube-specific options
    # --------------------------------------------------------

    if is_youtube:

        ydl_opts.update({
            # Helps with currently-live YouTube streams.
            "live_from_start": True,

            # Wait briefly when a live video is not immediately
            # available.
            "wait_for_video": (5, 30),

            # Prefer HLS/DASH-capable YouTube extraction.
            "hls_prefer_native": True,

            # Allow extractor to use the standard YouTube
            # player clients.
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android",
                        "web"
                    ]
                }
            },
        })

    loop = asyncio.get_running_loop()

    def run_download():

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
            }

    try:

        info = await loop.run_in_executor(
            None,
            run_download
        )

        file_path = find_downloaded_file(prefix)

        if not file_path:
            return None, info

        return file_path, info

    except Exception as e:

        logger.exception(
            f"yt-dlp download failed for {url}: {e}"
        )

        return None, None

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# CLEANUP
# ============================================================

def cleanup_file(file_path: str):

    try:

        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:

        logger.warning(
            f"Failed to remove downloaded file: {e}"
        )

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# TELEGRAM PUBLIC MEDIA
# ============================================================

async def send_telegram_public_post(
    client,
    message: Message,
    username: str,
    message_id: int
):

    try:

        source_message = await client.get_messages(
            username,
            message_id
        )

        if not source_message:
            return False

        if source_message.empty:
            return False

        # Video
        if source_message.video:

            await message.reply_video(
                source_message.video.file_id
            )

            return True

        # Document
        if source_message.document:

            await message.reply_document(
                source_message.document.file_id
            )

            return True

        # Animation
        if source_message.animation:

            await message.reply_animation(
                source_message.animation.file_id
            )

            return True

        # Photo
        if source_message.photo:

            await message.reply_photo(
                source_message.photo.file_id
            )

            return True

        return False

    except Exception as e:

        logger.warning(
            f"Telegram public post failed: {e}"
        )

        return False

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #

# ============================================================
# VIDEO HANDLER
# ============================================================

def register_video_handlers(app):

    @app.on_message(
        filters.command("video")
        & filters.text
    )
    async def video_handler(client, message: Message):

        # ----------------------------------------------------
        # GET URL
        # ----------------------------------------------------

        command_parts = message.text.split(
            maxsplit=1
        )

        if len(command_parts) < 2:

            await message.reply_text(
                "❌ <b>Please provide a video URL.</b>\n\n"
                "Example:\n"
                "<code>/video https://youtu.be/Aiue8PMuD-k</code>"
            )

            return

        url = command_parts[1].strip()

        if not is_valid_url(url):

            await message.reply_text(
                "❌ <b>Invalid URL.</b>"
            )

            return

        # ----------------------------------------------------
        # TELEGRAM PUBLIC POST
        # ----------------------------------------------------

        telegram_post = parse_telegram_public_post(
            url
        )

        if telegram_post:

            username, message_id = telegram_post

            status = await message.reply_text(
                "⏳ <b>Getting media...</b>"
            )

            success = await send_telegram_public_post(
                client,
                message,
                username,
                message_id
            )

            try:
                await status.delete()
            except Exception:
                pass

            if not success:

                await message.reply_text(
                    "❌ <b>This Telegram post does not "
                    "contain accessible downloadable media.</b>"
                )

            return

        # ----------------------------------------------------
        # YT-DLP DOWNLOAD
        # ----------------------------------------------------

        status = await message.reply_text(
            "⏳ <b>Downloading...</b>"
        )

        prefix = (
            f"{message.chat.id}_"
            f"{message.id}"
        )

        file_path = None

        try:

            file_path, info = await download_media(
                url,
                prefix
            )

            # ------------------------------------------------
            # DOWNLOAD FAILED
            # ------------------------------------------------

            if not file_path:

                await status.edit_text(
                    "❌ <b>This video cannot be downloaded.</b>\n\n"
                    "The website may require login, use DRM, "
                    "be unavailable, or not be supported by yt-dlp."
                )

                return

            # ------------------------------------------------
            # CHECK FILE SIZE
            # ------------------------------------------------

            file_size = os.path.getsize(
                file_path
            )

            # ------------------------------------------------
            # UPLOAD
            # ------------------------------------------------

            await status.edit_text(
                "📤 <b>Uploading...</b>"
            )

            title = None

            if info:
                title = info.get("title")

            caption = (
                f"🎬 <b>{title}</b>"
                if title
                else "🎬 <b>Downloaded Media</b>"
            )

            # ------------------------------------------------
            # SEND VIDEO
            # ------------------------------------------------

            extension = os.path.splitext(
                file_path
            )[1].lower()

            video_extensions = {
                ".mp4",
                ".mkv",
                ".webm",
                ".mov",
                ".avi",
                ".flv",
                ".m4v",
            }

            if extension in video_extensions:

                await message.reply_video(
                    video=file_path,
                    caption=caption,
                    supports_streaming=True
                )

            else:

                await message.reply_document(
                    document=file_path,
                    caption=caption
                )

            # ------------------------------------------------
            # DONE
            # ------------------------------------------------

            try:
                await status.delete()
            except Exception:
                pass

        except Exception as e:

            logger.exception(
                f"Video handler error: {e}"
            )

            try:

                await status.edit_text(
                    "❌ <b>This video cannot be downloaded.</b>\n\n"
                    "The media may be unavailable, "
                    "login-required, DRM-protected, "
                    "or unsupported."
                )

            except Exception:
                pass

        finally:

            # ------------------------------------------------
            # ALWAYS CLEAN TEMP FILE
            # ------------------------------------------------

            if file_path:
                cleanup_file(file_path)

            # Also remove any leftover files
            for leftover in glob.glob(
                os.path.join(
                    DOWNLOAD_DIR,
                    f"{prefix}.*"
                )
            ):

                cleanup_file(leftover)

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity 
# Support : @Coders_Grp 
# ------------------------ #
