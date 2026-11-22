from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import time
from pyrogram import filters, enums
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from aoiwaifu import app, application, sudo_users, OWNER_ID

START_TIME_PING = time.time()

def _format_uptime():
    sec = int(time.time() - START_TIME_PING)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}h {m}m {s}s"

@app.on_message(filters.command("ping"))
async def pyro_ping(client, message):
    lang = await get_effective_lang(message)
    start_time = time.time()
    msg = await message.reply_text(tr("🌸 <i>Pinging Aoi Waifu servers...</i>", lang), parse_mode=enums.ParseMode.HTML)
    elapsed_time = round((time.time() - start_time) * 1000, 2)
    uptime = _format_uptime()
    response_text = (
        f"╭━━━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐏𝐎𝐍𝐆 〕━━━╮\n\n"
        f"<blockquote>⚡ <b>Network Latency:</b> <code>{elapsed_time} ms</code>\n"
        f"⏳ <b>Uptime:</b> <code>{uptime}</code>\n"
        f"🌸 <b>Core Status:</b> <code>Optimal &amp; Operational ✦</code></blockquote>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯"
    )
    await msg.edit_text(tr(response_text, lang), parse_mode=enums.ParseMode.HTML)

async def ping(update: Update, context: CallbackContext) -> None:
    lang = await get_effective_lang(update)
    start_time = time.time()
    message = await update.message.reply_text(tr("🌸 <i>Pinging Aoi Waifu servers...</i>", lang), parse_mode="HTML")
    elapsed_time = round((time.time() - start_time) * 1000, 2)
    response_text = (
        f"╭━━━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐏𝐎𝐍𝐆 〕━━━╮\n\n"
        f"<blockquote>⚡ <b>Network Latency:</b> <code>{elapsed_time} ms</code>\n"
        f"🌸 <b>Core Status:</b> <code>Optimal &amp; Operational ✦</code></blockquote>\n"
        f"╰━━━━━━━━━━━━━━━━━━━━╯"
    )
    await message.edit_text(tr(response_text, lang), parse_mode="HTML")

application.add_handler(CommandHandler("ping", ping))
