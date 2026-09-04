from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

import html


# ============================================================
# FONT TABLES
# ============================================================

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ============================================================
# ORIGINAL TEXT CACHE
# ============================================================

# Stores the original text for each generated font message.
# This prevents fonts from stacking when another font is clicked.
FONT_TEXT_CACHE = {}


# ============================================================
# UNICODE FONT CONVERTER
# ============================================================

FONT_MAPS = {

    "bold": (
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇",
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    ),

    "italic": (
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻",
        "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    ),

    "bold_italic": (
        "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯",
        "𝘼𝘽𝘾𝘿𝘌𝙵𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕"
    ),

    "mono": (
        "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣",
        "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉"
    ),

    "double": (
        "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫",
        "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ"
    ),

    "gothic": (
        "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷",
        "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ"
    ),

    "bold_gothic": (
        "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟",
        "𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"
    ),

    "sans": (
        "𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓",
        "𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹"
    ),

    "sans_bold": (
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇",
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    ),

    "sans_italic": (
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻",
        "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    )
}


def unicode_font(text, font):

    if font not in FONT_MAPS:
        return text

    lower, upper = FONT_MAPS[font]

    table = str.maketrans(
        LOWER + UPPER,
        lower + upper
    )

    return text.translate(table)


# ============================================================
# SPECIAL FONT FUNCTIONS
# ============================================================

def small_caps(text):

    table = str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    )

    return text.translate(table)


def bubble(text):

    table = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ"
        "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
    )

    return text.translate(table)


def square(text):

    table = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
        "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉"
    )

    return text.translate(table)


def spacing(text):

    return " ".join(text.upper())


def strike(text):

    return "".join(
        char + "\u0336"
        if char != " "
        else char
        for char in text
    )


def underline(text):

    return "".join(
        char + "\u0332"
        if char != " "
        else char
        for char in text
    )


def slash(text):

    return "".join(
        char + "\u0338"
        if char != " "
        else char
        for char in text
    )


def ray(text):

    return "".join(
        char + "\u0336"
        if char != " "
        else char
        for char in text
    )


def arrows(text):

    return "".join(
        char + "↑"
        if char != " "
        else char
        for char in text
    )


def reverse(text):

    return text[::-1]


def clouds(text):

    return "☁ " + text + " ☁"


def happy(text):

    return "☺ " + text + " ☺"


def sad(text):

    return "☹ " + text + " ☹"


# ============================================================
# ALL FONTS
# ============================================================

FONTS = [

    # --------------------------------------------------------
    # PAGE 1
    # --------------------------------------------------------

    ("Typewriter", "mono"),
    ("Outline", "double"),
    ("Serif", "italic"),

    ("Serif", "bold_italic"),
    ("Serif", "double"),
    ("Sᴍᴀʟʟ Cᴀᴘs", "smallcaps"),

    ("sᴄʀɪᴘᴛ", "italic"),
    ("sᴄʀɪᴘᴛ", "bold_italic"),
    ("tiny", "smallcaps"),

    ("Cᴏᴍɪᴄ", "bold"),
    ("Sans", "sans_bold"),
    ("Sans", "sans_italic"),

    ("Sans", "sans"),
    ("Sans", "bold"),
    ("ⒸⒾⓇⒸⓁⒺⓈ", "bubble"),

    ("CIRCLES", "bubble"),
    ("Gothic", "gothic"),
    ("Gothic", "bold_gothic"),

    ("Clouds", "clouds"),
    ("Häppy", "happy"),
    ("Säd", "sad"),


    # --------------------------------------------------------
    # PAGE 2
    # --------------------------------------------------------

    ("S P E C I", "spacing"),
    ("🅂🅀🅄🄰🅁🄴🅂", "square"),
    ("🆂🆀🆄🅰🆁🅴🆂", "bold"),

    ("ᖴᗩᑎᑕY", "bold"),
    ("ＭＡＴＨ", "double"),
    ("S̴t̴i̴n̴k̴y̴", "strike"),

    ("Bubbles", "bubble"),
    ("Underline", "underline"),
    ("Reverse", "reverse"),

    ("R̷a̷y̷s̷", "ray"),
    ("G̶l̶i̶t̶c̶h̶", "strike"),
    ("S̸l̸a̸s̸h̸", "slash"),

    ("ⓈⓉⓄⓅ", "bubble"),
    ("S̅k̅y̅l̅i̅n̅e̅", "underline"),
    ("A↑r↑r↑o↑w↑s", "arrows"),

    ("ᚱᚢᚾᛁᚲ", "gothic"),
    ("S̶t̶r̶i̶k̶e̶", "strike"),
    ("F̷r̷o̷z̷e̷n̷", "slash")
]


# ============================================================
# SETTINGS
# ============================================================

PER_PAGE = 21


# ============================================================
# GET FONT RESULT
# ============================================================

