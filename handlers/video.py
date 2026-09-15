import os
import re
import glob
import asyncio
import logging
import time
from urllib.parse import urlparse

import yt_dlp

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# ============================================================
# CONFIG
# ============================================================

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def format_bytes(size):
    if not size:
        return "Unknown"

    size = float(size)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"


def format_speed(speed):
    if not speed:
        return "0 B/s"

    return f"{format_bytes(speed)}/s"


def format_time(seconds):
    if seconds is None:
        return "Unknown"

    try:
        seconds = int(seconds)
    except Exception:
        return "Unknown"

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def is_valid_url(url):
    try:
        parsed = urlparse(url)

        return parsed.scheme in (
            "http",
            "https",
        ) and bool(parsed.netloc)

    except Exception:
        return False


# ============================================================
# TELEGRAM PUBLIC POST
# ============================================================

TELEGRAM_POST_REGEX = re.compile(
    r"(?:https?://)?t\.me/(?:c/)?"
    r"([A-Za-z0-9_]+)/(\d+)"
)


async def send_telegram_public_post(client, message, url):
    match = TELEGRAM_POST_REGEX.search(url)

    if not match:
        return None

    chat_username = match.group(1)
    message_id = int(match.group(2))

    try:
        post = await client.get_messages(
            chat_username,
            message_id
        )

        if not post:
            return None

        if post.video:
            return await client.download_media(post)

        if post.document:
            return await client.download_media(post)

        if post.audio:
            return await client.download_media(post)

        if post.animation:
            return await client.download_media(post)

    except Exception as e:
        LOGGER.error(
            "Telegram post download error: %s",
            e
        )

    return None


# ============================================================
# FIND DOWNLOADED FILE
# ============================================================

def find_downloaded_file(prefix):

    files = glob.glob(
        os.path.join(
            DOWNLOAD_DIR,
            f"{prefix}.*"
        )
    )

    if not files:
        return None

    files.sort(
        key=lambda x: os.path.getmtime(x),
        reverse=True
    )

    return files[0]


# ============================================================
# DOWNLOAD MEDIA
# ============================================================

async def download_media(
    url,
    prefix,
    progress_state,
    status_message
):

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{prefix}.%(ext)s"
    )

    progress_state.update({
        "status": "extracting",
        "filename": "",
        "total": 0,
        "downloaded": 0,
        "speed": 0,
        "eta": None,
        "start_time": time.time(),
    })

    def progress_hook(data):

        try:
            status = data.get("status")

            if status == "downloading":

                total = (
                    data.get("total_bytes")
                    or data.get("total_bytes_estimate")
                    or 0
                )

                downloaded = (
                    data.get("downloaded_bytes")
                    or 0
                )

                progress_state.update({
                    "status": "downloading",
                    "filename": data.get(
                        "filename",
                        ""
                    ),
                    "total": total,
                    "downloaded": downloaded,
                    "speed": data.get(
                        "speed",
                        0
                    ),
                    "eta": data.get(
                        "eta"
                    ),
                })

            elif status == "finished":

                progress_state.update({
                    "status": "extracting",
                    "downloaded": data.get(
                        "downloaded_bytes",
                        progress_state.get(
                            "downloaded",
                            0
                        )
                    ),
                    "total": (
                        data.get(
                            "total_bytes"
                        )
                        or progress_state.get(
                            "total",
                            0
                        )
                    ),
                    "speed": 0,
                    "eta": None,
                })

        except Exception as e:
            LOGGER.error(
                "Progress hook error: %s",
                e
            )

    def postprocessor_hook(data):

        try:
            progress_state["status"] = "extracting"
        except Exception:
            pass

    ydl_opts = {
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

        "socket_timeout": 60,

        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "extractor_retries": 5,

        "concurrent_fragment_downloads": 4,

        "skip_unavailable_fragments": True,

        "extract_flat": False,

        "progress_hooks": [
            progress_hook
        ],

        "postprocessor_hooks": [
            postprocessor_hook
        ],

        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    # ========================================================
    # YOUTUBE OPTIONS
    # ========================================================

    if "youtube.com" in url or "youtu.be" in url:

        ydl_opts.update({
            "hls_prefer_native": True,

            "live_from_start": True,

            "wait_for_video": (
                5,
                30
            ),

            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android",
                        "web"
                    ]
                }
            },
        })

    try:

        def blocking_download():

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = ydl.extract_info(
                    url,
                    download=True
                )

                return info

        loop = asyncio.get_running_loop()

        info = await loop.run_in_executor(
            None,
            blocking_download
        )

        progress_state["status"] = "finished"

        file_path = find_downloaded_file(
            prefix
        )

        if not file_path:

            # Try to get filename directly
            try:
                requested = (
                    info.get(
                        "requested_downloads"
                    )
                    or []
                )

                for item in requested:

                    filename = item.get(
                        "filepath"
                    )

                    if filename and os.path.exists(
                        filename
                    ):
                        file_path = filename
                        break

            except Exception:
                pass

        return file_path, info

    except Exception as e:

        LOGGER.exception(
            "yt-dlp download failed"
        )

        progress_state["status"] = "error"
        progress_state["error"] = str(e)

        return None, None


