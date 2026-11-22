"""Character catching commands (/guess, /protecc, /collect, /grab, /hunt)."""

import asyncio
from datetime import datetime
from html import escape
import time
from pyrogram import Client, enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from aoiwaifu import (
    app,
    check_cooldown,
    db,
    first_correct_guesses,
    get_remaining_cooldown,
    last_characters,
    react_to_message,
    top_global_groups_collection,
    user_collection,
    user_guess_progress,
)
from aoiwaifu.unit.aoi_lang import get_effective_lang, t, tr


@app.on_message(filters.command(["guess", "protecc", "collect", "grab", "hunt"]))
async def guess(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = await get_effective_lang(message, chat_id=chat_id, user_id=user_id)

    if await db["blocked_character_drop_groups"].find_one({"_id": chat_id}):
        await message.reply_text(t("guess_disabled_group", lang))
        return

    today = datetime.utcnow().date()
    if await check_cooldown(user_id):
        remaining_time = await get_remaining_cooldown(user_id)
        await message.reply_text(t("guess_cooldown", lang, remaining_time=remaining_time))
        return

    if (
        "name" not in last_characters.get(chat_id, {})
        or chat_id not in last_characters
        or chat_id in first_correct_guesses
    ):
        await message.reply_text(
            tr("❌ No active character to catch right now. Keep chatting in the group!", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    if last_characters[chat_id].get("ranaway", False):
        await message.reply_text(t("guess_ran_away", lang))
        return

    guess_text = " ".join(message.command[1:]).lower() if len(message.command) > 1 else ""
    if "()" in guess_text or "&" in guess_text.lower():
        await message.reply_text(t("guess_invalid_chars", lang))
        return

    name_parts = last_characters[chat_id]["name"].lower().split()
    if sorted(name_parts) == sorted(guess_text.split()) or any(part == guess_text for part in name_parts):
        first_correct_guesses[chat_id] = user_id
        for task in asyncio.all_tasks():
            if task.get_name() == f"expire_session_{chat_id}":
                task.cancel()
                break

        timestamp = last_characters[chat_id].get("timestamp")
        time_taken_str = f"{int(time.time() - timestamp)} seconds" if timestamp else "Unknown time"

        if user_id not in user_guess_progress or user_guess_progress[user_id]["date"] != today:
            user_guess_progress[user_id] = {"date": today, "count": 0}
        user_guess_progress[user_id]["count"] += 1

        user = await user_collection.find_one({"id": user_id})
        if user:
            update_fields = {}
            if message.from_user.username != user.get("username"):
                update_fields["username"] = message.from_user.username
            if message.from_user.first_name != user.get("first_name"):
                update_fields["first_name"] = message.from_user.first_name
            if update_fields:
                await user_collection.update_one({"id": user_id}, {"$set": update_fields})
            await user_collection.update_one(
                {"id": user_id},
                {"$push": {"characters": last_characters[chat_id]}, "$inc": {"balance": 40}},
            )
        else:
            await user_collection.insert_one(
                {
                    "id": user_id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "balance": 40,
                    "tokens": 0,
                    "characters": [last_characters[chat_id]],
                }
            )

        if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
            group_name = message.chat.title or f"Group_{chat_id}"
            await top_global_groups_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {"group_name": group_name}, "$inc": {"count": 1}},
                upsert=True,
            )

        await react_to_message(chat_id, message.id)
        updated_user = await user_collection.find_one({"id": user_id}, {"balance": 1})
        new_balance = int((updated_user or {}).get("balance", 40) or 40)

        char = last_characters[chat_id]
        caption = (
            f"✨ <b><a href='tg://user?id={user_id}'>{escape(message.from_user.first_name or 'Player')}</a></b> "
            f"caught a character!\n\n"
            f"<blockquote>💮 <b>Name:</b> {escape(str(char['name']))}\n"
            f"🌸 <b>Anime:</b> {escape(str(char['anime']))}\n"
            f"💎 <b>Rarity:</b> {escape(str(char['rarity']))}\n"
            f"⏱ <b>Time:</b> {time_taken_str}\n"
            f"💰 <b>Reward:</b> +40 coins (Total: {new_balance:,})</blockquote>"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(t("btn_view_in_harem", lang), switch_inline_query_current_chat=f"collection.{user_id}")]]
        )
        await message.reply_text(tr(caption, lang), parse_mode=enums.ParseMode.HTML, reply_markup=keyboard)
    else:
        message_id = last_characters[chat_id].get("message_id")
        incorrect_text = t("guess_incorrect", lang)
        if message_id:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(t("btn_view_media_again", lang), url=f"https://t.me/c/{str(chat_id)[4:]}/{message_id}")]]
            )
            await message.reply_text(tr(incorrect_text, lang), reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text(tr(incorrect_text, lang), parse_mode=enums.ParseMode.HTML)
