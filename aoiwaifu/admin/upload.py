"""Admin character upload commands (/gupload, /upload, /u, /find) — ImgBB only."""

import asyncio
import os
import requests
from pyrogram import filters

from aoiwaifu import (
    CHARA_CHANNEL_ID,
    IMGBB_API_KEYS,
    ZYRO,
    collection,
    rarity_map,
    require_power,
)
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

WRONG_FORMAT_TEXT = (
    "Wrong ❌ format... eg. /gupload reply to photo muzan-kibutsuji Demon-slayer 3\n\n"
    "Format: /gupload <character-name> <anime-name> <rarity-number>\n\n"
    "Rarity numbers:\n"
    + "\n".join(f"{number}. {name}" for number, name in rarity_map.items())
)


async def find():
    cursor = collection.find().sort("id", 1)
    ids = []
    async for doc in cursor:
        if "id" in doc:
            try:
                ids.append(int(doc["id"]))
            except (TypeError, ValueError):
                continue
    ids.sort()
    for i in range(1, len(ids) + 2):
        if i not in ids:
            return str(i).zfill(2)
    return str(len(ids) + 1).zfill(2)


async def find_available_id():
    return await find()


def upload_to_imgbb(file_path: str) -> str:
    """Upload a local image file to ImgBB using configured API key(s)."""
    if not file_path or not os.path.isfile(file_path):
        raise Exception(f"Invalid file path: {file_path}")

    api_keys = list(IMGBB_API_KEYS) or [
        key.strip()
        for key in os.getenv("IMGBB_API_KEYS", os.getenv("IMGBB_API_KEY", "")).split(",")
        if key.strip()
    ]
    if not api_keys:
        raise Exception(
            "ImgBB API key is not configured. Set IMGBB_API_KEYS or IMGBB_API_KEY in your environment."
        )

    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            with open(file_path, "rb") as image_file:
                response = requests.post(
                    IMGBB_UPLOAD_URL,
                    data={"key": api_key},
                    files={"image": image_file},
                    timeout=60,
                )
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("url"):
                    return data["data"]["url"]
                err_msg = data.get("error", {}).get("message", "Unexpected ImgBB response")
                errors.append(f"key #{index}: {err_msg}")
            else:
                errors.append(f"key #{index}: HTTP {response.status_code} - {response.text[:200]}")
        except Exception as exc:
            errors.append(f"key #{index}: {str(exc)[:200]}")

    raise Exception("ImgBB upload failed: " + " | ".join(errors))


_upload_lock = None


def _get_upload_lock() -> asyncio.Lock:
    global _upload_lock
    if _upload_lock is None:
        _upload_lock = asyncio.Lock()
    return _upload_lock


@ZYRO.on_message(filters.command(["find"]))
@require_power("add_character")
async def find_next_id_cmd(client, message):
    lang = await get_effective_lang(message)
    available_id = await find()
    await message.reply_text(tr(f"Next available character ID: `{available_id}`", lang))


@ZYRO.on_message(filters.command(["gupload", "u", "upload"]))
@require_power("add_character")
async def ul_main(client, message):
    lang = await get_effective_lang(message)
    if _get_upload_lock().locked():
        await message.reply_text(
            tr("Another upload is in progress. Please wait until it is completed.", lang)
        )
        return

    async with _get_upload_lock():
        reply = message.reply_to_message
        if not reply or not (reply.photo or reply.document):
            await message.reply_text(
                tr("Please reply to a photo or image document (ImgBB only).", lang)
            )
            return

        if reply.document:
            mime = getattr(reply.document, "mime_type", "") or ""
            if not mime.startswith("image/"):
                await message.reply_text(
                    tr("Only image files are supported for ImgBB upload.", lang)
                )
                return

        args = message.text.split()
        if len(args) != 4:
            await message.reply_text(tr(WRONG_FORMAT_TEXT, lang))
            return

        character_name = args[1].replace("-", " ").title()
        anime = args[2].replace("-", " ").title()
        try:
            rarity = int(args[3])
        except ValueError:
            await message.reply_text(tr(WRONG_FORMAT_TEXT, lang))
            return

        if rarity not in rarity_map:
            await message.reply_text(
                tr(f"Invalid rarity value. Choose a number from 1 to {len(rarity_map)}.", lang)
            )
            return

        rarity_text = rarity_map[rarity]
        available_id = await find_available_id()
        processing_message = await message.reply(tr("⏳ Uploading image to ImgBB...", lang))
        path = await reply.download()

        try:
            file_url = await asyncio.to_thread(upload_to_imgbb, path)
            character = {
                "name": character_name,
                "anime": anime,
                "rarity": rarity_text,
                "id": available_id,
                "img_url": file_url,
            }

            if CHARA_CHANNEL_ID:
                await client.send_photo(
                    chat_id=CHARA_CHANNEL_ID,
                    photo=file_url,
                    caption=tr(
                        f"Character Name: {character_name}\n"
                        f"Anime Name: {anime}\n"
                        f"Rarity: {rarity_text}\n"
                        f"ID: {available_id}\n"
                        f"Added by [{message.from_user.first_name}](tg://user?id={message.from_user.id})",
                        lang,
                    ),
                )

            await collection.insert_one(character)
            await processing_message.edit_text(
                tr(
                    f"✅ Character added!\n"
                    f"➲ Added by: [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n"
                    f"➥ Name: {character_name}\n"
                    f"➥ Anime: {anime}\n"
                    f"➥ Character ID: {available_id}\n"
                    f"➥ Rarity: {rarity_text}",
                    lang,
                )
            )
        except Exception as e:
            await processing_message.edit_text(
                tr(f"❌ Character Upload Unsuccessful.\nError: {str(e)}", lang)
            )
        finally:
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
