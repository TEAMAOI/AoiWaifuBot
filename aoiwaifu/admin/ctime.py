from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t
from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus
from aoiwaifu import group_user_totals_collection, group_ctimes, OWNER_ID, app, x, get_chat_lang, t

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """
    Check if the user is an admin or owner of the chat.
    Bypasses check if user_id matches ADMIN_ID.
    Returns True if the user is an admin, owner, or matches ADMIN_ID, False otherwise.
    """
    if user_id == x:
        return True
        
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.on_message(filters.command("ctime") & filters.group)
async def set_ctime(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Bot owner bypasses admin check
    if user_id == OWNER_ID:
        is_owner = True
        is_admin_user = False  # Not needed, but for clarity
    else:
        is_owner = False
        is_admin_user = await is_admin(client, chat_id, user_id)

    lang = await get_chat_lang(chat_id)
    if not (is_owner or is_admin_user):
        await message.reply(t("ctime_admin_only", lang))
        return

    # Parse command argument
    try:
        ctime = int(message.command[1])
    except (IndexError, ValueError):
        await message.reply(t("ctime_usage", lang))
        return

    # Validate ctime based on permissions
    if is_owner:
        if not 1 <= ctime <= 200:
            await message.reply(t("ctime_owner_range", lang))
            return
    else:
        if not 80 <= ctime <= 200:
            await message.reply(t("ctime_admin_range", lang))
            return

    # Update ctime in MongoDB
    await group_user_totals_collection.update_one(
        {"group_id": str(chat_id)},
        {"$set": {"ctime": ctime}},
        upsert=True
    )

    group_ctimes[str(chat_id)] = ctime
    await message.reply(t("ctime_success", lang, ctime=ctime))
