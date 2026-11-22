"""
Language & Group Settings Module (aoiwaifu/modules/lang.py)
Provides:
- /lang, /language, /setlang, /settings in DM (User Language) and Groups (Group Language via Admin Settings)
- Inline callback handlers for DM first-start language selection, DM language menu, and Group Settings language selector
- Web Server endpoints (/api/i18n, /api/i18n/set, /js/aoi_i18n.js) for Dress-Up Mini App & all 10 HTML5 Games
"""
import html
import json
from pyrogram import Client, filters, enums
try:
    from pyrogram.enums import ChatMemberStatus
except ImportError:
    ChatMemberStatus = getattr(enums, 'ChatMemberStatus', None)
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from aoiwaifu import (
    app,
    OWNER_ID,
    sudo_users,
    group_user_totals_collection,
    group_ctimes,
    x,
)
from aoiwaifu.unit.aoi_lang import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_LANG_CODES,
    DEFAULT_LANG,
    normalize_lang_code,
    get_lang_meta,
    get_lang_label,
    get_user_lang,
    set_user_lang,
    get_chat_lang,
    set_chat_lang,
    get_effective_lang,
    build_language_keyboard,
    t,
)
from aoiwaifu.modules.start import generate_start_message


async def is_group_admin_or_owner(client: Client, chat_id: int, user_id: int) -> bool:
    """Allow group-language changes only to this group's owner or administrators."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
        )
    except Exception:
        return False


async def _get_group_ctime(chat_id: int) -> int:
    cid_str = str(chat_id)
    if cid_str in group_ctimes:
        return int(group_ctimes[cid_str])
    try:
        doc = await group_user_totals_collection.find_one({"group_id": cid_str}, {"ctime": 1})
        if doc and doc.get("ctime"):
            group_ctimes[cid_str] = int(doc["ctime"])
            return int(doc["ctime"])
    except Exception:
        pass
    return 80


def build_dm_lang_menu_text(lang: str) -> str:
    return (
        "╭━〔 🌐 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 • 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄 〕━╮\n\n"
        f"<blockquote>{t('lang_select_dm_title', lang)}\n"
        f"{t('lang_select_dm_body', lang)}\n\n"
        f"🌐 <b>Current:</b> <code>{get_lang_label(lang)}</code></blockquote>\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯"
    )


async def build_group_settings_text_and_markup(chat_id: int, group_title: str, lang: str = None) -> tuple[str, InlineKeyboardMarkup]:
    if not lang:
        lang = await get_chat_lang(chat_id)
    ctime = await _get_group_ctime(chat_id)
    safe_title = html.escape(str(group_title or f"Group {chat_id}"))
    text = (
        "╭━〔 ⚙️ 𝐆𝐑𝐎𝐔𝐏 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒 〕━╮\n\n"
        f"<blockquote>{t('lang_select_group_title', lang)}\n\n"
        f"{t('lang_select_group_body', lang, group_title=safe_title, lang_label=get_lang_label(lang), ctime=ctime)}</blockquote>\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━╯"
    )
    markup = build_language_keyboard(
        callback_prefix="set_grp_lang",
        current_lang=lang,
        back_callback=None,
    )
    return text, markup


# 🔹 Command: /lang, /language, /setlang, /settings in Private Chat (DM)
@app.on_message(filters.command(["lang", "language", "setlang", "settings"]) & filters.private)
async def dm_lang_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else message.chat.id
    if len(message.command) > 1:
        arg_code = message.command[1].strip().lower()
        if arg_code in SUPPORTED_LANG_CODES:
            new_lang = await set_user_lang(user_id, arg_code)
            await message.reply_text(
                t("lang_updated_dm", new_lang, lang_label=get_lang_label(new_lang)),
                parse_mode=enums.ParseMode.HTML,
            )
            return

    cur_lang = await get_user_lang(user_id)
    text = build_dm_lang_menu_text(cur_lang)
    markup = build_language_keyboard(
        callback_prefix="set_dm_lang",
        current_lang=cur_lang,
        back_callback="back_to_home",
        extra_suffix=":menu",
    )
    await message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


# 🔹 Command: /lang, /language, /setlang, /settings in Group Chat
@app.on_message(filters.command(["lang", "language", "setlang", "settings"]) & filters.group)
async def group_settings_lang_command(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    cur_lang = await get_chat_lang(chat_id)

    if not await is_group_admin_or_owner(client, chat_id, user_id):
        await message.reply_text(t("lang_admin_only", cur_lang), parse_mode=enums.ParseMode.HTML)
        return

    if len(message.command) > 1:
        arg_code = message.command[1].strip().lower()
        if arg_code in SUPPORTED_LANG_CODES:
            new_lang = await set_chat_lang(chat_id, arg_code)
            await message.reply_text(
                t("lang_updated_group", new_lang, lang_label=get_lang_label(new_lang)),
                parse_mode=enums.ParseMode.HTML,
            )
            return

    group_title = getattr(message.chat, "title", None) or f"Group {chat_id}"
    text, markup = await build_group_settings_text_and_markup(chat_id, group_title, lang=cur_lang)
    await message.reply_text(text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


# 🔹 Callback: Open DM Language Menu from Start Screen
@app.on_callback_query(filters.regex(r"^open_dm_lang$"))
async def open_dm_lang_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id if query.from_user else 0
    cur_lang = await get_user_lang(user_id)
    text = build_dm_lang_menu_text(cur_lang)
    markup = build_language_keyboard(
        callback_prefix="set_dm_lang",
        current_lang=cur_lang,
        back_callback="back_to_home",
        extra_suffix=":menu",
    )
    try:
        await query.message.edit_caption(caption=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await query.message.edit_text(text=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    await query.answer()


# 🔹 Callback: Open Group Settings & Language Menu from Group Start Button
@app.on_callback_query(filters.regex(r"^open_group_settings$"))
async def open_group_settings_callback(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id if (query.message and query.message.chat) else 0
    user_id = query.from_user.id if query.from_user else 0
    cur_lang = await get_chat_lang(chat_id)

    if not await is_group_admin_or_owner(client, chat_id, user_id):
        await query.answer(t("lang_admin_only", cur_lang), show_alert=True)
        return

    group_title = getattr(query.message.chat, "title", None) or f"Group {chat_id}"
    text, markup = await build_group_settings_text_and_markup(chat_id, group_title, lang=cur_lang)
    try:
        await query.message.edit_caption(caption=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await query.message.edit_text(text=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    await query.answer()


# 🔹 Callback: Select DM Language (First-Start or Menu)
@app.on_callback_query(filters.regex(r"^set_dm_lang:([a-z]{2})(?::(start|menu))?$"))
async def set_dm_lang_callback(client: Client, query: CallbackQuery):
    lang = await get_effective_lang(query)
    lang_code = query.matches[0].group(1)
    mode = query.matches[0].group(2) or "start"
    user_id = query.from_user.id if query.from_user else (query.message.chat.id if query.message and query.message.chat else 0)

    new_lang = await set_user_lang(user_id, lang_code)
    confirm_msg = t("lang_updated_dm", new_lang, lang_label=get_lang_label(new_lang))
    await query.answer(confirm_msg, show_alert=False)

    # After choosing language on first /start (or from start menu), display the localized Start Home screen!
    caption, buttons = await generate_start_message(client, query.message, lang=new_lang)
    markup = InlineKeyboardMarkup(buttons)
    try:
        await query.message.edit_caption(caption=caption, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await query.message.edit_text(text=caption, reply_markup=markup, parse_mode=enums.ParseMode.HTML)


# 🔹 Callback: Select Group Language (Group Settings)
@app.on_callback_query(filters.regex(r"^set_grp_lang:([a-z]{2})$"))
async def set_group_lang_callback(client: Client, query: CallbackQuery):
    lang_code = query.matches[0].group(1)
    chat_id = query.message.chat.id if (query.message and query.message.chat) else 0
    user_id = query.from_user.id if query.from_user else 0
    cur_lang = await get_chat_lang(chat_id)

    if not await is_group_admin_or_owner(client, chat_id, user_id):
        await query.answer(t("lang_admin_only", cur_lang), show_alert=True)
        return

    new_lang = await set_chat_lang(chat_id, lang_code)
    confirm_msg = t("lang_updated_group", new_lang, lang_label=get_lang_label(new_lang))
    await query.answer(confirm_msg, show_alert=False)

    group_title = getattr(query.message.chat, "title", None) or f"Group {chat_id}"
    text, markup = await build_group_settings_text_and_markup(chat_id, group_title, lang=new_lang)
    try:
        await query.message.edit_caption(caption=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
    except Exception:
        await query.message.edit_text(text=text, reply_markup=markup, parse_mode=enums.ParseMode.HTML)
