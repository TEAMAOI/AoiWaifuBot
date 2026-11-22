"""Admin redeem code generator (/cgen)."""

import random
import string
from pyrogram import enums, filters

from aoiwaifu import ZYRO as app, collection, db, require_power
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

redeem_collection = db["redeem_codes"]


@app.on_message(filters.command("cgen"))
@require_power("VIP")
async def generate_redeem_code(client, message):
    lang = await get_effective_lang(message)
    args = message.command
    if len(args) < 3:
        await message.reply_text(
            tr("Usage: <code>/cgen &lt;character_id&gt; &lt;redeem_limit&gt;</code>", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    character_id = args[1]
    try:
        redeem_limit = int(args[2])
        if redeem_limit <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text(
            tr("❌ Invalid redeem limit. It must be a positive number.", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    character = await collection.find_one({"id": character_id})
    if not character:
        await message.reply_text(tr("❌ Character not found.", lang), parse_mode=enums.ParseMode.HTML)
        return

    redeem_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await redeem_collection.insert_one(
        {
            "code": redeem_code,
            "character_id": character_id,
            "character_name": character.get("name", "Unknown"),
            "redeem_limit": redeem_limit,
            "redeemed_by": [],
        }
    )

    char_info = (
        f"🎭 <b>Character:</b> <code>{character.get('name', 'Unknown')}</code>\n"
        f"📺 <b>Anime:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
        f"🌟 <b>Rarity:</b> <code>{character.get('rarity', 'Unknown')}</code>\n"
        f"🖼 <b>Image:</b> <a href=\"{character.get('img_url', '#')}\">Click Here</a>\n\n"
        f"🔢 <b>Redeem Limit:</b> <code>{redeem_limit}</code>\n"
        f"🎟 <b>Redeem Code:</b> <code>{redeem_code}</code>"
    )
    await message.reply_text(
        tr(f"✅ <b>Redeem code generated!</b>\n\n{char_info}", lang),
        parse_mode=enums.ParseMode.HTML,
    )
