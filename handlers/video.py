

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

from bot import app


# ============================================================
# CONFIG
# ============================================================

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)


# ============================================================
# HELPERS
# ============================================================

def format_bytes(size):
    if size is None or size < 0:
        return "Unknown"

    size = float(size)

    if size < 1024:
        return f"{int(size)} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"

    return f"{size / (1024 ** 3):.2f} GB"


def format_speed(speed):
    if not speed or speed <= 0:
        return "0 B/s"

    return f"{format_bytes(speed)}/s"


def format_time(seconds):
    if seconds is None:
        return "Unknown"

    try:
        seconds = int(seconds)
    except Exception:
        return "Unknown"

    if seconds < 0:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def is_valid_url(url):
    try:
        parsed = urlparse(url)

        return parsed.scheme in (
            "http",
            "https",
        ) and bool(parsed.netloc)

    except Exception:
        return False


def find_downloaded_file(prefix):
    patterns = [
        f"{prefix}.*",
        f"{prefix}.*.*",
    ]

    files = []

    for pattern in patterns:
        files.extend(
            glob.glob(
                os.path.join(
                    DOWNLOAD_DIR,
                    pattern,
                )
            )
        )

    files = [
        x for x in files
        if os.path.isfile(x)
    ]

    if not files:
        return None

    files.sort(
        key=lambda x: os.path.getmtime(x),
        reverse=True,
    )

    return files[0]


def cleanup_file(file_path):
    if not file_path:
        return

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logging.warning(
            "Cleanup error: %s",
            e,
        )


# ============================================================
# TELEGRAM PUBLIC POST
# ============================================================

TELEGRAM_PUBLIC_POST_REGEX = re.compile(
    r"^(?:https?://)?t\.me/"
    r"([A-Za-z0-9_]+)/"
    r"(\d+)"
    r"(?:\?.*)?$"
)


async def send_telegram_public_post(
    client,
    message,
    url,
):
    match = TELEGRAM_PUBLIC_POST_REGEX.match(
        url.strip()
    )

    if not match:
        return False

    username = match.group(1)
    message_id = int(match.group(2))

    try:
        source_message = await client.get_messages(
            username,
            message_id,
        )

        if not source_message:
            await message.edit(
                "❌ Telegram post not found."
            )
            return True

        if source_message.video:
            await source_message.copy(
                message.chat.id
            )

        elif source_message.document:
            await source_message.copy(
                message.chat.id
            )

        elif source_message.audio:
            await source_message.copy(
                message.chat.id
            )

        elif source_message.photo:
            await source_message.copy(
                message.chat.id
            )

        elif source_message.animation:
            await source_message.copy(
                message.chat.id
            )

        else:
            await message.edit(
                "❌ This Telegram post does not contain downloadable media."
            )

        return True

    except Exception as e:
        logging.exception(
            "Telegram public post error: %s",
            e,
        )

        await message.edit(
            "❌ Failed to access the Telegram post."
        )

        return True


# ============================================================
# DOWNLOAD
# ============================================================