# ============================================================
# PROGRESS UPDATER
# ============================================================

async def update_progress(
    status_message,
    progress_state
):

    last_text = ""

    while True:

        try:

            status = progress_state.get(
                "status",
                "extracting"
            )

            start_time = progress_state.get(
                "start_time",
                time.time()
            )

            elapsed = int(
                time.time() - start_time
            )

            if status == "extracting":

                text = (
                    "🔍 **Extracting...**\n\n"
                    f"⏱ **Time:** `{format_time(elapsed)}`\n"
                    "📦 **Downloaded:** "
                    f"`{format_bytes(progress_state.get('downloaded', 0))}`"
                )

            elif status == "downloading":

                downloaded = progress_state.get(
                    "downloaded",
                    0
                )

                total = progress_state.get(
                    "total",
                    0
                )

                speed = progress_state.get(
                    "speed",
                    0
                )

                eta = progress_state.get(
                    "eta"
                )

                if total:

                    percentage = min(
                        100,
                        int(
                            downloaded
                            * 100
                            / total
                        )
                    )

                    bar_length = 12

                    filled = int(
                        bar_length
                        * percentage
                        / 100
                    )

                    bar = (
                        "█" * filled
                        + "░"
                        * (
                            bar_length
                            - filled
                        )
                    )

                    progress_line = (
                        f"`{bar}` "
                        f"**{percentage}%**"
                    )

                    size_line = (
                        f"`{format_bytes(downloaded)}`"
                        " / "
                        f"`{format_bytes(total)}`"
                    )

                else:

                    progress_line = (
                        "📊 **Progress:** `Unknown`"
                    )

                    size_line = (
                        f"`{format_bytes(downloaded)}`"
                    )

                text = (
                    "⬇️ **Downloading...**\n\n"
                    f"{progress_line}\n\n"
                    f"📦 **Size:** {size_line}\n"
                    f"🚀 **Speed:** "
                    f"`{format_speed(speed)}`\n"
                    f"⏱ **Time:** "
                    f"`{format_time(elapsed)}`\n"
                    f"⌛ **ETA:** "
                    f"`{format_time(eta)}`"
                )

            elif status == "finished":

                text = (
                    "✅ **Download completed!**\n\n"
                    f"⏱ **Time:** "
                    f"`{format_time(elapsed)}`"
                )

            elif status == "error":

                error = progress_state.get(
                    "error",
                    "Unknown error"
                )

                text = (
                    "❌ **Download failed!**\n\n"
                    f"`{error[:500]}`"
                )

            else:

                text = (
                    "⏳ **Processing...**\n\n"
                    f"⏱ **Time:** "
                    f"`{format_time(elapsed)}`"
                )

            if text != last_text:

                try:

                    await status_message.edit_text(
                        text
                    )

                    last_text = text

                except Exception:
                    pass

            if status in (
                "finished",
                "error"
            ):
                break

            await asyncio.sleep(2)

        except asyncio.CancelledError:
            break

        except Exception as e:

            LOGGER.error(
                "Progress updater error: %s",
                e
            )

            await asyncio.sleep(2)


# ============================================================
# /VIDEO COMMAND
# ============================================================

