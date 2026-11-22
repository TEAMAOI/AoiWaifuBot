"""User character redeem command (/redeem)."""

from pymongo import ReturnDocument
from pyrogram import enums, filters

from aoiwaifu import ZYRO as app, collection, db, user_collection
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

redeem_collection = db["redeem_codes"]
redeem_locks = set()


@app.on_message(filters.command("redeem"))
async def redeem_character(client, message):
    lang = await get_effective_lang(message)
    args = message.command
    if len(args) < 2:
        await message.reply_text(
            tr("Usage: <code>/redeem &lt;code&gt;</code>", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    redeem_code = args[1].strip()
    user_id = message.from_user.id
    if user_id in redeem_locks:
        await message.reply_text(
            tr("⏳ Your redeem request is already processing. Please wait!", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    redeem_locks.add(user_id)
    try:
        redeem_data = await redeem_collection.find_one({"code": redeem_code})
        if not redeem_data:
            await message.reply_text(
                tr("❌ Invalid or expired redeem code.", lang),
                parse_mode=enums.ParseMode.HTML,
            )
            return
        if user_id in redeem_data.get("redeemed_by", []):
            await message.reply_text(
                tr("❌ You have already redeemed this code.", lang),
                parse_mode=enums.ParseMode.HTML,
            )
            return
        if len(redeem_data.get("redeemed_by", [])) >= redeem_data.get("redeem_limit", 0):
            await message.reply_text(
                tr("❌ This redeem code has reached its limit.", lang),
                parse_mode=enums.ParseMode.HTML,
            )
            return

        character = await collection.find_one({"id": redeem_data["character_id"]})
        if not character:
            await message.reply_text(tr("❌ Character not found.", lang), parse_mode=enums.ParseMode.HTML)
            return

        claimed = await redeem_collection.find_one_and_update(
            {
                "code": redeem_code,
                "redeemed_by": {"$ne": user_id},
                "$expr": {"$lt": [{"$size": "$redeemed_by"}, "$redeem_limit"]},
            },
            {"$push": {"redeemed_by": user_id}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            await message.reply_text(
                tr("❌ Code limit reached or already claimed!", lang),
                parse_mode=enums.ParseMode.HTML,
            )
            return

        await user_collection.update_one(
            {"id": user_id}, {"$push": {"characters": character}}, upsert=True
        )
        char_info = (
            f"🎭 <b>Character:</b> <code>{character.get('name', 'Unknown')}</code>\n"
            f"📺 <b>Anime:</b> <code>{character.get('anime', 'Unknown')}</code>\n"
            f"🌟 <b>Rarity:</b> <code>{character.get('rarity', 'Unknown')}</code>\n"
            f"🖼 <b>Image:</b> <a href=\"{character.get('img_url', '#')}\">Click Here</a>\n\n"
            f"🎉 <b>You have successfully redeemed this character!</b>"
        )
        await message.reply_text(tr(char_info, lang), parse_mode=enums.ParseMode.HTML)
    finally:
        redeem_locks.discard(user_id)
