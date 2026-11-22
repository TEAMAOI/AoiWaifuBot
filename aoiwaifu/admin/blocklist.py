"""Admin user blocklist commands (/blocklist, /removeblocklist)."""

from datetime import datetime, timezone
from pyrogram import enums, filters
from pyrogram.types import Message

from aoiwaifu import OWNER_ID, app, db, require_power
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

user_blocklist_collection = db["user_blocklist"]


async def is_user_blocklisted(user_id: int) -> bool:
    """Return whether a Telegram user ID is on the user blocklist."""
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    if uid <= 0:
        return False
    return (
        await user_blocklist_collection.find_one(
            {"$or": [{"_id": uid}, {"_id": str(uid)}, {"user_id": uid}, {"user_id": str(uid)}]},
            {"_id": 1},
        )
        is not None
    )


async def get_blocklisted_id_variants() -> list:
    """Return integer and string variants so older mixed-type IDs are filtered too."""
    docs = await user_blocklist_collection.find({}, {"_id": 1, "user_id": 1}).to_list(length=None)
    values = set()
    for doc in docs:
        raw_id = doc.get("user_id", doc.get("_id"))
        if raw_id is None:
            continue
        try:
            uid = int(raw_id)
        except (TypeError, ValueError):
            values.add(str(raw_id))
            continue
        values.add(uid)
        values.add(str(uid))
    return list(values)


def _parse_user_id(message: Message):
    if len(message.command) < 2:
        return None
    try:
        user_id = int(message.command[1])
    except (TypeError, ValueError):
        return None
    return user_id if user_id > 0 else None


@app.on_message(filters.command("blocklist"))
@require_power("VIP")
async def add_user_blocklist(client, message: Message):
    lang = await get_effective_lang(message)
    user_id = _parse_user_id(message)
    if user_id is None:
        return await message.reply_text(tr("❌ Invalid user ID.\nUsage: /blocklist user_id", lang))
    if user_id == OWNER_ID:
        return await message.reply_text(tr("❌ The bot owner cannot be blocklisted.", lang))
    if await is_user_blocklisted(user_id):
        return await message.reply_text(
            tr(f"ℹ️ User <code>{user_id}</code> is already on the blocklist.", lang),
            parse_mode=enums.ParseMode.HTML,
        )
    await user_blocklist_collection.update_one(
        {"_id": user_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "blocked_by": message.from_user.id,
                "blocked_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    await message.reply_text(
        tr(
            f"🚫 User <code>{user_id}</code> has been blocklisted.\n"
            f"They won't appear in rankings or send/receive payments, gifts, or trades.",
            lang,
        ),
        parse_mode=enums.ParseMode.HTML,
    )


@app.on_message(filters.command("removeblocklist"))
@require_power("VIP")
async def remove_user_blocklist(client, message: Message):
    lang = await get_effective_lang(message)
    user_id = _parse_user_id(message)
    if user_id is None:
        return await message.reply_text(tr("❌ Invalid user ID.\nUsage: /removeblocklist user_id", lang))
    result = await user_blocklist_collection.delete_many(
        {"$or": [{"_id": user_id}, {"_id": str(user_id)}, {"user_id": user_id}, {"user_id": str(user_id)}]}
    )
    if not result.deleted_count:
        return await message.reply_text(
            tr(f"ℹ️ User <code>{user_id}</code> is not on the blocklist.", lang),
            parse_mode=enums.ParseMode.HTML,
        )
    await message.reply_text(
        tr(f"✅ User <code>{user_id}</code> has been removed from the blocklist.", lang),
        parse_mode=enums.ParseMode.HTML,
    )
