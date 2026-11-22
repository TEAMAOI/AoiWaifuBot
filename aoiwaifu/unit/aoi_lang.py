"""
Central 10-Language Localization Engine for Aoi Waifu Bot & Mini WebApps.
Supports:
  1. en - 🇺🇸 English
  2. ru - 🇷🇺 Русский
  3. es - 🇪🇸 Español
  4. pt - 🇧🇷 Português
  5. id - 🇮🇩 Indonesia
  6. hi - 🇮🇳 हिन्दी
  7. my - 🇲🇲 မြန်မာစာ
  8. ar - 🇸🇦 العربية
  9. tr - 🇹🇷 Türkçe
 10. vi - 🇻🇳 Tiếng Việt
"""
import json
import os
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

LANGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "langs"))

SUPPORTED_LANGUAGES = [
    {"num": 1, "code": "en", "name": "English", "flag": "🇺🇸", "native": "English", "label": "🇺🇸 English", "desc": "Global default / International users", "dir": "ltr"},
    {"num": 2, "code": "ru", "name": "Russian", "flag": "🇷🇺", "native": "Русский", "label": "🇷🇺 Русский", "desc": "Telegram gaming & tech community", "dir": "ltr"},
    {"num": 3, "code": "es", "name": "Spanish", "flag": "🇪🇸", "native": "Español", "label": "🇪🇸 Español", "desc": "Latin America (Mexico, Colombia) & Spain", "dir": "ltr"},
    {"num": 4, "code": "pt", "name": "Portuguese", "flag": "🇧🇷", "native": "Português", "label": "🇧🇷 Português", "desc": "Brazil (massive Telegram community)", "dir": "ltr"},
    {"num": 5, "code": "id", "name": "Indonesian", "flag": "🇮🇩", "native": "Indonesia", "label": "🇮🇩 Indonesia", "desc": "Southeast Asia gaming & bot users", "dir": "ltr"},
    {"num": 6, "code": "hi", "name": "Hindi", "flag": "🇮🇳", "native": "हिन्दी", "label": "🇮🇳 हिन्दी", "desc": "Indian subcontinent", "dir": "ltr"},
    {"num": 7, "code": "my", "name": "Burmese", "flag": "🇲🇲", "native": "မြန်မာစာ", "label": "🇲🇲 မြန်မာစာ", "desc": "Myanmar (Game items, channels & resale)", "dir": "ltr"},
    {"num": 8, "code": "ar", "name": "Arabic", "flag": "🇸🇦", "native": "العربية", "label": "🇸🇦 العربية", "desc": "Middle East & North Africa (MENA)", "dir": "rtl"},
    {"num": 9, "code": "tr", "name": "Turkish", "flag": "🇹🇷", "native": "Türkçe", "label": "🇹🇷 Türkçe", "desc": "Turkey (Crypto, bot & community channels)", "dir": "ltr"},
    {"num": 10, "code": "vi", "name": "Vietnamese", "flag": "🇻🇳", "native": "Tiếng Việt", "label": "🇻🇳 Tiếng Việt", "desc": "Vietnam (Active Telegram gaming/crypto audience)", "dir": "ltr"},
]

SUPPORTED_LANG_CODES = tuple(item["code"] for item in SUPPORTED_LANGUAGES)
LANG_META_BY_CODE = {item["code"]: item for item in SUPPORTED_LANGUAGES}
DEFAULT_LANG = "en"

# Fixed max button text lengths so inline buttons never overflow on mobile screens
MAX_MULTI_BTN_LEN = 16
MAX_SINGLE_BTN_LEN = 22

# In-memory caches for fast lookup during message rendering and send/edit hooks
user_langs_cache: dict[int, str] = {}
user_lang_set_cache: dict[int, bool] = {}
chat_langs_cache: dict[int, str] = {}
chat_lang_set_cache: dict[int, bool] = {}

_LANG_DATA: dict[str, dict] = {}
_SORTED_PHRASES: dict[str, list[tuple[str, str]]] = {}


def load_all_languages(force: bool = False) -> dict[str, dict]:
    global _LANG_DATA, _SORTED_PHRASES
    if _LANG_DATA and not force:
        return _LANG_DATA
    _LANG_DATA = {}
    _SORTED_PHRASES = {}
    for code in SUPPORTED_LANG_CODES:
        fpath = os.path.join(LANGS_DIR, f"{code}.json")
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _LANG_DATA[code] = data
                    phrases = data.get("phrases") or {}
                    if isinstance(phrases, dict):
                        _SORTED_PHRASES[code] = sorted(
                            [(k, v) for k, v in phrases.items() if k and v and isinstance(k, str) and isinstance(v, str)],
                            key=lambda kv: len(kv[0]),
                            reverse=True,
                        )
            except Exception:
                _LANG_DATA[code] = {}
                _SORTED_PHRASES[code] = []
        else:
            _LANG_DATA[code] = {}
            _SORTED_PHRASES[code] = []
    return _LANG_DATA


