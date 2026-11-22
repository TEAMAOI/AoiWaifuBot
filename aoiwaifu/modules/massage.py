# ==============================================================================
# How to Use:
#   - Purpose: Tracks group message counts and triggers character drops
#     using per-group /ctime or dynamic MongoDB global/default message thresholds.
#   - Components: message_counter, _forward_pyrogram_message_to_ptb.
#   - Roots / Routes:
#       * Handler: Non-command group messages -> PTB message_counter
#       * DB Collections: db.group_user_totalsssssss, db.bot_dynamic_settings
#   - Usage: Loaded automatically by aoiwaifu/__main__.py.
# ==============================================================================

from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t
from aoiwaifu import *
import asyncio
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters
from pyrogram import filters as pyro_filters
import time

# Ensure Motor always resolves the currently running event loop even if only massage.py is updated
try:
    from motor.core import AgnosticClient

    AgnosticClient.get_io_loop = lambda self: asyncio.get_running_loop()
except Exception:
    pass

for _mc in (globals().get("ddw"), globals().get("backup_ddw")):
    if _mc is not None:
        try:
            _mc.get_io_loop = asyncio.get_running_loop
        except Exception:
            pass


async def message_counter(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if not chat or not user or not message:
        return

    chat_id = str(chat.id)
    user_id = user.id
    now = time.monotonic()

    # Bind the per-chat lock to the currently running event loop.
    running_loop = asyncio.get_running_loop()
    if hasattr(ddw, "io_loop") and ddw.io_loop is not running_loop:
        try:
            ddw.io_loop = running_loop
        except Exception:
            pass

    lock = locks.get(chat_id)
    if lock is None or getattr(lock, "_loop", None) not in (None, running_loop):
        lock = asyncio.Lock()
        locks[chat_id] = lock

    async with lock:
        # Check dynamic MongoDB settings for default_ctime or force_global_ctime
        default_ctime = 80
        force_ctime = 0

        if force_ctime > 0:
            ctime = force_ctime
            group_ctimes[chat_id] = ctime
        else:
            ctime = group_ctimes.get(chat_id)
            if ctime is None:
                document = await group_user_totals_collection.find_one(
                    {"group_id": chat_id},
                    {"_id": 0, "ctime": 1},
                )
                ctime = int(document.get("ctime", default_ctime)) if document else default_ctime

                if not document:
                    await group_user_totals_collection.update_one(
                        {"group_id": chat_id},
                        {"$setOnInsert": {"group_id": chat_id, "ctime": ctime}},
                        upsert=True,
                    )

                group_ctimes[chat_id] = ctime

        cooldown_end = user_cooldowns.get(user_id, 0)
        if now < cooldown_end:
            return
        if cooldown_end:
            user_cooldowns.pop(user_id, None)

        previous = last_user.get(chat_id)
        if previous and previous["user_id"] == user_id:
            previous["count"] += 1

            if previous["count"] >= 10:
                previous["count"] = 0
                last_warn = warned_users.get(user_id, 0)
                if now - last_warn >= 600:
                    user_cooldowns[user_id] = now + 600
                    warned_users[user_id] = now
                    grp_lang = await get_chat_lang(chat.id)
                    await message.reply_text(
                        t("spam_warning", grp_lang, first_name=user.first_name or "User")
                    )
                return
        else:
            last_user[chat_id] = {"user_id": user_id, "count": 1}

        count = normal_message_counts.get(chat_id, 0) + 1
        if count >= ctime:
            normal_message_counts[chat_id] = 0
            await send_image(update, context)
        else:
            normal_message_counts[chat_id] = count


ptb_message_handler = MessageHandler(
    ~filters.COMMAND,
    message_counter,
    block=True,
)
application.add_handler(ptb_message_handler)


def _pyrogram_message_to_update(message):
    """Build the minimal PTB Update needed by message_counter."""
    chat = message.chat
    user = message.from_user

    if not chat or not user:
        return None

    chat_type = getattr(chat.type, "value", str(chat.type))
    chat_data = {
        "id": chat.id,
        "type": chat_type.lower().replace("chattype.", ""),
    }

    if getattr(chat, "title", None):
        chat_data["title"] = chat.title
    if getattr(chat, "username", None):
        chat_data["username"] = chat.username

    user_data = {
        "id": user.id,
        "is_bot": bool(getattr(user, "is_bot", False)),
        "first_name": getattr(user, "first_name", None) or "User",
    }

    if getattr(user, "last_name", None):
        user_data["last_name"] = user.last_name
    if getattr(user, "username", None):
        user_data["username"] = user.username

    message_data = {
        "message_id": message.id,
        "date": int(message.date.timestamp()) if message.date else int(time.time()),
        "chat": chat_data,
        "from": user_data,
    }

    if getattr(message, "text", None):
        message_data["text"] = message.text
    elif getattr(message, "caption", None):
        message_data["caption"] = message.caption

    return Update.de_json(
        {
            "update_id": int(time.time() * 1_000_000) % 2_147_483_647,
            "message": message_data,
        },
        application.bot,
    )


@app.on_message(pyro_filters.all, group=1)
async def _forward_pyrogram_message_to_ptb(client, message):
    """Forward non-command Pyrogram messages to the PTB message counter."""
    lang = await get_effective_lang(message)
    if not getattr(message, "from_user", None):
        return

    text = getattr(message, "text", None) or getattr(message, "caption", None) or ""
    if text.startswith("/"):
        return

    update = _pyrogram_message_to_update(message)
    if update is not None:
        await application.process_update(update)
