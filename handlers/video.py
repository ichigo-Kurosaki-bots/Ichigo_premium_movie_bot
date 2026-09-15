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
import time
from urllib.parse import urlparse

# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity
# Support : @Coders_Grp
# ------------------------ #

import yt_dlp
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

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
# HELPERS
# ============================================================

def format_bytes(size):

    if size is None:
        return "Unknown"

    try:
        size = float(size)
    except Exception:
        return "Unknown"

    if size < 1024:
        return f"{size:.0f} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.1f} MB"

    return f"{size / (1024 ** 3):.2f} GB"


def format_speed(speed):

    if not speed:
        return "0 B/s"

    return f"{format_bytes(speed)}/s"


def format_time(seconds):

    if seconds is None:
        return "00:00"

    try:
        seconds = int(seconds)
    except Exception:
        return "00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


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
# Updates : @Aero_Unity
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

    match = TELEGRAM_PUBLIC_RE.match(
        url.strip()
    )

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
# Support : @Coders_Grp
# ------------------------ #


# ============================================================
# DOWNLOAD USING YT-DLP
# ============================================================

async def download_media(
    url: str,
    prefix: str,
    progress_state: dict,
    status_message: Message
):

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"{prefix}.%(ext)s"
    )

    # --------------------------------------------------------
    # Detect YouTube
    # --------------------------------------------------------

    parsed = urlparse(url)

    hostname = parsed.netloc.lower().split(":")[0]

    is_youtube = (
        hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
        or hostname == "youtu.be"
        or hostname.endswith(".youtu.be")
    )

    # --------------------------------------------------------
    # YT-DLP OPTIONS
    # --------------------------------------------------------

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

        "cookiefile": None,

    }

    # --------------------------------------------------------
    # YouTube options
    # --------------------------------------------------------

    if is_youtube:

        ydl_opts.update({

            "live_from_start": True,

            "wait_for_video": (5, 30),

            "hls_prefer_native": True,

            "extractor_args": {

                "youtube": {

                    "player_client": [
                        "android",
                        "web"
                    ]

                }

            },

        })

    # --------------------------------------------------------
    # Progress Hook
    # --------------------------------------------------------

    def progress_hook(data):

        try:

            progress_state["status"] = data.get(
                "status",
                "downloading"
            )

            if data.get("filename"):
                progress_state["filename"] = data.get(
                    "filename"
                )

            if data.get("total_bytes"):

                progress_state["total"] = data.get(
                    "total_bytes"
                )

            elif data.get("total_bytes_estimate"):

                progress_state["total"] = data.get(
                    "total_bytes_estimate"
                )

            if data.get("downloaded_bytes") is not None:

                progress_state["downloaded"] = data.get(
                    "downloaded_bytes",
                    0
                )

            if data.get("speed") is not None:

                progress_state["speed"] = data.get(
                    "speed",
                    0
                )

            if data.get("eta") is not None:

                progress_state["eta"] = data.get(
                    "eta"
                )

            if data.get("status") == "finished":

                progress_state["status"] = "finished"

        except Exception as e:

            logger.warning(
                f"Progress hook error: {e}"
            )

    # --------------------------------------------------------
    # Postprocessor Hook
    # --------------------------------------------------------

    def postprocessor_hook(data):

        try:

            progress_state["status"] = "extracting"

            progress_state["postprocessor"] = (
                data.get(
                    "postprocessor",
                    "Extracting"
                )
            )

        except Exception as e:

            logger.warning(
                f"Postprocessor hook error: {e}"
            )

    ydl_opts["progress_hooks"] = [
        progress_hook
    ]

    ydl_opts["postprocessor_hooks"] = [
        postprocessor_hook
    ]

    loop = asyncio.get_running_loop()

    # --------------------------------------------------------
    # Run YT-DLP
    # --------------------------------------------------------

    def run_download():

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

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

        progress_state["status"] = "finished"

        file_path = find_downloaded_file(
            prefix
        )

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
# PROGRESS MESSAGE UPDATER
# ============================================================