async def download_media(
    url,
    prefix,
    progress_state,
):
    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{prefix}.%(ext)s",
    )

    loop = asyncio.get_running_loop()

    def progress_hook(data):

        status = data.get("status")

        if status == "downloading":

            progress_state["phase"] = "downloading"

            downloaded = (
                data.get("downloaded_bytes")
                or 0
            )

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            speed = data.get(
                "speed"
            )

            eta = data.get(
                "eta"
            )

            filename = data.get(
                "filename"
            )

            progress_state["downloaded"] = downloaded
            progress_state["total"] = total
            progress_state["speed"] = speed
            progress_state["eta"] = eta
            progress_state["filename"] = filename

        elif status == "finished":

            progress_state["phase"] = "extracting"

            downloaded = (
                data.get("downloaded_bytes")
                or 0
            )

            total = (
                data.get("total_bytes")
                or downloaded
            )

            progress_state["downloaded"] = downloaded
            progress_state["total"] = total
            progress_state["speed"] = 0
            progress_state["eta"] = 0

    def postprocessor_hook(data):

        status = data.get("status")

        if status in (
            "started",
            "processing",
        ):
            progress_state["phase"] = "extracting"

        elif status == "finished":
            progress_state["phase"] = "finalizing"

    ydl_options = {
        # ----------------------------------------------------
        # VIDEO / AUDIO FORMAT
        # ----------------------------------------------------

        "format": (
            "bestvideo[height<=1080]+bestaudio/"
            "best[height<=1080]/"
            "bestvideo+bestaudio/"
            "best"
        ),

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "noplaylist": True,

        # ----------------------------------------------------
        # FILENAMES
        # ----------------------------------------------------

        "restrictfilenames": True,

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        "socket_timeout": 60,

        "retries": 10,

        "fragment_retries": 10,

        "file_access_retries": 5,

        "extractor_retries": 5,

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        "concurrent_fragment_downloads": 4,

        "skip_unavailable_fragments": True,

        "extract_flat": False,

        # ----------------------------------------------------
        # YT-DLP
        # ----------------------------------------------------

        "quiet": False,

        "no_warnings": False,

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        "progress_hooks": [
            progress_hook
        ],

        "postprocessor_hooks": [
            postprocessor_hook
        ],

        # ----------------------------------------------------
        # FFMPEG
        # ----------------------------------------------------

        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],

        # ----------------------------------------------------
        # YOUTUBE
        # ----------------------------------------------------

        "hls_prefer_native": True,

        "live_from_start": True,

        "wait_for_video": (
            5,
            30,
        ),

        # ----------------------------------------------------
        # SAFE
        # ----------------------------------------------------

        "overwrites": True,
    }

    def run_download():

        with yt_dlp.YoutubeDL(
            ydl_options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

            if not info:
                raise Exception(
                    "Unable to extract media information."
                )

            title = (
                info.get("title")
                or "Downloaded Media"
            )

            duration = (
                info.get("duration")
                or 0
            )

            filesize = (
                info.get("filesize")
                or info.get("filesize_approx")
                or 0
            )

            progress_state["title"] = title
            progress_state["duration"] = duration
            progress_state["total"] = filesize

            ydl.download(
                [url]
            )

            file_path = find_downloaded_file(
                prefix
            )

            if not file_path:
                raise Exception(
                    "Downloaded file was not found."
                )

            return {
                "file_path": file_path,
                "title": title,
                "filesize": os.path.getsize(
                    file_path
                ),
            }

    return await loop.run_in_executor(
        None,
        run_download,
    )


# ============================================================
# DOWNLOAD STATUS
# ============================================================

async def update_download_status(
    message,
    progress_state,
    start_time,
):
    last_text = ""

    while True:

        try:
            phase = progress_state.get(
                "phase",
                "starting",
            )

            downloaded = progress_state.get(
                "downloaded",
                0,
            )

            total = progress_state.get(
                "total",
            )

            speed = progress_state.get(
                "speed",
                0,
            )

            eta = progress_state.get(
                "eta",
            )

            elapsed = time.time() - start_time

            elapsed_text = format_time(
                elapsed
            )

            downloaded_text = format_bytes(
                downloaded
            )

            total_text = format_bytes(
                total
            )

            speed_text = format_speed(
                speed
            )

            eta_text = format_time(
                eta
            )

            if phase == "starting":

                text = (
                    "⏳ **Starting Download...**\n\n"
                    f"📦 Downloaded: `{downloaded_text}`\n"
                    f"📦 Size: `{total_text}`\n"
                    f"🚀 Speed: `{speed_text}`\n"
                    f"⏱ Time: `{elapsed_text}`\n"
                    f"⌛ ETA: `{eta_text}`"
                )

            elif phase == "extracting":

                text = (
                    "⚙️ **Extracting...**\n\n"
                    f"📦 Downloaded: `{downloaded_text}`\n"
                    f"📦 Size: `{total_text}`\n"
                    f"🚀 Speed: `{speed_text}`\n"
                    f"⏱ Time: `{elapsed_text}`\n"
                    f"⌛ ETA: `Processing...`"
                )

            elif phase == "finalizing":

                text = (
                    "🔄 **Finalizing...**\n\n"
                    f"📦 Downloaded: `{downloaded_text}`\n"
                    f"📦 Size: `{total_text}`\n"
                    f"🚀 Speed: `{speed_text}`\n"
                    f"⏱ Time: `{elapsed_text}`\n"
                    f"⌛ ETA: `Processing...`"
                )

            else:

                if total and total > 0:

                    percentage = (
                        downloaded / total
                    ) * 100

                    if percentage > 100:
                        percentage = 100

                    progress_bar_length = 10

                    filled = int(
                        percentage
                        / 100
                        * progress_bar_length
                    )

                    bar = (
                        "█" * filled
                        + "░"
                        * (
                            progress_bar_length
                            - filled
                        )
                    )

                    progress_line = (
                        f"📊 Progress: "
                        f"`{bar}` "
                        f"`{percentage:.1f}%`"
                    )

                else:

                    progress_line = (
                        "📊 Progress: `Unknown`"
                    )

                text = (
                    "⬇️ **Downloading...**\n\n"
                    f"{progress_line}\n"
                    f"📦 Downloaded: `{downloaded_text}`\n"
                    f"📦 Size: `{total_text}`\n"
                    f"🚀 Speed: `{speed_text}`\n"
                    f"⏱ Time: `{elapsed_text}`\n"
                    f"⌛ ETA: `{eta_text}`"
                )

            if text != last_text:

                try:
                    await message.edit_text(
                        text
                    )
                    last_text = text

                except Exception:
                    pass

            await asyncio.sleep(2)

        except asyncio.CancelledError:
            break

        except Exception as e:

            logging.warning(
                "Status updater error: %s",
                e,
            )

            await asyncio.sleep(2)


# ============================================================
# /DL COMMAND
# ============================================================

@app.on_message(
    filters.command("dl")
    & filters.private
)
async def download_command(
    client,
    message: Message,
):

    if len(message.command) < 2:

        await message.reply_text(
            "❌ **Please provide a URL.**\n\n"
            "Example:\n"
            "`/dl https://example.com/video`"
        )

        return

    url = message.text.split(
        None,
        1
    )[1].strip()

    if not is_valid_url(url):

        await message.reply_text(
            "❌ **Invalid URL.**\n\n"
            "Please send a valid `http://` or `https://` link."
        )

        return

    # --------------------------------------------------------
    # TELEGRAM PUBLIC POSTS
    # --------------------------------------------------------

    telegram_handled = (
        await send_telegram_public_post(
            client,
            message,
            url,
        )
    )

    if telegram_handled:
        return

    # --------------------------------------------------------
    # STATUS MESSAGE
    # --------------------------------------------------------

    status_message = await message.reply_text(
        "⏳ **Starting Download...**"
    )

    prefix = (
        f"dl_{message.from_user.id}_"
        f"{status_message.id}_"
        f"{int(time.time())}"
    )

    progress_state = {
        "phase": "starting",
        "downloaded": 0,
        "total": None,
        "speed": 0,
        "eta": None,
        "filename": None,
        "title": "Downloaded Media",
    }

    start_time = time.time()

    status_task = asyncio.create_task(
        update_download_status(
            status_message,
            progress_state,
            start_time,
        )
    )

    try:

        result = await download_media(
            url,
            prefix,
            progress_state,
        )

    except Exception as e:

        logging.exception(
            "Download error: %s",
            e,
        )

        status_task.cancel()

        try:
            await status_task
        except asyncio.CancelledError:
            pass

        await status_message.edit_text(
            "❌ **Download Failed**\n\n"
            f"**Error:** `{str(e)[:1500]}`"
        )

        return

    finally:

        if not status_task.done():

            status_task.cancel()

            try:
                await status_task
            except asyncio.CancelledError:
                pass

    file_path = result.get(
        "file_path"
    )

    title = result.get(
        "title"
    ) or "Downloaded Media"

    filesize = result.get(
        "filesize"
    ) or 0

    if not file_path or not os.path.exists(
        file_path
    ):

        await status_message.edit_text(
            "❌ **Downloaded file not found.**"
        )

        return

    # --------------------------------------------------------
    # SAVE SESSION
    # --------------------------------------------------------

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
        "file_size": filesize,
        "created_at": time.time(),
    }

    # --------------------------------------------------------
    # OUTPUT BUTTONS
    # --------------------------------------------------------

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎥 Video",
                    callback_data=(
                        f"video_output:"
                        f"{status_message.id}"
                    ),
                ),
                InlineKeyboardButton(
                    "📁 Document",
                    callback_data=(
                        f"document_output:"
                        f"{status_message.id}"
                    ),
                ),
            ]
        ]
    )

    elapsed = format_time(
        time.time() - start_time
    )

    await status_message.edit_text(
        "✅ **Download Completed!**\n\n"
        f"🎬 **Title:** `{title[:200]}`\n"
        f"📦 **Size:** `{format_bytes(filesize)}`\n"
        f"⏱ **Time:** `{elapsed}`\n\n"
        "Choose how you want to receive the file:",
        reply_markup=keyboard,
    )


