from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pymongo import MongoClient
from aoiwaifu import app, user_collection

@app.on_message(filters.command('fav'))
async def fav_command(client, message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    if len(message.command) < 2:
        await message.reply_text(tr('Please provide a character ID. ❌', lang))
        return
    character_id = message.command[1]
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await message.reply_text(tr('You have not guessed any characters yet. ❌', lang))
        return
    character = next((c for c in user.get('characters', []) if isinstance(c, dict) and str(c.get('id')) == str(character_id)), None)
    if not character:
        await message.reply_text(tr('This character is not in your collection. ❌', lang))
        return
    if 'vid_url' in character:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('✅ Yes', callback_data=f'fav_yes_{character_id}_{user_id}'), InlineKeyboardButton('❎ No', callback_data='fav_no')]])
        await message.reply_video(video=character['vid_url'], caption=tr(f"Add {character['name']} to favorites?", lang), reply_markup=keyboard)
    elif 'img_url' in character:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('✅ Yes', callback_data=f'fav_yes_{character_id}_{user_id}'), InlineKeyboardButton('❎ No', callback_data='fav_no')]])
        await message.reply_photo(photo=character['img_url'], caption=tr(f"Add {character['name']} to favorites?", lang), reply_markup=keyboard)
    else:
        await message.reply_text(tr('This character has no media (image or video) associated with it. ❌', lang))

@app.on_callback_query(filters.regex('fav_yes_(.+?)_(\\d+)'))
async def fav_yes(client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    parts = callback_query.data.split('_')
    if len(parts) < 4:
        return await callback_query.answer(tr('Invalid favorite request. Please try /fav again.', lang), show_alert=True)
    character_id, user_id = (parts[2], int(parts[3]))
    if callback_query.from_user.id != user_id:
        await callback_query.answer(tr('This button is not for you! ❌', lang), show_alert=True)
        return
    user = await user_collection.find_one({'id': user_id})
    if not user:
        await callback_query.message.reply_text(tr('User not found. ❌', lang))
        return
    character = next((c for c in user.get('characters', []) if isinstance(c, dict) and str(c.get('id')) == str(character_id)), None)
    if not character:
        await callback_query.message.reply_text(tr('Character not found in your collection. ❎', lang))
        return
    user['favorites'] = [character_id]
    await user_collection.update_one({'id': user_id}, {'$set': {'favorites': user['favorites']}})
    await callback_query.message.edit_caption(tr(f"{character['name']} has been added to your favorites! ✅", lang))
    await callback_query.answer(tr('Character added to favorites. ✅', lang))

@app.on_callback_query(filters.regex('fav_no'))
async def fav_no(client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    await callback_query.message.delete()
    await callback_query.answer(tr('Action canceled.', lang))
