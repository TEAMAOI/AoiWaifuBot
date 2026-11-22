from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from aoiwaifu import app, collection as character_collection, user_collection
from aoiwaifu.admin.blocklist import get_blocklisted_id_variants
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio

@app.on_message(filters.command('check'))
async def check_character(client, message):
    lang = await get_effective_lang(message)
    args = message.command
    if len(args) < 2:
        await message.reply_text(tr('Please provide a Character ID: `/check <character_id>`', lang))
        return
    character_id = args[1]
    character = await character_collection.find_one({'id': character_id})
    if not character:
        await message.reply_text(tr('Character not found.', lang))
        return
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Who Have It', callback_data=f'whohaveit_{character_id}')]])
    text = f"🌟 **Character Info**\n🆔 ID: `{character_id}`\n📛 Name: {character['name']}\n📺 Anime: {character['anime']}\n💎 Rarity: {character['rarity']}\n"
    if 'vid_url' in character:
        await message.reply_video(character['vid_url'], caption=tr(text, lang), reply_markup=keyboard)
    else:
        await message.reply_photo(character['img_url'], caption=tr(text, lang), reply_markup=keyboard)

@app.on_callback_query(filters.regex('^whohaveit_'))
async def who_have_it(client, callback_query):
    lang = await get_effective_lang(callback_query)
    character_id = callback_query.data.split('_')[1]
    blocked_ids = await get_blocklisted_id_variants()
    users = await user_collection.find({'characters.id': character_id, 'id': {'$nin': blocked_ids}}).to_list(length=10)
    if not users:
        await callback_query.answer(tr('No one owns this character yet!', lang), show_alert=True)
        return
    owner_text = '**🏆 Top 10 Users Who Own This Character:**\n\n'
    for i, user in enumerate(users, 1):
        user_name = user.get('first_name', 'Unknown')
        count = sum((1 for char in user.get('characters', []) if char['id'] == character_id))
        owner_text += f"{i}. [{user_name}](tg://user?id={user['id']}) — x{count}\n"
    await callback_query.message.edit_caption(caption=tr(f'{callback_query.message.caption}\n\n{owner_text}', lang), reply_markup=None)
