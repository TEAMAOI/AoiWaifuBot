"""AoiWaifu Bot — Core initialization, clients, database handles, and shared state."""

import asyncio
import logging

# Ensure a single main event loop is initialized before Pyrogram/Kurigram, Motor, or PTB.
try:
    mongo_loop = asyncio.get_running_loop()
except RuntimeError:
    try:
        mongo_loop = asyncio.get_event_loop()
    except RuntimeError:
        mongo_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(mongo_loop)


def _get_current_io_loop():
    """Always return the currently running event loop for Motor futures."""
    try:
        running_loop = asyncio.get_running_loop()
        for client_name in ("ddw", "backup_ddw"):
            client_obj = globals().get(client_name)
            if client_obj is not None and hasattr(client_obj, "io_loop") and client_obj.io_loop is not running_loop:
                try:
                    client_obj.io_loop = running_loop
                except Exception:
                    pass
        return running_loop
    except RuntimeError:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return mongo_loop


try:
    from motor.core import AgnosticClient

    AgnosticClient.get_io_loop = lambda self: _get_current_io_loop()
except Exception:
    pass

from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, enums, filters as f
from telegram.ext import Application

from aoiwaifu.config import (
    API_ID,
    API_HASH,
    TOKEN,
    MONGO_URL,
    BACKUP_MONGO_URL,
    DB_NAME,
    OWNER_ID,
    OWNER_USERNAME,
    SUDO,
    GLOG,
    CHARA_CHANNEL_ID,
    SUPPORT_CHAT_ID,
    SUPPORT_CHAT,
    UPDATE_CHAT,
    IMGBB_API_KEYS,
    START_MEDIA,
    PHOTO_URL,
    STATS_IMG,
)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        logging.FileHandler("log.txt"),
        logging.StreamHandler(),
    ],
)

logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Backward-compatible aliases for config values
api_id = API_ID
api_hash = API_HASH
mongo_url = MONGO_URL
backup_mongo_url = BACKUP_MONGO_URL

# --- Bot Clients ---
command_filter = f.create(lambda _, __, message: bool(message.text and message.text.startswith("/")))
application = Application.builder().token(TOKEN).build()
AOI = Client(
    "AoiWaifu",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TOKEN,
    parse_mode=enums.ParseMode.DISABLED,
)
ZYRO = AOI
app = AOI
bot = AOI

if getattr(AOI, "loop", None) is not None and isinstance(AOI.loop, asyncio.AbstractEventLoop):
    mongo_loop = AOI.loop
    asyncio.set_event_loop(mongo_loop)


# --- MongoDB Setup ---
def _create_motor_client(uri: str, **kwargs):
    try:
        client = AsyncIOMotorClient(uri, io_loop=mongo_loop, **kwargs)
    except TypeError:
        client = AsyncIOMotorClient(uri)
    try:
        client.get_io_loop = _get_current_io_loop
    except Exception:
        pass
    return client


ddw = _create_motor_client(
    MONGO_URL,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    maxPoolSize=50,
)
backup_ddw = _create_motor_client(
    BACKUP_MONGO_URL,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    maxPoolSize=10,
)

db = ddw[DB_NAME]
collection = db["anime_characters_lol"]
user_totals_collection = db["user_totals_lmaoooo"]
user_collection = db["user_collection_lmaoooo"]
group_user_totals_collection = db["group_user_totalsssssss"]
top_global_groups_collection = db["top_global_groups"]
pm_users = db["total_pm_users"]
discounts_collection = db["discounts"]

# --- Runtime State ---
locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
last_user = {}
warned_users = {}
user_cooldowns = {}
user_guess_progress = {}
normal_message_counts = {}
group_ctimes = {}

# --- Unit Helpers ---
from aoiwaifu.unit.aoi_lang import *
from aoiwaifu.unit.aoi_ban import *
from aoiwaifu.unit.aoi_sudo import *
from aoiwaifu.unit.aoi_react import *
from aoiwaifu.unit.aoi_log import *
from aoiwaifu.unit.aoi_send_img import *
from aoiwaifu.unit.aoi_rarity import *
from aoiwaifu.unit.aoi_parse_fix import install_parse_mode_guard, SudoUsersHybrid

group_langs = chat_langs_cache
user_langs = user_langs_cache


async def PLOG(text: str):
    if GLOG:
        await app.send_message(chat_id=GLOG, text=text)


install_parse_mode_guard()
sudo_users = SudoUsersHybrid(db["sudo_users"], SUDO, OWNER_ID)
