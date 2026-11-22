from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from aoiwaifu import app, collection
from pyrogram import filters, enums

@app.on_message(filters.command('rarity'))
async def rarity_count(client, message):
    lang = await get_effective_lang(message)
    try:
        distinct_rarities = await collection.distinct('rarity')
        if not distinct_rarities:
            await message.reply_text(tr('⚠️ No rarities found in the database.', lang))
            return
        response_message = '✨ Character Count by Rarity ✨\n\n'
        total_count = 0
        for rarity in distinct_rarities:
            count = await collection.count_documents({'rarity': rarity})
            total_count += count
            response_message += f'◈ {rarity} — {count} character(s)\n'
        response_message += f'\n💠 Total Characters: {total_count}'
        await message.reply_text(tr(response_message, lang))
    except Exception as e:
        await message.reply_text(tr(f'⚠️ Error: {str(e)}', lang))