def normalize_lang_code(code: str | None) -> str:
    if not code or not isinstance(code, str):
        return DEFAULT_LANG
    clean = code.strip().lower().split("-")[0].split("_")[0]
    if clean in LANG_META_BY_CODE:
        return clean
    return DEFAULT_LANG


def get_lang_meta(code: str | None) -> dict:
    norm = normalize_lang_code(code)
    return LANG_META_BY_CODE.get(norm, LANG_META_BY_CODE[DEFAULT_LANG])


def get_lang_label(code: str | None) -> str:
    return get_lang_meta(code)["label"]


def get_lang_dict(code: str | None) -> dict:
    load_all_languages()
    norm = normalize_lang_code(code)
    return _LANG_DATA.get(norm) or _LANG_DATA.get(DEFAULT_LANG) or {}


def get_webapp_translations(code: str | None = None) -> dict:
    load_all_languages()
    if code:
        d = get_lang_dict(code)
        return d.get("webapp", {})
    return {c: (_LANG_DATA.get(c, {}).get("webapp", {})) for c in SUPPORTED_LANG_CODES}


def clamp_button_text(text: str, max_len: int = MAX_MULTI_BTN_LEN) -> str:
    """Ensure button label stays within a fixed mobile-safe character length."""
    if not text or not isinstance(text, str):
        return str(text or "")
    s = " ".join(text.strip().split())
    if len(s) <= max_len:
        return s
    return s[: max(4, max_len - 1)].rstrip() + "…"


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Retrieve a localized string from the language files and format with kwargs."""
    load_all_languages()
    norm = normalize_lang_code(lang)
    lang_dict = _LANG_DATA.get(norm) or {}
    en_dict = _LANG_DATA.get(DEFAULT_LANG) or {}
    template = lang_dict.get(key)
    if template is None or isinstance(template, dict):
        template = en_dict.get(key, key)
    if isinstance(template, dict):
        template = key
    if kwargs and isinstance(template, str):
        try:
            res = template.format(**kwargs)
        except Exception:
            res = template
    else:
        res = str(template)
    if isinstance(key, str) and key.startswith("btn_"):
        limit = MAX_SINGLE_BTN_LEN if key in ("btn_play_daily", "btn_play_game", "btn_add_to_group") else MAX_MULTI_BTN_LEN
        return clamp_button_text(res, limit)
    return res


def translate_text_phrases(text: str, lang: str = DEFAULT_LANG) -> str:
    """Apply longest-match-first phrase localization when lang != 'en'."""
    if not text or not isinstance(text, str):
        return text
    norm = normalize_lang_code(lang)
    if norm == DEFAULT_LANG:
        return text
    load_all_languages()
    sorted_pairs = _SORTED_PHRASES.get(norm)
    if not sorted_pairs:
        phrases = (_LANG_DATA.get(norm) or {}).get("phrases") or {}
        if not phrases:
            return text
        sorted_pairs = sorted(
            [(k, v) for k, v in phrases.items() if k and v],
            key=lambda kv: len(kv[0]),
            reverse=True,
        )
        _SORTED_PHRASES[norm] = sorted_pairs
    out = text
    for src, dst in sorted_pairs:
        if src in out:
            out = out.replace(src, dst)
    return out


def tr(text_or_key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Universal translation helper usable in every command, callback, and admin handler:
    - If `text_or_key` matches a key in the language JSON files, formats and returns `t(text_or_key, lang, **kwargs)`.
    - Otherwise formats `text_or_key` (if kwargs provided) and translates all phrases into `lang`.
    """
    if not text_or_key or not isinstance(text_or_key, str):
        return str(text_or_key or "")
    load_all_languages()
    norm = normalize_lang_code(lang)
    lang_dict = _LANG_DATA.get(norm) or {}
    en_dict = _LANG_DATA.get(DEFAULT_LANG) or {}
    if (text_or_key in lang_dict and not isinstance(lang_dict[text_or_key], dict)) or (
        text_or_key in en_dict and not isinstance(en_dict[text_or_key], dict)
    ):
        return t(text_or_key, norm, **kwargs)
    out = text_or_key
    if kwargs:
        try:
            out = out.format(**kwargs)
        except Exception:
            pass
    if norm != DEFAULT_LANG:
        out = translate_text_phrases(out, norm)
    return out


