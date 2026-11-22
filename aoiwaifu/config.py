"""Centralized environment-based configuration for AoiWaifu Bot."""

import os
from dotenv import load_dotenv

load_dotenv()


def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_int_list(raw: str) -> list[int]:
    result: list[int] = []
    for item in str(raw or "").split(","):
        item = item.strip()
        if item and item.lstrip("-").isdigit():
            result.append(int(item))
    return result


def _parse_str_list(raw: str, fallback: list[str]) -> list[str]:
    items = [x.strip() for x in str(raw or "").split(",") if x.strip()]
    return items if items else list(fallback)


# --- Telegram Credentials (Required) ---
API_ID: int = _parse_int(os.getenv("API_ID", "0"), 0)
API_HASH: str = os.getenv("API_HASH", "").strip()
TOKEN: str = os.getenv("TOKEN", "").strip()

# --- Database (Required) ---
MONGO_URL: str = os.getenv("MONGO_URL", "").strip()
BACKUP_MONGO_URL: str = os.getenv("BACKUP_MONGO_URL", "").strip() or MONGO_URL
DB_NAME: str = os.getenv("DB_NAME", "aoiwaifu").strip() or "aoiwaifu"

# --- Owner & Sudo Admins ---
OWNER_ID: int = _parse_int(os.getenv("OWNER_ID", "0"), 0)
OWNER_USERNAME: str = os.getenv("OWNER_USERNAME", "").strip().lstrip("@")
SUDO: list[int] = _parse_int_list(os.getenv("SUDO", ""))

# --- Channels & Chats ---
GLOG: str = os.getenv("GLOG", "").strip()
CHARA_CHANNEL_ID: str = os.getenv("CHARA_CHANNEL_ID", "").strip() or GLOG
SUPPORT_CHAT_ID: str = os.getenv("SUPPORT_CHAT_ID", "").strip()
SUPPORT_CHAT: str = os.getenv("SUPPORT_CHAT", "https://t.me/Telegram").strip()
UPDATE_CHAT: str = os.getenv("UPDATE_CHAT", "https://t.me/Telegram").strip()

# --- Image Hosting (ImgBB Only) ---
IMGBB_API_KEYS: list[str] = [
    k.strip()
    for k in os.getenv("IMGBB_API_KEYS", os.getenv("IMGBB_API_KEY", "")).split(",")
    if k.strip()
]

# --- Media URLs ---
_DEFAULT_PHOTO = "https://telegra.ph/file/900f153e2524317309612.jpg"
START_MEDIA: list[str] = _parse_str_list(
    os.getenv("START_MEDIA", ""),
    [os.getenv("PHOTO_URL_1", _DEFAULT_PHOTO)],
)
PHOTO_URL: list[str] = _parse_str_list(
    os.getenv("PHOTO_URL", ""),
    [
        u
        for u in (
            os.getenv("PHOTO_URL_1", "").strip(),
            os.getenv("PHOTO_URL_2", "").strip(),
        )
        if u
    ]
    or [_DEFAULT_PHOTO],
)
STATS_IMG: list[str] = _parse_str_list(
    os.getenv("STATS_IMG", ""),
    [PHOTO_URL[0]],
)
