"""User collector profile and statistics (/profile, /stats)."""

import html
from pyrogram import Client, enums, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from aoiwaifu import STATS_IMG, app, collection, rarity_map, rarity_map2, user_collection
from aoiwaifu.admin.blocklist import get_blocklisted_id_variants, is_user_blocklisted
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr


async def get_user_stats(user_id: int, username: str = "", first_name: str = "Collector"):
    """Fetch complete Waifu Collector profile data for a user."""
    user_doc = await user_collection.find_one({"id": user_id}) or {}
    balance = int(user_doc.get("balance") or 0)
    tokens = int(user_doc.get("tokens") or 0)
    raw_first_name = str(user_doc.get("first_name") or first_name or "Collector")
    escaped_first_name = html.escape(raw_first_name)

    raw_characters = user_doc.get("characters") or []
    characters = [c for c in raw_characters if isinstance(c, dict) and c.get("id") is not None]
    total_characters = await collection.count_documents({})
    character_count = len(characters)
    unique_character_count = len({str(c.get("id")) for c in characters})
    progress_percentage = min(
        100.0, (unique_character_count / total_characters * 100.0) if total_characters > 0 else 0.0
    )

    progress_bar_length = 10
    filled_slots = min(progress_bar_length, int(progress_percentage / 100.0 * progress_bar_length))
    progress_bar = "█" * filled_slots + "□" * (progress_bar_length - filled_slots)

    blocked_ids = await get_blocklisted_id_variants()
    user_is_blocklisted = await is_user_blocklisted(user_id)
    cursor = user_collection.find({"id": {"$nin": blocked_ids}}, {"_id": 0, "id": 1, "characters": 1})
    all_users = await cursor.to_list(length=None)
    all_users.sort(
        key=lambda x: len(x.get("characters") or []) if isinstance(x.get("characters"), list) else 0,
        reverse=True,
    )
    total_users = len(all_users)
    rank = (
        None
        if user_is_blocklisted
        else next((i + 1 for i, u in enumerate(all_users) if str(u.get("id")) == str(user_id)), None)
    )

    rarity_counts = {rarity: 0 for rarity in rarity_map.values()}
    for char in characters:
        rarity = char.get("rarity")
        if rarity in rarity_counts:
            rarity_counts[rarity] += 1

    # Pick user's favorite character photo if available, else first character photo, else STATS_IMG
    fav_photo = None
    favorites = user_doc.get("favorites") or []
    if favorites:
        fav_id = str(favorites[0])
        fav_char = next((c for c in characters if str(c.get("id")) == fav_id and c.get("img_url")), None)
        if fav_char:
            fav_photo = fav_char["img_url"]
    if not fav_photo:
        first_img = next((c.get("img_url") for c in characters if c.get("img_url")), None)
        fav_photo = first_img or STATS_IMG[0]

    return (
        {
            "user_id": user_id,
            "first_name": escaped_first_name,
            "balance": balance,
            "tokens": tokens,
            "character_count": character_count,
            "unique_character_count": unique_character_count,
            "total_characters": total_characters,
            "progress_percentage": progress_percentage,
            "progress_bar": progress_bar,
            "rank": rank,
            "total_users": total_users,
            "rarity_counts": rarity_counts,
            "photo_url": fav_photo,
        },
        None,
    )