def apply_font(text, style):

    if style in FONT_MAPS:

        return unicode_font(
            text,
            style
        )

    if style == "smallcaps":

        return small_caps(text)

    if style == "bubble":

        return bubble(text)

    if style == "square":

        return square(text)

    if style == "spacing":

        return spacing(text)

    if style == "strike":

        return strike(text)

    if style == "underline":

        return underline(text)

    if style == "slash":

        return slash(text)

    if style == "ray":

        return ray(text)

    if style == "arrows":

        return arrows(text)

    if style == "reverse":

        return reverse(text)

    if style == "clouds":

        return clouds(text)

    if style == "happy":

        return happy(text)

    if style == "sad":

        return sad(text)

    return text


# ============================================================
# FONT KEYBOARD
# ============================================================

def font_keyboard(
    page,
    text
):

    start = page * PER_PAGE
    end = start + PER_PAGE

    page_fonts = FONTS[
        start:end
    ]

    buttons = []

    # --------------------------------------------------------
    # 3 BUTTONS PER ROW
    # --------------------------------------------------------

    for i in range(
        0,
        len(page_fonts),
        3
    ):

        row = []

        for j in range(3):

            index = i + j

            if index >= len(page_fonts):
                break

            name, style = page_fonts[index]

            absolute_index = (
                start + index
            )

            row.append(
                InlineKeyboardButton(
                    name,
                    callback_data=(
                        f"fontstyle_"
                        f"{absolute_index}"
                    )
                )
            )

        buttons.append(row)

    # --------------------------------------------------------
    # NEXT / BACK
    # --------------------------------------------------------

    navigation = []

    if page > 0:

        navigation.append(
            InlineKeyboardButton(
                "• ʙᴀᴄᴋ •",
                callback_data=(
                    f"fontpage_{page - 1}"
                )
            )
        )

    if end < len(FONTS):

        navigation.append(
            InlineKeyboardButton(
                "• ɴᴇxᴛ •",
                callback_data=(
                    f"fontpage_{page + 1}"
                )
            )
        )

    if navigation:

        buttons.append(
            navigation
        )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# COPY BUTTON
# ============================================================

def copy_keyboard(
    result,
    page
):

    buttons = [

        [
            InlineKeyboardButton(
                "☝️ Click To Copy",
                callback_data="font_copy"
            )
        ]
    ]

    keyboard = font_keyboard(
        page,
        result
    )

    buttons.extend(
        keyboard.inline_keyboard
    )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# RESULT TEXT
# ============================================================

def build_result_text(result):

    safe_result = html.escape(
        str(result)
    )

    return (
        f"<code>{safe_result}</code>\n\n"
        "☝️ <b>Click To Copy</b>"
    )


# ============================================================
# REGISTER FONT HANDLERS
# ============================================================