# ============================================================
# VIDEO BUTTON
# ============================================================

@app.on_callback_query(
    filters.regex(
        r"^video_output:(\d+)$"
    )
)
async def video_output_callback(
    client,
    callback_query,
):

    try:

        message_id = int(
            callback_query.data.split(
                ":"
            )[1]
        )

    except Exception:

        await callback_query.answer(
            "❌ Invalid request.",
            show_alert=True,
        )

        return

    sessions = getattr(
        client,
        "_video_sessions",
        {},
    )

    session = sessions.get(
        message_id
    )

    if not session:

        await callback_query.answer(
            "❌ Download session expired.",
            show_alert=True,
        )

        return

    if (
        callback_query.from_user.id
        != session["user_id"]
    ):

        await callback_query.answer(
            "❌ This file is not for you.",
            show_alert=True,
        )

        return

    file_path = session.get(
        "file_path"
    )

    if not file_path or not os.path.exists(
        file_path
    ):

        sessions.pop(
            message_id,
            None,
        )

        await callback_query.answer(
            "❌ File no longer exists.",
            show_alert=True,
        )

        return

    await callback_query.answer(
        "📤 Sending video..."
    )

    try:

        await client.send_video(
            chat_id=callback_query.from_user.id,
            video=file_path,
            caption=(
                f"🎬 **{session['title'][:200]}**"
            ),
            supports_streaming=True,
        )

        cleanup_file(
            file_path
        )

        sessions.pop(
            message_id,
            None,
        )

        try:
            await callback_query.message.delete()
        except Exception:
            pass

    except Exception as e:

        logging.exception(
            "Video send error: %s",
            e,
        )

        await callback_query.message.edit_text(
            "❌ **Failed to send video.**\n\n"
            f"Error: `{str(e)[:1000]}`"
        )