def _build_profile_view(stats: dict, lang: str = "en") -> tuple[str, InlineKeyboardMarkup]:
    """Single source of truth for /profile and profile_refresh caption & keyboard."""
    global_rank = f"#{stats['rank']} / {stats['total_users']}" if stats.get("rank") else "Unranked"
    caption = (
        f"╭━━━〔 🌸 𝐂𝐎𝐋𝐋𝐄𝐂𝐓𝐎𝐑 𝐏𝐑𝐎𝐅𝐈𝐋𝐄 〕━━━╮\n\n"
        f"<blockquote>👤 <b>Name:</b> {stats['first_name']}\n"
        f"🆔 <b>User ID:</b> <code>{stats['user_id']}</code>\n"
        f"🏆 <b>Global Rank:</b> <code>{global_rank}</code>\n\n"
        f"💰 <b>Coins:</b> <code>{stats['balance']:,}</code>\n"
        f"🪙 <b>Tokens:</b> <code>{stats['tokens']:,}</code>\n\n"
        f"🎴 <b>Total Waifus:</b> <code>{stats['character_count']:,}</code>\n"
        f"✨ <b>Unique:</b> <code>{stats['unique_character_count']:,} / {stats['total_characters']:,}</code>\n"
        f"📊 <b>Progress:</b> <code>{stats['progress_bar']}</code> ({stats['progress_percentage']:.1f}%)"
    )

    non_zero_rarities = [(rarity, count) for rarity, count in stats["rarity_counts"].items() if count > 0]
    if non_zero_rarities:
        caption += "\n\n💎 <b>RARITY BREAKDOWN</b>\n"
        for idx, (rarity, count) in enumerate(non_zero_rarities):
            branch = "└" if idx == len(non_zero_rarities) - 1 else "├"
            emoji = rarity_map2.get(rarity, "❍")
            caption += f"{branch} {emoji} {html.escape(str(rarity))}: <b>{count:,}</b>\n"

    caption += "</blockquote>\n╰━━━━━━━━━━━━━━━━━━━━━━╯"

    uid = stats["user_id"]
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🌸 Harem ({stats['character_count']})",
                    switch_inline_query_current_chat=f"collection.{uid}",
                ),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"profile_refresh:{uid}"),
            ]
        ]
    )
    return tr(caption, lang), keyboard


async def _resolve_target_user(client: Client, message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return (u.id, u.username or "", u.first_name or "Collector")
    if len(message.command) > 1:
        arg = message.command[1].strip()
        if arg.lstrip("-").isdigit():
            uid = int(arg)
            db_user = await user_collection.find_one({"id": uid})
            if db_user:
                return (uid, db_user.get("username") or "", db_user.get("first_name") or "Collector")
            try:
                tg_u = await client.get_users(uid)
                return (tg_u.id, tg_u.username or "", tg_u.first_name or "Collector")
            except Exception:
                return (uid, "", f"User {uid}")
        else:
            clean_uname = arg.lstrip("@")
            db_user = await user_collection.find_one(
                {"username": {"$regex": f"^{clean_uname}$", "$options": "i"}}
            )
            if db_user and db_user.get("id"):
                return (
                    int(db_user["id"]),
                    db_user.get("username") or clean_uname,
                    db_user.get("first_name") or clean_uname,
                )
            try:
                tg_u = await client.get_users(arg)
                return (tg_u.id, tg_u.username or "", tg_u.first_name or "Collector")
            except Exception:
                pass
    u = message.from_user
    return (u.id, u.username or "", u.first_name or "Collector")


@app.on_message(filters.command(["profile", "stats"]))
async def profile_and_stats_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    target_user_id, target_username, target_first_name = await _resolve_target_user(client, message)
    stats, error = await get_user_stats(
        target_user_id, username=target_username, first_name=target_first_name
    )
    if error or not stats:
        await message.reply_text(tr(error or "Unable to load profile.", lang), parse_mode=enums.ParseMode.HTML)
        return

    caption, keyboard = _build_profile_view(stats, lang=lang)
    try:
        await message.reply_photo(
            photo=stats["photo_url"],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML,
        )
    except Exception:
        await message.reply_photo(
            photo=STATS_IMG[0],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.HTML,
        )


@app.on_callback_query(filters.regex(r"^profile_refresh:(\d+)$"))
async def profile_refresh_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    try:
        target_user_id = int(callback_query.matches[0].group(1))
        await callback_query.answer(tr("🔄 Refreshing profile...", lang))
        stats, error = await get_user_stats(target_user_id)
        if error or not stats:
            return
        caption, keyboard = _build_profile_view(stats, lang=lang)
        try:
            await callback_query.message.edit_caption(
                caption=caption,
                reply_markup=keyboard,
                parse_mode=enums.ParseMode.HTML,
            )
        except Exception:
            pass
    except Exception:
        pass
