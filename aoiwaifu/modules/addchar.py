"""User character submission request command (/addchar) — ImgBB only."""

import asyncio
import os
from bson.objectid import ObjectId
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from aoiwaifu import CHARA_CHANNEL_ID, app as ZYRO, collection, db, rarity_map, require_power
from aoiwaifu.admin.upload import find_available_id, upload_to_imgbb
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

WRONG_FORMAT_TEXT = (
    "Wrong ❌ format...\n"
    "eg. /addchar muzan-kibutsuji Demon-slayer\n\n"
    "Format: /addchar <character-name> <anime-name>"
)
upload_collection = db.uploads


@ZYRO.on_message(filters.command(["addchar"]))
async def request_upload(client, message):
    lang = await get_effective_lang(message)
    reply = message.reply_to_message
    if not reply or not (reply.photo or reply.document):
        return await message.reply_text(tr("Please reply to a photo or image document.", lang))

    if reply.document:
        mime = getattr(reply.document, "mime_type", "") or ""
        if not mime.startswith("image/"):
            return await message.reply_text(tr("Only image files are supported.", lang))

    args = message.text.split()
    if len(args) != 3:
        return await message.reply_text(tr(WRONG_FORMAT_TEXT, lang))

    processing_message = await message.reply(tr("⏳ Processing...", lang))
    character_name = args[1].replace("-", " ").title()
    anime = args[2].replace("-", " ").title()
    path = await reply.download()
    try:
        img_url = await asyncio.to_thread(upload_to_imgbb, path)
        upload_data = {
            "name": character_name,
            "anime": anime,
            "img_url": img_url,
            "requested_by": {
                "id": message.from_user.id,
                "name": message.from_user.first_name,
            },
        }
        result = await upload_collection.insert_one(upload_data)

        rarity_buttons = []
        rarity_items = list(rarity_map.items())
        for i in range(0, len(rarity_items), 4):
            row = [
                InlineKeyboardButton(text=value, callback_data=f"rarity_{result.inserted_id}_{key}")
                for key, value in rarity_items[i : i + 4]
            ]
            rarity_buttons.append(row)
        rarity_buttons.append(
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{result.inserted_id}")]
        )
        keyboard = InlineKeyboardMarkup(rarity_buttons)

        await client.send_photo(
            chat_id=CHARA_CHANNEL_ID,
            photo=img_url,
            caption=tr(
                f"#pending\n\n**New Character Upload Request**\n"
                f"Character Name: {character_name}\n"
                f"Anime Name: {anime}\n"
                f"Requested by [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n\n"
                f"Select a rarity to upload the character or cancel the request:",
                lang,
            ),
            reply_markup=keyboard,
        )
        await processing_message.edit(tr("✅ Your request has been submitted successfully!", lang))
    except Exception as e:
        await processing_message.edit(tr(f"❌ Request upload failed.\nError: {str(e)}", lang))
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


@ZYRO.on_callback_query(filters.regex(r"^rarity_([0-9a-fA-F]+)_(\d+)$"))
@require_power("add_character")
async def approve_upload(client, callback_query):
    lang = await get_effective_lang(callback_query)
    upload_id = callback_query.matches[0].group(1)
    rarity_key = int(callback_query.matches[0].group(2))
    upload_data = await upload_collection.find_one({"_id": ObjectId(upload_id)})
    if not upload_data:
        return await callback_query.answer(tr("Request already processed or not found.", lang), show_alert=True)

    rarity_text = rarity_map.get(rarity_key, "🟢 Common")
    available_id = await find_available_id()
    character = {
        "name": upload_data["name"],
        "anime": upload_data["anime"],
        "rarity": rarity_text,
        "id": available_id,
        "img_url": upload_data["img_url"],
    }
    await collection.insert_one(character)
    await upload_collection.delete_one({"_id": ObjectId(upload_id)})
    await callback_query.message.edit_caption(
        tr(
            f"#approved\n\nCharacter Name: {character['name']}\n"
            f"Anime Name: {character['anime']}\n"
            f"Rarity: {rarity_text}\n"
            f"ID: {available_id}\n"
            f"Approved by [{callback_query.from_user.first_name}](tg://user?id={callback_query.from_user.id})",
            lang,
        )
    )
    await callback_query.answer(tr("✅ Character approved and added!", lang))


@ZYRO.on_callback_query(filters.regex(r"^cancel_([0-9a-fA-F]+)$"))
@require_power("add_character")
async def cancel_upload(client, callback_query):
    lang = await get_effective_lang(callback_query)
    upload_id = callback_query.matches[0].group(1)
    await upload_collection.delete_one({"_id": ObjectId(upload_id)})
    await callback_query.message.edit_caption(
        tr(
            f"#cancelled\n\nCancelled by [{callback_query.from_user.first_name}](tg://user?id={callback_query.from_user.id})",
            lang,
        )
    )
    await callback_query.answer(tr("❌ Request cancelled.", lang))