# ============================================================
# DOCUMENT BUTTON
# ============================================================

@app.on_callback_query(
    filters.regex(
        r"^document_output:(\d+)$"
    )
)
async def document_output_callback(
    client,
    callback_query,
):

    try:

        message_id = int(
            callback_query.data.split(
                ":"
            )[1]
        )

    except Exception:

        await callback_query.answer(
            "❌ Invalid request.",
            show_alert=True,
        )

        return

    sessions = getattr(
        client,
        "_video_sessions",
        {},
    )

    session = sessions.get(
        message_id
    )

    if not session:

        await callback_query.answer(
            "❌ Download session expired.",
            show_alert=True,
        )

        return

    if (
        callback_query.from_user.id
        != session["user_id"]
    ):

        await callback_query.answer(
            "❌ This file is not for you.",
            show_alert=True,
        )

        return

    file_path = session.get(
        "file_path"
    )

    if not file_path or not os.path.exists(
        file_path
    ):

        sessions.pop(
            message_id,
            None,
        )

        await callback_query.answer(
            "❌ File no longer exists.",
            show_alert=True,
        )

        return

    await callback_query.answer(
        "📤 Sending document..."
    )

    try:

        await client.send_document(
            chat_id=callback_query.from_user.id,
            document=file_path,
            caption=(
                f"📁 **{session['title'][:200]}**"
            ),
        )

        cleanup_file(
            file_path
        )

        sessions.pop(
            message_id,
            None,
        )

        try:
            await callback_query.message.delete()
        except Exception:
            pass

    except Exception as e:

        logging.exception(
            "Document send error: %s",
            e,
        )

        await callback_query.message.edit_text(
            "❌ **Failed to send document.**\n\n"
            f"Error: `{str(e)[:1000]}`"
        )