def translate_reply_markup(reply_markup, lang: str = DEFAULT_LANG):
    """Translate inline keyboard button labels and enforce fixed compact button lengths."""
    if reply_markup is None:
        return reply_markup
    rows = getattr(reply_markup, "inline_keyboard", None)
    if not rows:
        return reply_markup
    norm = normalize_lang_code(lang)
    load_all_languages()
    phrases = (_LANG_DATA.get(norm) or {}).get("phrases") or {}
    for row in rows:
        row_len = len(row) if hasattr(row, "__len__") else 2
        max_btn_chars = MAX_SINGLE_BTN_LEN if row_len == 1 else MAX_MULTI_BTN_LEN
        for btn in row:
            txt = getattr(btn, "text", None)
            if txt and isinstance(txt, str):
                new_txt = txt
                if norm != DEFAULT_LANG and phrases:
                    new_txt = phrases.get(txt) or translate_text_phrases(txt, norm)
                new_txt = clamp_button_text(new_txt, max_btn_chars)
                if new_txt != txt:
                    try:
                        btn.text = new_txt
                    except Exception:
                        try:
                            object.__setattr__(btn, "text", new_txt)
                        except Exception:
                            pass
    return reply_markup


def get_cached_lang_for_chat_or_user(chat_id: int | str | None = None, user_id: int | None = None) -> str:
    """Fast synchronous cache lookup used by send/edit wrappers."""
    try:
        if chat_id is not None:
            cid = int(chat_id)
            if cid < 0 and cid in chat_langs_cache:
                c_lang = chat_langs_cache[cid]
                if c_lang != DEFAULT_LANG or chat_lang_set_cache.get(cid, False):
                    return c_lang
            if cid > 0 and cid in user_langs_cache:
                return user_langs_cache[cid]
    except (ValueError, TypeError):
        pass
    try:
        if user_id is not None:
            uid = int(user_id)
            if uid in user_langs_cache:
                return user_langs_cache[uid]
    except (ValueError, TypeError):
        pass
    return DEFAULT_LANG


async def get_user_lang(user_id: int | None) -> str:
    if not user_id:
        return DEFAULT_LANG
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return DEFAULT_LANG
    if uid in user_langs_cache:
        return user_langs_cache[uid]
    try:
        from aoiwaifu import user_collection
        doc = await user_collection.find_one({"id": uid}, {"lang": 1, "lang_set": 1})
        if doc and doc.get("lang"):
            code = normalize_lang_code(doc.get("lang"))
            user_langs_cache[uid] = code
            user_lang_set_cache[uid] = bool(doc.get("lang_set", True))
            return code
    except Exception:
        pass
    return DEFAULT_LANG


async def has_user_set_lang(user_id: int | None) -> bool:
    if not user_id:
        return False
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return False
    if uid in user_lang_set_cache and user_lang_set_cache[uid]:
        return True
    try:
        from aoiwaifu import user_collection
        doc = await user_collection.find_one({"id": uid}, {"lang": 1, "lang_set": 1})
        if doc and doc.get("lang_set") and doc.get("lang"):
            user_langs_cache[uid] = normalize_lang_code(doc.get("lang"))
            user_lang_set_cache[uid] = True
            return True
    except Exception:
        pass
    return False


async def set_user_lang(user_id: int, lang_code: str) -> str:
    uid = int(user_id)
    norm = normalize_lang_code(lang_code)
    user_langs_cache[uid] = norm
    user_lang_set_cache[uid] = True
    try:
        from aoiwaifu import user_collection
        await user_collection.update_one(
            {"id": uid},
            {
                "$set": {"lang": norm, "lang_set": True},
                "$setOnInsert": {"balance": 0, "tokens": 0, "characters": []},
            },
            upsert=True,
        )
    except Exception:
        pass
    return norm


