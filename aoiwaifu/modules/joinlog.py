from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from aoiwaifu import user_collection, app, db, GLOG

game_active_groups_col = db["game_active_groups"]


async def send_log_message(chat_id: int, message: str):
    """Send a log message to the specified chat."""
    await app.send_message(chat_id=chat_id, text=message)


@app.on_message(filters.new_chat_members)
async def on_new_chat_members(client: Client, message: Message):
    """Handle new chat members joining the chat."""
    lang = await get_effective_lang(message)
    bot_user = await client.get_me()

    # Check if the bot is one of the new members
    if bot_user.id in [user.id for user in message.new_chat_members]:
        added_by = message.from_user.mention if message.from_user else "ᴜɴᴋɴᴏᴡɴ ᴜsᴇʀ"
        chat_title = message.chat.title
        chat_id = message.chat.id
        chat_username = f"@{message.chat.username}" if message.chat.username else "ᴩʀɪᴠᴀᴛ"

        try:
            await game_active_groups_col.update_one(
                {"chat_id": int(chat_id)},
                {
                    "$set": {
                        "chat_id": int(chat_id),
                        "chat_title": chat_title or f"Chat {chat_id}",
                        "active": True,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                },
                upsert=True,
            )
        except Exception:
            pass

        # Construct the log message
        log_message = (
            f"#newgoroup\n\n"
            f"chat name : {chat_title}\n"
            f"username : {chat_username}\n"
            f"added by : {added_by}"
        )

        # Send the log message
        await send_log_message(GLOG, log_message)

        # Check if the group has less than 100 members
        chat_members_count = await client.get_chat_members_count(chat_id)
        if chat_members_count < 1:
            leave_message = (
                f"#leftgroup\n\n"
                f"chat name : {chat_title}\n"
                f"chat username : {chat_username}\n"
                f"reason : Group has less than 1 members"
            )
            await send_log_message(chat_id, leave_message)
            await client.leave_chat(chat_id)
            leave_message = (
                f"#leftgroup\n\n"
                f"chat name : {chat_title}\n"
                f"chat username : {chat_username}\n"
                f"reason : Group has less than 40 members"
            )
            await send_log_message(GLOG, leave_message)


@app.on_message(filters.left_chat_member)
async def on_left_chat_member(_, message: Message):
    """Handle the bot leaving the chat."""
    lang = await get_effective_lang(message)
    bot_user = await app.get_me()

    # Check if the bot is the one that left
    if bot_user.id == message.left_chat_member.id:
        removed_by = message.from_user.mention if message.from_user else "ᴜɴᴋɴᴏᴡɴ ᴜsᴇʀ"
        chat_title = message.chat.title
        chat_id = message.chat.id
        chat_username = f"@{message.chat.username}" if message.chat.username else "ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ"

        try:
            await game_active_groups_col.update_one(
                {"chat_id": int(chat_id)},
                {"$set": {"active": False, "updated_at": datetime.utcnow().isoformat()}},
            )
        except Exception:
            pass

        # Construct the log message
        log_message = (
            f"#leftgroup \n\n"
            f"chat name : {chat_title}\n"
            f"chat username : {chat_username}\n"
            f"remove by : {removed_by}\n"
        )

        await send_log_message(GLOG, log_message)
