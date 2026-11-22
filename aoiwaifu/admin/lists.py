"""Admin user/group export commands (/list, /groups)."""

import os
from pyrogram import Client, filters
from pyrogram.types import Message

from aoiwaifu import app, sudo_users as SUDO_USERS, top_global_groups_collection, user_collection
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr


@app.on_message(filters.command("list"))
async def send_users_document(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if str(message.from_user.id) not in SUDO_USERS:
        await message.reply_text(tr("Only for Sudo users.", lang))
        return

    lines = []
    async for doc in user_collection.find({}, {"first_name": 1, "id": 1}):
        lines.append(f"{doc.get('first_name', 'Unknown')} ({doc.get('id', '?')})")

    file_path = "users.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        await message.reply_document(document=file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.on_message(filters.command("groups"))
async def send_groups_document(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if str(message.from_user.id) not in SUDO_USERS:
        await message.reply_text(tr("Only for Sudo users.", lang))
        return

    lines = []
    async for doc in top_global_groups_collection.find({}, {"group_name": 1, "chat_id": 1}):
        lines.append(f"{doc.get('group_name', 'Unknown')} ({doc.get('chat_id', '?')})")

    file_path = "groups.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    try:
        await message.reply_document(document=file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
