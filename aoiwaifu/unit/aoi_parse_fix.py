import re
import html
import inspect
from functools import wraps
from pyrogram import Client, enums
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from pyrogram.errors import BadRequest
from aoiwaifu.unit.aoi_lang import (
    get_cached_lang_for_chat_or_user,
    get_effective_lang,
    translate_text_phrases,
    translate_reply_markup,
    DEFAULT_LANG,
)

_HTML_TAG_RE = re.compile(r"</?(?:b|strong|i|em|u|s|strike|del|code|pre|blockquote|a|tg-spoiler|tg-emoji)\b[^>]*>", re.IGNORECASE)
_MD_SYNTAX_RE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def normalize_parse_mode(pm, text: str = None):
    """Normalize string or enum parse_mode into Pyrogram enums.ParseMode and auto-detect HTML/Markdown when omitted."""
    if isinstance(pm, enums.ParseMode):
        return pm
    if isinstance(pm, str):
        val = pm.strip().lower()
        if val in ("html", "htm"):
            return enums.ParseMode.HTML
        if val in ("markdown", "md", "markdownv2"):
            return enums.ParseMode.MARKDOWN
        if val in ("disabled", "none", "off"):
            return enums.ParseMode.DISABLED
        if val == "default":
            return enums.ParseMode.DEFAULT
    if pm is None and text and isinstance(text, str):
        if _HTML_TAG_RE.search(text):
            return enums.ParseMode.HTML
        if _MD_SYNTAX_RE.search(text) and "<" not in text and ">" not in text:
            return enums.ParseMode.MARKDOWN
    return enums.ParseMode.DISABLED if pm is None else pm


def strip_formatting_tags(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    cleaned = _HTML_TAG_RE.sub("", text)
    cleaned = html.unescape(cleaned)
    return cleaned


def _extract_chat_and_user_ids(args, kwargs) -> tuple[int | None, int | None]:
    chat_id = kwargs.get("chat_id")
    user_id = None
    if args:
        self_obj = args[0]
        if hasattr(self_obj, "chat") and getattr(self_obj.chat, "id", None) is not None:
            chat_id = self_obj.chat.id
        if hasattr(self_obj, "from_user") and getattr(self_obj.from_user, "id", None) is not None:
            if not getattr(self_obj.from_user, "is_bot", False):
                user_id = self_obj.from_user.id
        if hasattr(self_obj, "message") and getattr(self_obj, "message", None) is not None:
            m = self_obj.message
            if chat_id is None and hasattr(m, "chat") and getattr(m.chat, "id", None) is not None:
                chat_id = m.chat.id
        if chat_id is None and len(args) >= 2 and isinstance(args[1], (int, str)):
            try:
                chat_id = int(args[1])
            except (ValueError, TypeError):
                pass
    try:
        chat_id = int(chat_id) if chat_id is not None else None
    except (ValueError, TypeError):
        chat_id = None
    try:
        user_id = int(user_id) if user_id is not None else None
    except (ValueError, TypeError):
        user_id = None
    return chat_id, user_id


def _resolve_call_lang(args, kwargs) -> str:
    """Resolve active language synchronously from cache."""
    chat_id, user_id = _extract_chat_and_user_ids(args, kwargs)
    return get_cached_lang_for_chat_or_user(chat_id=chat_id, user_id=user_id)


async def _resolve_call_lang_async(args, kwargs) -> str:
    """Resolve active language asynchronously (cache + MongoDB fallback)."""
    chat_id, user_id = _extract_chat_and_user_ids(args, kwargs)
    cached = get_cached_lang_for_chat_or_user(chat_id=chat_id, user_id=user_id)
    if cached != DEFAULT_LANG:
        return cached
    return await get_effective_lang(chat_id=chat_id, user_id=user_id)


def _wrap_send_or_edit(func, text_Param="text"):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        kwargs.pop("quote", None)

        try:
            sig_params = inspect.signature(func).parameters
            has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values())
            if not has_var_kw:
                if "disable_web_page_preview" in kwargs and "disable_web_page_preview" not in sig_params:
                    dwp = kwargs.pop("disable_web_page_preview")
                    if "link_preview_options" in sig_params and "link_preview_options" not in kwargs:
                        try:
                            from pyrogram.types import LinkPreviewOptions
                            kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=bool(dwp))
                        except Exception:
                            pass
                for k in list(kwargs.keys()):
                    if k not in sig_params:
                        kwargs.pop(k, None)
        except Exception:
            kwargs.pop("disable_web_page_preview", None)

        lang = await _resolve_call_lang_async(args, kwargs)

        if "reply_markup" in kwargs and kwargs["reply_markup"] is not None:
            translate_reply_markup(kwargs["reply_markup"], lang)

        txt = kwargs.get(text_Param)
        if txt is not None and isinstance(txt, str) and lang != DEFAULT_LANG:
            txt = translate_text_phrases(txt, lang)
            kwargs[text_Param] = txt
        elif txt is None and len(args) >= 2 and text_Param == "text" and isinstance(args[1], str):
            txt = args[1]
            if lang != DEFAULT_LANG:
                txt = translate_text_phrases(txt, lang)
                args = (args[0], txt) + args[2:]
        elif txt is None and len(args) >= 3 and text_Param == "text" and isinstance(args[2], str):
            txt = args[2]
            if lang != DEFAULT_LANG:
                txt = translate_text_phrases(txt, lang)
                args = (args[0], args[1], txt) + args[3:]

        positional_parse_mode = False
        try:
            bound = inspect.signature(func).bind_partial(*args, **kwargs)
            positional_parse_mode = (
                "parse_mode" in bound.arguments
                and "parse_mode" not in kwargs
            )
        except (TypeError, ValueError):
            pass

        if ("parse_mode" in kwargs or txt) and not positional_parse_mode:
            kwargs["parse_mode"] = normalize_parse_mode(kwargs.get("parse_mode"), txt)

        try:
            return await func(*args, **kwargs)
        except BadRequest as e:
            err_str = str(e).upper()
            if any(k in err_str for k in ("ENTITY", "PARSE", "TAG", "MARKDOWN", "HTML", "CAN'T FIND END")):
                if positional_parse_mode:
                    args = list(args)
                    try:
                        parse_index = list(inspect.signature(func).parameters).index("parse_mode")
                        args[parse_index] = enums.ParseMode.DISABLED
                        args = tuple(args)
                    except (ValueError, IndexError):
                        pass
                else:
                    kwargs["parse_mode"] = enums.ParseMode.DISABLED
                if text_Param in kwargs and isinstance(kwargs[text_Param], str):
                    kwargs[text_Param] = strip_formatting_tags(kwargs[text_Param])
                return await func(*args, **kwargs)
            raise
    return wrapper


