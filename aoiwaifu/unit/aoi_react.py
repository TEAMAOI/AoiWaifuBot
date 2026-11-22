import random
import aiohttp
from aoiwaifu import TOKEN

emojis = ["👍", "😘", "❤️", "🔥", "🥰", "🤩", "💘", "😏", "🤯", "⚡️", "🏆", "🤭", "🎉"]

async def react_to_message(chat_id, message_id):
    random_emoji = random.choice(emojis)
    url = f"https://api.telegram.org/bot{TOKEN}/setMessageReaction"
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": [{"type": "emoji", "emoji": random_emoji}]
    }
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=params) as resp:
                pass
    except Exception:
        pass
