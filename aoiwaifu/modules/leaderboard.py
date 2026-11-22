"""Public leaderboard and bot count commands (/TopGroups, /ctop, /st)."""

import html
import random
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from aoiwaifu import (
    PHOTO_URL,
    app,
    group_user_totals_collection,
    top_global_groups_collection,
    user_collection,
)
from aoiwaifu.admin.blocklist import get_blocklisted_id_variants
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr


@app.on_message(filters.command("TopGroups"))
async def global_leaderboard(client: Client, message: Message):
    lang = await get_effective_lang(message)
    cursor = top_global_groups_collection.aggregate(
        [
            {"$project": {"group_name": 1, "count": 1}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
    )
    leaderboard_data = await cursor.to_list(length=10)
    leaderboard_message = "<b>TOP 10 GROUPS WHO GUESSED MOST CHARACTERS</b>\n\n"
    for i, group in enumerate(leaderboard_data, start=1):
        raw_gname = str(group.get("group_name") or "Unknown")
        if len(raw_gname) > 15:
            raw_gname = raw_gname[:15] + "..."
        group_name = html.escape(raw_gname)
        count = group["count"]
        leaderboard_message += f"{i}. <b>{group_name}</b> ➾ <b>{count}</b>\n"
    photo_url = random.choice(PHOTO_URL)
    await message.reply_photo(
        photo=photo_url,
        caption=tr(leaderboard_message, lang),
        parse_mode=enums.ParseMode.HTML,
    )


@app.on_message(filters.command("ctop"))
async def ctop(client: Client, message: Message):
    lang = await get_effective_lang(message)
    chat_id = message.chat.id
    blocked_ids = await get_blocklisted_id_variants()
    blocked_docs = await user_collection.find({"id": {"$in": blocked_ids}}, {"username": 1}).to_list(length=None)
    blocked_names = {str(u.get("username") or "").lstrip("@").lower() for u in blocked_docs}

    cursor = group_user_totals_collection.aggregate(
        [
            {"$match": {"group_id": chat_id, "username": {"$nin": list(blocked_names)}}},
            {"$project": {"username": 1, "first_name": 1, "character_count": "$count"}},
            {"$sort": {"character_count": -1}},
            {"$limit": 10},
        ]
    )
    leaderboard_data = await cursor.to_list(length=10)
    leaderboard_message = "<b>TOP 10 USERS WHO GUESSED MOST CHARACTERS IN THIS GROUP</b>\n\n"
    for i, user in enumerate(leaderboard_data, start=1):
        username = user.get("username", "Unknown")
        raw_fname = str(user.get("first_name") or "Unknown")
        if len(raw_fname) > 15:
            raw_fname = raw_fname[:15] + "..."
        first_name = html.escape(raw_fname)
        character_count = user["character_count"]
        leaderboard_message += f'{i}. <a href="https://t.me/{username}"><b>{first_name}</b></a> ➾ <b>{character_count}</b>\n'
    photo_url = random.choice(PHOTO_URL)
    await message.reply_photo(
        photo=photo_url,
        caption=tr(leaderboard_message, lang),
        parse_mode=enums.ParseMode.HTML,
    )


@app.on_message(filters.command("st"))
async def stats(client: Client, message: Message):
    lang = await get_effective_lang(message)
    user_count = await user_collection.count_documents({})
    group_count = await group_user_totals_collection.distinct("group_id")
    await message.reply_text(tr(f"Total Users: {user_count}\nTotal Groups: {len(group_count)}", lang))