async def update_download_progress(
    status_message: Message,
    progress_state: dict
):

    last_text = ""

    while not progress_state.get(
        "finished",
        False
    ):

        try:

            state = progress_state.get(
                "status",
                "downloading"
            )

            elapsed = time.monotonic() - progress_state.get(
                "start_time",
                time.monotonic()
            )

            downloaded = progress_state.get(
                "downloaded",
                0
            )

            total = progress_state.get(
                "total"
            )

            speed = progress_state.get(
                "speed",
                0
            )

            # ------------------------------------------------
            # EXTRACTING
            # ------------------------------------------------

            if state == "extracting":

                text = (
                    "🔍 <b>Extracting...</b>\n\n"
                    f"⏱ <b>Time:</b> "
                    f"{format_time(elapsed)}\n"
                    f"📦 <b>Downloaded:</b> "
                    f"{format_bytes(downloaded)}\n"
                    f"📦 <b>Size:</b> "
                    f"{format_bytes(total)}"
                )

            else:

                # --------------------------------------------
                # PERCENTAGE
                # --------------------------------------------

                if total and total > 0:

                    percentage = (
                        downloaded / total
                    ) * 100

                    percentage = min(
                        100,
                        max(0, percentage)
                    )

                    progress = (
                        f"{percentage:.1f}%"
                    )

                else:

                    progress = "Unknown"

                # --------------------------------------------
                # ETA
                # --------------------------------------------

                eta = progress_state.get(
                    "eta"
                )

                eta_text = (
                    format_time(eta)
                    if eta is not None
                    else "Unknown"
                )

                text = (
                    "⏳ <b>Downloading...</b>\n\n"
                    f"📊 <b>Progress:</b> "
                    f"{progress}\n"
                    f"📦 <b>Downloaded:</b> "
                    f"{format_bytes(downloaded)}\n"
                    f"📦 <b>Size:</b> "
                    f"{format_bytes(total)}\n"
                    f"🚀 <b>Speed:</b> "
                    f"{format_speed(speed)}\n"
                    f"⏱ <b>Time:</b> "
                    f"{format_time(elapsed)}\n"
                    f"⌛ <b>ETA:</b> "
                    f"{eta_text}"
                )

            # ------------------------------------------------
            # Don't edit unnecessarily
            # ------------------------------------------------

            if text != last_text:

                try:

                    await status_message.edit_text(
                        text
                    )

                    last_text = text

                except Exception:

                    pass

        except Exception as e:

            logger.warning(
                f"Progress update error: {e}"
            )

        await asyncio.sleep(2)


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

        if file_path and os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

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

        # ----------------------------------------------------
        # Video
        # ----------------------------------------------------

        if source_message.video:

            await message.reply_video(
                source_message.video.file_id
            )

            return True

        # ----------------------------------------------------
        # Document
        # ----------------------------------------------------

        if source_message.document:

            await message.reply_document(
                source_message.document.file_id
            )

            return True

        # ----------------------------------------------------
        # Animation
        # ----------------------------------------------------

        if source_message.animation:

            await message.reply_animation(
                source_message.animation.file_id
            )

            return True

        # ----------------------------------------------------
        # Photo
        # ----------------------------------------------------

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

    # ========================================================
    # /VIDEO COMMAND
    # ========================================================

    @app.on_message(
        filters.command("video")
        & filters.text
    )
    async def video_handler(
        client,
        message: Message
    ):

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
        # DOWNLOAD STATUS
        # ----------------------------------------------------

        status = await message.reply_text(
            "⏳ <b>Downloading...</b>\n\n"
            "📊 <b>Progress:</b> 0%\n"
            "📦 <b>Downloaded:</b> 0 B\n"
            "📦 <b>Size:</b> Unknown\n"
            "🚀 <b>Speed:</b> 0 B/s\n"
            "⏱ <b>Time:</b> 00:00\n"
            "⌛ <b>ETA:</b> Unknown"
        )

        # ----------------------------------------------------
        # UNIQUE PREFIX
        # ----------------------------------------------------

        prefix = (
            f"{message.chat.id}_"
            f"{message.id}"
        )

        # ----------------------------------------------------
        # PROGRESS STATE
        # ----------------------------------------------------

        progress_state = {

            "status": "downloading",

            "downloaded": 0,

            "total": None,

            "speed": 0,

            "eta": None,

            "start_time": time.monotonic(),

            "finished": False,

        }

        file_path = None

        progress_task = None

        try:

            # ------------------------------------------------
            # START PROGRESS UPDATER
            # ------------------------------------------------

            progress_task = asyncio.create_task(
                update_download_progress(
                    status,
                    progress_state
                )
            )

            # ------------------------------------------------
            # DOWNLOAD
            # ------------------------------------------------

            file_path, info = await download_media(
                url,
                prefix,
                progress_state,
                status
            )

            # ------------------------------------------------
            # STOP PROGRESS
            # ------------------------------------------------

            progress_state["finished"] = True

            if progress_task:

                try:

                    await progress_task

                except Exception:

                    pass

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
            # FILE SIZE
            # ------------------------------------------------

            file_size = os.path.getsize(
                file_path
            )

            # ------------------------------------------------
            # EXTRACTION COMPLETE
            # ------------------------------------------------

            try:

                await status.edit_text(
                    "🔍 <b>Extracting...</b>\n\n"
                    f"📦 <b>Size:</b> "
                    f"{format_bytes(file_size)}"
                )

                await asyncio.sleep(1)

            except Exception:

                pass

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            title = None

            if info:

                title = info.get(
                    "title"
                )

            if not title:

                title = "Downloaded Media"

            # ------------------------------------------------
            # STORE SESSION
            # ------------------------------------------------

            if not hasattr(
                client,
                "_video_sessions"
            ):

                client._video_sessions = {}

            client._video_sessions[
                status.id
            ] = {

                "file_path": file_path,

                "user_id": message.from_user.id
                if message.from_user
                else message.chat.id,

                "title": title,

                "file_size": file_size,

            }

            # ------------------------------------------------
            # OUTPUT BUTTONS
            # ------------------------------------------------

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🎥 Video",
                            callback_data=(
                                f"video_output:{status.id}"
                            )
                        ),
                        InlineKeyboardButton(
                            "📁 Document",
                            callback_data=(
                                f"document_output:{status.id}"
                            )
                        )
                    ]
                ]
            )

            # ------------------------------------------------
            # READY
            # ------------------------------------------------

            await status.edit_text(
                "✅ <b>Download Completed</b>\n\n"
                f"🎬 <b>{title}</b>\n"
                f"📦 <b>Size:</b> "
                f"{format_bytes(file_size)}\n"
                f"⏱ <b>Time:</b> "
                f"{format_time(time.monotonic() - progress_state['start_time'])}\n\n"
                "📤 <b>Select how you want to receive the file:</b>",
                reply_markup=keyboard
            )

        except Exception as e:

            logger.exception(
                f"Video handler error: {e}"
            )

            progress_state["finished"] = True

            if progress_task:

                try:

                    progress_task.cancel()

                except Exception:

                    pass

            try:

                await status.edit_text(
                    "❌ <b>This video cannot be downloaded.</b>\n\n"
                    "The media may be unavailable, "
                    "login-required, DRM-protected, "
                    "or unsupported."
                )

            except Exception:

                pass

            if file_path:

                cleanup_file(
                    file_path
                )

        finally:

            progress_state["finished"] = True

            # Do NOT delete file here.
            #
            # The file must remain available until
            # the user chooses Video or Document.
            #
            # Callback handler below will delete it
            # after successful sending.


    # ========================================================
    # VIDEO OUTPUT BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^video_output:(\d+)$"
        )
    )
    async def video_output_callback(
        client,
        callback_query
    ):

        try:

            status = callback_query.message

            status_id = int(
                callback_query.data.split(
                    ":"
                )[1]
            )

            sessions = getattr(
                client,
                "_video_sessions",
                {}
            )

            session = sessions.get(
                status_id
            )

            if not session:

                await callback_query.answer(
                    "❌ File session expired.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # USER CHECK
            # ------------------------------------------------

            user_id = session.get(
                "user_id"
            )

            if (
                callback_query.from_user.id
                != user_id
            ):

                await callback_query.answer(
                    "❌ This file belongs to another user.",
                    show_alert=True
                )

                return

            file_path = session.get(
                "file_path"
            )

            title = session.get(
                "title",
                "Downloaded Video"
            )

            if not file_path or not os.path.exists(
                file_path
            ):

                sessions.pop(
                    status_id,
                    None
                )

                await callback_query.answer(
                    "❌ File no longer exists.",
                    show_alert=True
                )

                try:

                    await status.edit_text(
                        "❌ <b>File no longer exists.</b>\n\n"
                        "Please use <code>/video</code> again."
                    )

                except Exception:

                    pass

                return

            await callback_query.answer(
                "🎥 Sending video..."
            )

            await status.edit_text(
                " <b>Uploading as Video...</b>\n\n"
                f"<b>›› Size:</b> "
                f"{format_bytes(os.path.getsize(file_path))}"
            )

            # ------------------------------------------------
            # SEND VIDEO
            # ------------------------------------------------

            await client.send_video(
                chat_id=callback_query.message.chat.id,
                video=file_path,
                caption=f"🎬 <b>{title}</b>",
                supports_streaming=True
            )

            # ------------------------------------------------
            # CLEANUP
            # ------------------------------------------------

            cleanup_file(
                file_path
            )

            sessions.pop(
                status_id,
                None
            )

            try:

                await status.edit_text(
                    "✅ <b>Video sent successfully.</b>"
                )

            except Exception:

                pass

        except Exception as e:

            logger.exception(
                f"Video output callback error: {e}"
            )

            await callback_query.answer(
                "❌ Failed to send video.",
                show_alert=True
            )

            try:

                await callback_query.message.edit_text(
                    "❌ <b>Failed to send video.</b>\n\n"
                    "The downloaded file may use an "
                    "unsupported video format or codec."
                )

            except Exception:

                pass


    # ========================================================
    # DOCUMENT OUTPUT BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^document_output:(\d+)$"
        )
    )
    async def document_output_callback(
        client,
        callback_query
    ):

        try:

            status = callback_query.message

            status_id = int(
                callback_query.data.split(
                    ":"
                )[1]
            )

            sessions = getattr(
                client,
                "_video_sessions",
                {}
            )

            session = sessions.get(
                status_id
            )

            if not session:

                await callback_query.answer(
                    "❌ File session expired.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # USER CHECK
            # ------------------------------------------------

            user_id = session.get(
                "user_id"
            )

            if (
                callback_query.from_user.id
                != user_id
            ):

                await callback_query.answer(
                    "❌ This file belongs to another user.",
                    show_alert=True
                )

                return

            file_path = session.get(
                "file_path"
            )

            title = session.get(
                "title",
                "Downloaded Media"
            )

            if not file_path or not os.path.exists(
                file_path
            ):

                sessions.pop(
                    status_id,
                    None
                )

                await callback_query.answer(
                    "❌ File no longer exists.",
                    show_alert=True
                )

                try:

                    await status.edit_text(
                        "❌ <b>File no longer exists.</b>\n\n"
                        "Please use <code>/video</code> again."
                    )

                except Exception:

                    pass

                return

            await callback_query.answer(
                "📁 Sending document..."
            )

            await status.edit_text(
                " <b>Uploading as Document...</b>\n\n"
                f"<b>›› Size:</b> "
                f"{format_bytes(os.path.getsize(file_path))}"
            )

            # ------------------------------------------------
            # SEND DOCUMENT
            # ------------------------------------------------

            await client.send_document(
                chat_id=callback_query.message.chat.id,
                document=file_path,
                caption=f"🎬 <b>{title}</b>"
            )

            # ------------------------------------------------
            # CLEANUP
            # ------------------------------------------------

            cleanup_file(
                file_path
            )

            sessions.pop(
                status_id,
                None
            )

            try:

                await status.edit_text(
                    "✅ <b>Document sent successfully.</b>"
                )

            except Exception:

                pass

        except Exception as e:

            logger.exception(
                f"Document output callback error: {e}"
            )

            await callback_query.answer(
                "❌ Failed to send document.",
                show_alert=True
            )

            try:

                await callback_query.message.edit_text(
                    "❌ <b>Failed to send document.</b>"
                )

            except Exception:

                pass


# ------------------------ #
# Don't Remove My Credits
# Owner: @Mr_Mohammed_29
# Updates: @Aero_Unity
# Support : @Coders_Grp
# ------------------------ #