def register_font_handlers(app):

    # ========================================================
    # /font
    # ========================================================

    @app.on_message(
        filters.command("font")
    )
    async def font_command(
        client,
        message
    ):

        if len(message.command) < 2:

            await message.reply_text(
                "❌ <b>Give me some text.</b>\n\n"
                "Usage:\n"
                "<code>/font Aero Unity</code>"
            )

            return

        text = message.text.split(
            None,
            1
        )[1].strip()

        if not text:

            await message.reply_text(
                "❌ Please enter some text."
            )

            return

        # ----------------------------------------------------
        # ORIGINAL TEXT
        # ----------------------------------------------------

        result = text

        # ----------------------------------------------------
        # SEND RESULT
        # ----------------------------------------------------

        sent = await message.reply_text(
            build_result_text(result),
            reply_markup=copy_keyboard(
                result,
                0
            )
        )

        # ----------------------------------------------------
        # SAVE ORIGINAL TEXT
        # ----------------------------------------------------

        FONT_TEXT_CACHE[
            (sent.chat.id, sent.id)
        ] = text


    # ========================================================
    # FONT STYLE CALLBACK
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^fontstyle_\d+$"
        )
    )
    async def font_style_callback(
        client,
        callback
    ):

        # ----------------------------------------------------
        # VALIDATE FONT INDEX
        # ----------------------------------------------------

        try:

            index = int(
                callback.data.split("_")[1]
            )

            if index < 0 or index >= len(FONTS):

                raise ValueError

            name, style = FONTS[index]

        except Exception:

            await callback.answer(
                "Invalid font.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # GET MESSAGE
        # ----------------------------------------------------

        message = callback.message

        if not message:

            await callback.answer(
                "Message not found.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # GET ORIGINAL TEXT FROM CACHE
        # ----------------------------------------------------

        original = FONT_TEXT_CACHE.get(
            (message.chat.id, message.id)
        )

        # ----------------------------------------------------
        # FALLBACK FOR OLD MESSAGES
        # ----------------------------------------------------

        if original is None:

            current_text = (
                message.text or
                message.caption or
                ""
            )

            if "\n\n" in current_text:

                original = current_text.split(
                    "\n\n",
                    1
                )[0]

            else:

                original = current_text

            original = original.replace(
                "<code>",
                ""
            ).replace(
                "</code>",
                ""
            )

        # ----------------------------------------------------
        # VALIDATE ORIGINAL TEXT
        # ----------------------------------------------------

        if not original:

            await callback.answer(
                "Text not found.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # APPLY FONT TO ORIGINAL TEXT
        # ----------------------------------------------------

        result = apply_font(
            original,
            style
        )

        # ----------------------------------------------------
        # FIND PAGE
        # ----------------------------------------------------

        page = index // PER_PAGE

        # ----------------------------------------------------
        # UPDATE MESSAGE
        # ----------------------------------------------------

        try:

            await message.edit_text(
                build_result_text(result),
                reply_markup=copy_keyboard(
                    result,
                    page
                )
            )

        except Exception as e:

            await callback.answer(
                "Unable to apply font.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # KEEP ORIGINAL TEXT IN CACHE
        # ----------------------------------------------------

        FONT_TEXT_CACHE[
            (message.chat.id, message.id)
        ] = original

        # ----------------------------------------------------
        # CALLBACK SUCCESS
        # ----------------------------------------------------

        await callback.answer(
            f"{name} applied!"
        )


    # ========================================================
    # PAGE NAVIGATION
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^fontpage_\d+$"
        )
    )
    async def font_page_callback(
        client,
        callback
    ):

        try:

            page = int(
                callback.data.split("_")[1]
            )

            max_page = (
                len(FONTS) - 1
            ) // PER_PAGE

            if page < 0:

                page = 0

            if page > max_page:

                page = max_page

            message = callback.message

            if not message:

                await callback.answer(
                    "Message not found.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # GET ORIGINAL TEXT
            # ------------------------------------------------

            original = FONT_TEXT_CACHE.get(
                (message.chat.id, message.id)
            )

            # ------------------------------------------------
            # FALLBACK
            # ------------------------------------------------

            if original is None:

                current_text = (
                    message.text or
                    message.caption or
                    ""
                )

                if "\n\n" in current_text:

                    original = current_text.split(
                        "\n\n",
                        1
                    )[0]

                else:

                    original = current_text

                original = original.replace(
                    "<code>",
                    ""
                ).replace(
                    "</code>",
                    ""
                )

            # ------------------------------------------------
            # VALIDATE
            # ------------------------------------------------

            if not original:

                await callback.answer(
                    "Text not found.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # UPDATE ONLY KEYBOARD
            # ------------------------------------------------

            await message.edit_reply_markup(
                reply_markup=copy_keyboard(
                    original,
                    page
                )
            )

            # ------------------------------------------------
            # KEEP ORIGINAL TEXT
            # ------------------------------------------------

            FONT_TEXT_CACHE[
                (message.chat.id, message.id)
            ] = original

            await callback.answer()

        except Exception:

            await callback.answer(
                "Unable to change page.",
                show_alert=True
            )


    # ========================================================
    # COPY BUTTON
    # ========================================================

    @app.on_callback_query(
        filters.regex(
            r"^font_copy$"
        )
    )
    async def font_copy_callback(
        client,
        callback
    ):

        try:

            message = callback.message

            if not message:

                await callback.answer(
                    "Message not found.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # GET ORIGINAL TEXT
            # ------------------------------------------------

            original = FONT_TEXT_CACHE.get(
                (message.chat.id, message.id)
            )

            # ------------------------------------------------
            # FALLBACK
            # ------------------------------------------------

            if original is None:

                current_text = (
                    message.text or
                    message.caption or
                    ""
                )

                if "\n\n" in current_text:

                    current_text = current_text.split(
                        "\n\n",
                        1
                    )[0]

                original = current_text.replace(
                    "<code>",
                    ""
                ).replace(
                    "</code>",
                    ""
                )

            if not original:

                await callback.answer(
                    "Text not found.",
                    show_alert=True
                )

                return

            # ------------------------------------------------
            # DETERMINE CURRENT FONT RESULT
            # ------------------------------------------------

            current_text = (
                message.text or
                message.caption or
                ""
            )

            if "\n\n" in current_text:

                result = current_text.split(
                    "\n\n",
                    1
                )[0]

            else:

                result = original

            result = result.replace(
                "<code>",
                ""
            ).replace(
                "</code>",
                ""
            )

            # ------------------------------------------------
            # SEND COPYABLE TEXT
            #
            # This keeps compatibility with Pyrogram versions
            # where CopyTextButton is unavailable.
            # ------------------------------------------------

            await callback.message.reply_text(
                f"<code>{html.escape(result)}</code>"
            )

            await callback.answer(
                "Text sent below. Tap and copy it."
            )

        except Exception:

            await callback.answer(
                "Unable to copy text.",
                show_alert=True
    )