def _wrap_edit_reply_markup(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        lang = await _resolve_call_lang_async(args, kwargs)
        if "reply_markup" in kwargs and kwargs["reply_markup"] is not None:
            translate_reply_markup(kwargs["reply_markup"], lang)
        elif len(args) >= 2 and getattr(args[-1], "inline_keyboard", None) is not None:
            translate_reply_markup(args[-1], lang)
        return await func(*args, **kwargs)
    return wrapper


def _wrap_edit_media(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        lang = await _resolve_call_lang_async(args, kwargs)
        if "reply_markup" in kwargs and kwargs["reply_markup"] is not None:
            translate_reply_markup(kwargs["reply_markup"], lang)

        media = kwargs.get("media")
        if media is None and len(args) >= 2:
            media = args[1]
        if media is not None and hasattr(media, "caption") and getattr(media, "caption", None):
            if lang != DEFAULT_LANG and isinstance(media.caption, str):
                media.caption = translate_text_phrases(media.caption, lang)
            pm = getattr(media, "parse_mode", None)
            media.parse_mode = normalize_parse_mode(pm, media.caption)
        try:
            return await func(*args, **kwargs)
        except BadRequest as e:
            err_str = str(e).upper()
            if media is not None and any(k in err_str for k in ("ENTITY", "PARSE", "TAG", "MARKDOWN", "HTML")):
                media.parse_mode = enums.ParseMode.DISABLED
                if getattr(media, "caption", None):
                    media.caption = strip_formatting_tags(media.caption)
                return await func(*args, **kwargs)
            raise
    return wrapper


def _wrap_callback_answer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        lang = await _resolve_call_lang_async(args, kwargs)
        if "text" in kwargs and kwargs["text"] is not None:
            val = str(kwargs["text"])
            if lang != DEFAULT_LANG:
                val = translate_text_phrases(val, lang)
            if len(val) > 200:
                val = val[:197] + "..."
            kwargs["text"] = val
        elif len(args) >= 2 and isinstance(args[1], str):
            val = args[1]
            if lang != DEFAULT_LANG:
                val = translate_text_phrases(val, lang)
            if len(val) > 200:
                val = val[:197] + "..."
            args = list(args)
            args[1] = val
            args = tuple(args)
        try:
            return await func(*args, **kwargs)
        except Exception:
            return False
    return wrapper


_PATCHED = False

def install_parse_mode_guard():
    """Patch Pyrogram Client, Message, and CallbackQuery methods to prevent any parse_mode crashes and apply i18n."""
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # Client methods
    Client.send_message = _wrap_send_or_edit(Client.send_message, "text")
    Client.send_photo = _wrap_send_or_edit(Client.send_photo, "caption")
    Client.send_video = _wrap_send_or_edit(Client.send_video, "caption")
    Client.send_animation = _wrap_send_or_edit(Client.send_animation, "caption")
    Client.send_document = _wrap_send_or_edit(Client.send_document, "caption")
    Client.edit_message_text = _wrap_send_or_edit(Client.edit_message_text, "text")
    Client.edit_message_caption = _wrap_send_or_edit(Client.edit_message_caption, "caption")
    Client.edit_message_media = _wrap_edit_media(Client.edit_message_media)
    if hasattr(Client, "edit_message_reply_markup"):
        Client.edit_message_reply_markup = _wrap_edit_reply_markup(Client.edit_message_reply_markup)
    if hasattr(Client, "edit_inline_text"):
        Client.edit_inline_text = _wrap_send_or_edit(Client.edit_inline_text, "text")
    if hasattr(Client, "edit_inline_caption"):
        Client.edit_inline_caption = _wrap_send_or_edit(Client.edit_inline_caption, "caption")

    # Message bound shortcuts
    Message.reply_text = _wrap_send_or_edit(Message.reply_text, "text")
    Message.reply = _wrap_send_or_edit(Message.reply, "text")
    Message.reply_photo = _wrap_send_or_edit(Message.reply_photo, "caption")
    Message.reply_video = _wrap_send_or_edit(Message.reply_video, "caption")
    Message.reply_animation = _wrap_send_or_edit(Message.reply_animation, "caption")
    Message.edit_text = _wrap_send_or_edit(Message.edit_text, "text")
    Message.edit = _wrap_send_or_edit(Message.edit, "text")
    Message.edit_caption = _wrap_send_or_edit(Message.edit_caption, "caption")
    Message.edit_media = _wrap_edit_media(Message.edit_media)
    if hasattr(Message, "edit_reply_markup"):
        Message.edit_reply_markup = _wrap_edit_reply_markup(Message.edit_reply_markup)

    # CallbackQuery shortcuts
    CallbackQuery.edit_message_text = _wrap_send_or_edit(CallbackQuery.edit_message_text, "text")
    CallbackQuery.edit_message_caption = _wrap_send_or_edit(CallbackQuery.edit_message_caption, "caption")
    CallbackQuery.edit_message_media = _wrap_edit_media(CallbackQuery.edit_message_media)
    if hasattr(CallbackQuery, "edit_message_reply_markup"):
        CallbackQuery.edit_message_reply_markup = _wrap_edit_reply_markup(CallbackQuery.edit_message_reply_markup)
    CallbackQuery.answer = _wrap_callback_answer(CallbackQuery.answer)


class SudoUsersHybrid:
    """
    Hybrid proxy that acts as BOTH:
    1) A Motor collection (`await sudo_users.find_one(...)`, `await sudo_users.update_one(...)`, etc.)
    2) A list/set of sudo user IDs (`user_id in sudo_users` or `str(user_id) in sudo_users`)
    This resolves the collision between `sudo_users = SUDO` and `sudo_users = db['sudo_users']`.
    """
    def __init__(self, motor_collection, static_sudo_ids, owner_id=None):
        self._col = motor_collection
        self._ids = set()
        for uid in (static_sudo_ids or []):
            try:
                self._ids.add(int(uid))
                self._ids.add(str(int(uid)))
            except (ValueError, TypeError):
                pass
        if owner_id is not None:
            try:
                self._ids.add(int(owner_id))
                self._ids.add(str(int(owner_id)))
            except (ValueError, TypeError):
                pass

    def __contains__(self, item):
        return item in self._ids

    def __iter__(self):
        return iter(x for x in self._ids if isinstance(x, int))

    def __getattr__(self, name):
        return getattr(self._col, name)
