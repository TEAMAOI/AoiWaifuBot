from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from aoiwaifu.unit.aoi_inline import get_all_characters
from aoiwaifu import app

@app.on_message(filters.command('total'))
async def total_characters(client: Client, message: Message):
    lang = await get_effective_lang(message)
    try:
        all_characters = await get_all_characters()
        unique_characters = len({char['id']: char for char in all_characters if 'id' in char})
        await message.reply_text(tr(f'📊 <b>Total Characters in Bot:</b> <code>{unique_characters}</code>', lang), parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply_text(tr(f'❌ Error getting character count: {str(e)}', lang))
