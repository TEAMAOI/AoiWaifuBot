from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from aoiwaifu import app, collection, rarity_map2 as rarity_map
from pyrogram import Client, filters, enums
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def handle_search(client, message, query=None, page=1, is_callback=False):
    lang = await get_effective_lang(message)
    try:
        if not query:
            args = message.command
            if len(args) < 2:
                await message.reply_text(tr('Please provide a character name. Usage: /sips {character name}', lang))
                return
            query = ' '.join(args[1:]).strip()
        per_page = 10
        skip = (page - 1) * per_page
        total_characters = await collection.count_documents({'name': {'$regex': query, '$options': 'i'}})
        if total_characters == 0:
            await message.reply_text(tr(f'No characters found matching: {query}', lang))
            return
        characters = await collection.find({'name': {'$regex': query, '$options': 'i'}}).skip(skip).limit(per_page).to_list(length=per_page)
        response = f'**Total Characters Found:** {total_characters}\n\n'
        for index, character in enumerate(characters, start=1 + skip):
            rarity_emoji = rarity_map.get(character['rarity'], '❓')
            response += f"◈⌠{rarity_emoji}⌡ **{index}** {character['name']}\nAnime: {character['anime']}\nID: {character['id']}\n\n"
        keyboard = []
        navigation_buttons = []
        if page > 1:
            navigation_buttons.append(InlineKeyboardButton('⬅️ Back', callback_data=f'sips:{query}:{page - 1}'))
        if skip + per_page < total_characters:
            navigation_buttons.append(InlineKeyboardButton('➡️ Next', callback_data=f'sips:{query}:{page + 1}'))
        if navigation_buttons:
            keyboard.append(navigation_buttons)
        keyboard.append([InlineKeyboardButton('👁️ See', switch_inline_query_current_chat=f'see.{query}.{page}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        if is_callback:
            await message.edit_text(tr(response, lang), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text(tr(response, lang), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        error_message = f'Error: {str(e)}'
        if is_callback:
            await message.edit_text(tr(error_message, lang))
        else:
            await message.reply_text(tr(error_message, lang))

@app.on_message(filters.command('sips'))
async def search_characters(client, message):
    lang = await get_effective_lang(message)
    await handle_search(client, message)

@app.on_callback_query(filters.regex('^sips:(.+):(\\d+)$'))
async def handle_pagination(client, callback_query):
    lang = await get_effective_lang(callback_query)
    try:
        data = callback_query.data.split(':')
        query = data[1]
        page = int(data[2])
        await handle_search(client, callback_query.message, query=query, page=page, is_callback=True)
    except Exception as e:
        await callback_query.answer(tr(f'Error: {str(e)}', lang), show_alert=True)