async def get_chat_lang(chat_id: int | str | None) -> str:
    if chat_id is None:
        return DEFAULT_LANG
    try:
        cid = int(chat_id)
    except (ValueError, TypeError):
        return DEFAULT_LANG
    if cid > 0:
        return await get_user_lang(cid)
    if cid in chat_langs_cache:
        return chat_langs_cache[cid]
    try:
        from aoiwaifu import group_user_totals_collection, db
        doc = await group_user_totals_collection.find_one({"group_id": str(cid)}, {"lang": 1})
        if not doc or not doc.get("lang"):
            doc = await db["chat_langs"].find_one({"chat_id": cid}, {"lang": 1})
        if doc and doc.get("lang"):
            code = normalize_lang_code(doc.get("lang"))
            chat_langs_cache[cid] = code
            chat_lang_set_cache[cid] = True
            return code
    except Exception:
        pass
    return DEFAULT_LANG


async def set_chat_lang(chat_id: int | str, lang_code: str) -> str:
    cid = int(chat_id)
    norm = normalize_lang_code(lang_code)
    chat_langs_cache[cid] = norm
    chat_lang_set_cache[cid] = True
    try:
        from aoiwaifu import group_user_totals_collection, db
        await group_user_totals_collection.update_one(
            {"group_id": str(cid)},
            {"$set": {"lang": norm, "lang_set": True}, "$setOnInsert": {"ctime": 80}},
            upsert=True,
        )
        await db["chat_langs"].update_one(
            {"chat_id": cid},
            {"$set": {"chat_id": cid, "lang": norm, "lang_set": True}},
            upsert=True,
        )
    except Exception:
        pass
    return norm


async def get_effective_lang(message_or_query=None, chat_id: int | None = None, user_id: int | None = None) -> str:
    """
    Determine the effective language for any message, callback query, inline query, PTB Update, or WebApp request:
    - In groups (chat_id < 0): uses the group's configured language if set; if the group has not configured a language yet,
      falls back to the triggering user's configured language so `/daily` and commands open in the user's chosen language.
    - In private chat (chat_id > 0): uses the user's configured language.
    """
    cid = chat_id
    uid = user_id
    if message_or_query is not None:
        eff_chat = getattr(message_or_query, "effective_chat", None)
        eff_user = getattr(message_or_query, "effective_user", None)
        if cid is None and eff_chat is not None and getattr(eff_chat, "id", None) is not None:
            try:
                cid = int(eff_chat.id)
            except (ValueError, TypeError):
                pass
        if uid is None and eff_user is not None and getattr(eff_user, "id", None) is not None:
            try:
                uid = int(eff_user.id)
            except (ValueError, TypeError):
                pass

        msg = getattr(message_or_query, "message", None) or getattr(message_or_query, "effective_message", None) or message_or_query
        chat = getattr(msg, "chat", None)
        from_user = getattr(message_or_query, "from_user", None) or getattr(msg, "from_user", None)
        if cid is None and chat is not None and getattr(chat, "id", None) is not None:
            try:
                cid = int(chat.id)
            except (ValueError, TypeError):
                pass
        if uid is None and from_user is not None and getattr(from_user, "id", None) is not None:
            try:
                uid = int(from_user.id)
            except (ValueError, TypeError):
                pass

    if cid is not None:
        try:
            if int(cid) < 0:
                c_lang = await get_chat_lang(int(cid))
                if c_lang != DEFAULT_LANG or chat_lang_set_cache.get(int(cid), False):
                    return c_lang
                if uid is not None and int(uid) > 0:
                    u_lang = await get_user_lang(int(uid))
                    if u_lang != DEFAULT_LANG:
                        return u_lang
                return c_lang
        except (ValueError, TypeError):
            pass
    if uid is not None:
        try:
            if int(uid) > 0:
                return await get_user_lang(int(uid))
        except (ValueError, TypeError):
            pass
    if cid is not None:
        try:
            if int(cid) > 0:
                return await get_user_lang(int(cid))
        except (ValueError, TypeError):
            pass
    return DEFAULT_LANG


def build_language_keyboard(
    callback_prefix: str = "set_dm_lang",
    current_lang: str | None = None,
    back_callback: str | None = None,
    extra_suffix: str = "",
) -> InlineKeyboardMarkup:
    """Build a compact 2-column inline keyboard showing all 10 supported languages."""
    cur = normalize_lang_code(current_lang) if current_lang else None
    buttons = []
    for item in SUPPORTED_LANGUAGES:
        code = item["code"]
        label = item["label"]
        if cur and code == cur:
            label = f"✅ {label}"
        cb_data = f"{callback_prefix}:{code}{extra_suffix}"
        buttons.append(InlineKeyboardButton(clamp_button_text(label, MAX_MULTI_BTN_LEN), callback_data=cb_data))

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    if back_callback:
        rows.append([InlineKeyboardButton(t("btn_back", cur or DEFAULT_LANG), callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)