def register_video_handlers(app):

    @app.on_message(
        filters.command("video")
        & filters.private
    )
    async def video_handler(
        client,
        message: Message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "🎬 **Video Downloader**\n\n"
                "Use:\n"
                "`/video <URL>`\n\n"
                "Example:\n"
                "`/video https://youtu.be/xxxxx`"
            )

            return

        url = message.text.split(
            None,
            1
        )[1].strip()

        if not is_valid_url(url):

            await message.reply_text(
                "❌ **Invalid URL.**"
            )

            return

        status_message = await message.reply_text(
            "⏳ **Preparing download...**"
        )

        progress_state = {
            "status": "extracting",
            "downloaded": 0,
            "total": 0,
            "speed": 0,
            "eta": None,
            "start_time": time.time(),
        }

        progress_task = asyncio.create_task(
            update_progress(
                status_message,
                progress_state
            )
        )

        prefix = (
            f"video_"
            f"{message.chat.id}_"
            f"{message.id}_"
            f"{int(time.time())}"
        )

        file_path = None
        info = None

        try:

            # ====================================================
            # TELEGRAM PUBLIC POST
            # ====================================================

            if TELEGRAM_POST_REGEX.search(url):

                progress_state[
                    "status"
                ] = "downloading"

                file_path = (
                    await send_telegram_public_post(
                        client,
                        message,
                        url
                    )
                )

                if file_path:

                    progress_state[
                        "status"
                    ] = "finished"

                    info = {
                        "title": os.path.basename(
                            file_path
                        )
                    }

            else:

                file_path, info = (
                    await download_media(
                        url,
                        prefix,
                        progress_state,
                        status_message
                    )
                )

            # Stop updater

            if progress_task:

                try:
                    await progress_task
                except Exception:
                    pass

                progress_task = None

            # ====================================================
            # FAILED
            # ====================================================

            if not file_path:

                await status_message.edit_text(
                    "❌ **Download failed.**\n\n"
                    "Unable to download this video."
                )

                return

            if not os.path.exists(
                file_path
            ):

                await status_message.edit_text(
                    "❌ **Downloaded file not found.**"
                )

                return

            # ====================================================
            # FILE INFORMATION
            # ====================================================

            file_size = os.path.getsize(
                file_path
            )

            title = (
                info.get("title")
                if info
                else None
            )

            if not title:

                title = os.path.basename(
                    file_path
                )

            # ====================================================
            # SESSION STORAGE
            # ====================================================

            if not hasattr(
                client,
                "_video_sessions"
            ):

                client._video_sessions = {}

            client._video_sessions[
                status_message.id
            ] = {
                "file_path": file_path,
                "user_id": message.from_user.id,
                "title": title,
                "file_size": file_size,
                "created_at": time.time(),
            }

            # ====================================================
            # OUTPUT BUTTONS
            # ====================================================

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎥 Video",
                            callback_data=(
                                "video_output:"
                                f"{status_message.id}"
                            )
                        ),
                        InlineKeyboardButton(
                            "📁 Document",
                            callback_data=(
                                "document_output:"
                                f"{status_message.id}"
                            )
                        ),
                    ]
                ]
            )

            await status_message.edit_text(
                "✅ **Download completed!**\n\n"
                f"🎬 **Title:** `{title[:100]}`\n"
                f"📦 **Size:** "
                f"`{format_bytes(file_size)}`\n\n"
                "Choose how you want to receive the file:",
                reply_markup=keyboard
            )

        except Exception as e:

            LOGGER.exception(
                "Video handler error"
            )

            if progress_task:

                progress_task.cancel()

                try:
                    await progress_task
                except Exception:
                    pass

            await status_message.edit_text(
                "❌ **Download failed!**\n\n"
                f"`{str(e)[:500]}`"
            )


    # ========================================================
    # SEND AS VIDEO
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^video_output:(\d+)$"
        )
    )
    async def send_video_callback(
        client,
        callback
    ):

        try:

            session_id = int(
                callback.matches[0].group(1)
            )

            sessions = getattr(
                client,
                "_video_sessions",
                {}
            )

            session = sessions.get(
                session_id
            )

            if not session:

                await callback.answer(
                    "❌ Session expired.",
                    show_alert=True
                )

                return

            if (
                callback.from_user.id
                != session["user_id"]
            ):

                await callback.answer(
                    "❌ This file belongs to another user.",
                    show_alert=True
                )

                return

            file_path = session[
                "file_path"
            ]

            if not os.path.exists(
                file_path
            ):

                sessions.pop(
                    session_id,
                    None
                )

                await callback.answer(
                    "❌ File no longer exists.",
                    show_alert=True
                )

                return

            await callback.answer(
                "🎥 Sending video..."
            )

            await callback.message.edit_text(
                "📤 **Sending as Video...**"
            )

            await client.send_video(
                chat_id=callback.from_user.id,
                video=file_path,
                caption=(
                    f"🎬 **{session['title']}**"
                ),
                supports_streaming=True
            )

            # ==================================================
            # CLEANUP
            # ==================================================

            try:
                os.remove(file_path)
            except Exception:
                pass

            sessions.pop(
                session_id,
                None
            )

            try:
                await callback.message.delete()
            except Exception:
                pass

        except Exception as e:

            LOGGER.exception(
                "Send video error"
            )

            await callback.answer(
                "❌ Failed to send video.",
                show_alert=True
            )


    # ========================================================
    # SEND AS DOCUMENT
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^document_output:(\d+)$"
        )
    )
    async def send_document_callback(
        client,
        callback
    ):

        try:

            session_id = int(
                callback.matches[0].group(1)
            )

            sessions = getattr(
                client,
                "_video_sessions",
                {}
            )

            session = sessions.get(
                session_id
            )

            if not session:

                await callback.answer(
                    "❌ Session expired.",
                    show_alert=True
                )

                return

            if (
                callback.from_user.id
                != session["user_id"]
            ):

                await callback.answer(
                    "❌ This file belongs to another user.",
                    show_alert=True
                )

                return

            file_path = session[
                "file_path"
            ]

            if not os.path.exists(
                file_path
            ):

                sessions.pop(
                    session_id,
                    None
                )

                await callback.answer(
                    "❌ File no longer exists.",
                    show_alert=True
                )

                return

            await callback.answer(
                "📁 Sending document..."
            )

            await callback.message.edit_text(
                "📤 **Sending as Document...**"
            )

            await client.send_document(
                chat_id=callback.from_user.id,
                document=file_path,
                caption=(
                    f"🎬 **{session['title']}**"
                )
            )

            # ==================================================
            # CLEANUP
            # ==================================================

            try:
                os.remove(file_path)
            except Exception:
                pass

            sessions.pop(
                session_id,
                None
            )

            try:
                await callback.message.delete()
            except Exception:
                pass

        except Exception as e:

            LOGGER.exception(
                "Send document error"
            )

            await callback.answer(
                "❌ Failed to send document.",
                show_alert=True
        )
