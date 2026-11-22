# ==============================================================================
# How to Use:
#   - Purpose: Manages weighted character spawning in groups with dynamic
#     MongoDB rarity toggles, weights, rarity spawn spacing, and temp spawn logs.
#   - Components: RARITY_WEIGHTS, pick_weighted_rarity, send_image, delete_message.
#   - Roots / Routes:
#       * Triggered by: massage.py message_counter when count >= ctime
#       * DB Collections: db.anime_characters_lol, db.blocked_character_drop_groups,
#         db.bot_dynamic_settings
#   - Usage: Imported by aoiwaifu/__init__.py and massage.py.
# ==============================================================================

from aoiwaifu import *
import random
import time
import asyncio
from collections import defaultdict, deque
from telegram import Update
from telegram.ext import CallbackContext

log = "-1002155818429"
blocked_groups_collection = db["blocked_character_drop_groups"]

system_random = random.SystemRandom()

# Track recently spawned character IDs to prevent repeats across & within groups
recent_global_spawns = deque(maxlen=25)
recent_chat_spawns = defaultdict(lambda: deque(maxlen=15))


async def delete_message(chat_id, message_id, context):
    await asyncio.sleep(300)  # 5 minutes (300 seconds)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Error deleting message: {e}")


# Enabled rarity weights are normalized across the active drop pool.
RARITY_WEIGHTS = {
    "Frequent 🫧": (45.0, True),
    "Superior 🎋": (22.0, True),
    "Elite 🪸": (13.0, True),
    "Pookie 🐣": (6.0, True),
    "Majestic 👑": (4.5, True),
    "Mythical 🧜‍♀️": (3.2, True),
    "DIY 🎨": (2.2, True),
    "Angelic 🪄": (1.5, True),
    "Galactic 🌌": (1.0, True),
    "Phantom 🧌": (0.7, True),
    "Imaginative 🍀": (0.4, False),
    "Exclusive 🪎": (0.8, False),
    "Habitual 👘": (0.6, False),
    "Winter ☃️": (2.0, False),
    "Valentine's 💕": (2.0, False),
    "Summer 🏜️": (3.0, False),
    "Chibi 🎀": (0.3, True),
    "Cosplay 🗿": (0.2, True),
    "Rainy 🌧️": (2.0, False),
    "Seasonal 🍁": (2.0, False),
    "Diwali 🪔": (2.0, False),
    "Censored 💋": (0.0, False),
}


def pick_weighted_rarity(rarities_list: list[str]) -> str:
    """Strictly selects a rarity based on exact cumulative percentage weights."""
    weights = [max(0.01, float(RARITY_WEIGHTS.get(r, (1.0, True))[0])) for r in rarities_list]
    total_weight = sum(weights)
    if total_weight <= 0:
        return rarities_list[0]
    roll = system_random.uniform(0, total_weight)
    cumulative = 0.0
    for rarity, weight in zip(rarities_list, weights):
        cumulative += weight
        if roll <= cumulative:
            return rarity
    return rarities_list[0]


async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    chat_title = getattr(update.effective_chat, "title", None) or f"Group {chat_id}"

    # Ensure dynamic MongoDB settings are loaded
