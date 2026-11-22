import os
import requests
from aoiwaifu import TOKEN, OWNER_ID, OWNER_USERNAME

CHAT_ID = OWNER_ID
BOT_NAME = "Aoi Waifu"
IMAGE_URL = "https://files.catbox.moe/7ccoub.jpg"

def send_start_message():
    owner_str = f"@{(OWNER_USERNAME or 'AoiMrZyro').lstrip('@')}"
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    caption = (
        f"🌸 *Aoi Waifu is now Online & Operational\\!*\n\n"
        f"👑 *Owner ID:* `{OWNER_ID}`\n"
        f"🚀 *Status:* All modules loaded successfully\\!"
    )
    payload = {
        "chat_id": CHAT_ID,
        "photo": IMAGE_URL,
        "caption": caption,
        "parse_mode": "MarkdownV2"  # Use MarkdownV2 for proper escaping
    }
    
    response = None
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()  # Raise exception for HTTP errors
        print("Start message sent successfully.")
    except requests.exceptions.RequestException as e:
        if response is not None:
            print(f"Error response: {response.text}")
        print(f"Failed to send start message: {e}")

