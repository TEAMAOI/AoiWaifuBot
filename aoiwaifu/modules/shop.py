from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t
import random
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from bson import ObjectId
from pyrogram import filters
from pyrogram.enums import ParseMode
from aoiwaifu import *
from pymongo import ReturnDocument
user_shop_state = {}
shop_claim_locks = set()
SHOP_IMAGE_URL = 'https://i.ibb.co/HfnC1X4m/file-000000008d8c8208aeb660d5f616cdf0.png'
RARITY_PRICE = {'Frequent 🫧': 1000, 'Superior 🎋': 3000, 'Elite 🪸': 8000, 'Pookie 🐣': 20000, 'Majestic 👑': 25000, 'Mythical 🧜\u200d♀️': 70000, 'DIY 🎨': 70000, 'Angelic 🪄': 100000, 'Galactic 🌌': 150000, 'Phantom 🧌': 200000, 'Imaginative 🍀': 300000, 'Exclusive \U0001fa8e': 350000, 'Habitual 👘': 500000, 'Winter ☃️': 25000, "Valentine's 💕": 25000, 'Summer 🏜️': 25000, 'Chibi 🎀': 5000, 'Cosplay 🗿': 40000, 'Rainy 🌧️': 25000, 'Seasonal 🍁': 25000}
SHOP_RARITIES = [('Frequent 🫧', '🫧'), ('Superior 🎋', '🎋'), ('Elite 🪸', '🪸'), ('Majestic 👑', '👑'), ('Summer 🏜️', '🏜️')]
SHOP_MAIN_CAPTION = '╭━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐒𝐇𝐎𝐏 〕━╮\n\n<blockquote>🌟 <b>Choose a rarity emoji below to browse the Bazaar:</b>\n🫧 Frequent  •  🎋 Superior  •  🪸 Elite\n👑 Majestic  •  🏜️ Summer</blockquote>\n╰━━━━━━━━━━━━━━━━━━╯'

def build_shop_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(emoji, callback_data=f'xeno_{i}') for i, (_, emoji) in enumerate(SHOP_RARITIES)]
    keyboard = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(keyboard)

def safe_split(data, sep='_', expected=2):
    parts = data.split(sep)
    if len(parts) < expected:
        parts += [None] * (expected - len(parts))
    return parts[:expected]

def is_video(url):
    return any((url.lower().endswith(ext) for ext in ['.mp4', '.mov', '.webm']))

async def _edit_shop_message_media(msg, media_url: str, caption: str, reply_markup: InlineKeyboardMarkup):
    """
    Edit the existing shop message in place instead of deleting and sending a new message.
    """
    try:
        if is_video(media_url):
            media_obj = InputMediaVideo(media=media_url, caption=caption, parse_mode=ParseMode.HTML)
        else:
            media_obj = InputMediaPhoto(media=media_url, caption=caption, parse_mode=ParseMode.HTML)
        await msg.edit_media(media=media_obj, reply_markup=reply_markup)
    except Exception:
        try:
            await msg.edit_caption(caption=caption, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception:
            pass

@app.on_message(filters.command(['shop', 'hshop', 'hshopmenu']))
async def shop_menu(client, message):
    lang = await get_effective_lang(message)
    await message.reply_photo(photo=SHOP_IMAGE_URL, caption=t('shop_main_caption', lang), reply_markup=build_shop_keyboard(), parse_mode=ParseMode.HTML)

@app.on_callback_query(filters.regex('^xeno_\\d+$'))
async def show_rarity_list(client, callback_query):
    lang = await get_effective_lang(callback_query)
    _, index_str = safe_split(callback_query.data, '_', 2)
    idx = int(index_str)
    if idx < 0 or idx >= len(SHOP_RARITIES):
        return await callback_query.answer(tr('Invalid rarity selection!', lang), show_alert=True)
    rarity, _ = SHOP_RARITIES[idx]
    user_id = callback_query.from_user.id
    characters = await collection.find({'rarity': rarity}).to_list(length=200)
    if not characters:
        return await callback_query.answer(tr('No characters found for this rarity!', lang), show_alert=True)
    random.shuffle(characters)
    user_shop_state[user_id] = {'rarity': rarity, 'index': 0, 'characters': characters[:5]}
    await show_character(client, callback_query.message, user_id)
    await callback_query.answer()

async def show_character(client, msg, user_id):
    lang = await get_effective_lang(msg)
    data = user_shop_state[user_id]
    char = data['characters'][data['index']]
    price = RARITY_PRICE.get(char['rarity'], 1000)
    caption = f"╭━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐒𝐇𝐎𝐏 〕━╮\n\n<blockquote>💎 <b>{char['name']}</b>\n🏯 <b>Anime:</b> {char['anime']}\n⭐ <b>Rarity:</b> {char['rarity']}\n💰 <b>Price:</b> {price:,} Star Coins\n🆔 <b>ID:</b> <code>{char['id']}</code></blockquote>\n╰━━━━━━━━━━━━━━━━━━╯"
    keyboard = [[InlineKeyboardButton('⬅️', callback_data='prev_char'), InlineKeyboardButton('🪄 Buy', callback_data=f"claim_{data['index']}"), InlineKeyboardButton('➡️', callback_data='next_char')], [InlineKeyboardButton('🔄 5k', callback_data='refresh_chars'), InlineKeyboardButton('🏪 Back', callback_data='shop_back')]]
    image_url = char.get('img_url') or char.get('image') or char.get('url')
    if not image_url:
        try:
            return await msg.edit_caption(caption=tr(f'{caption}\n\n❌ <i>No valid media URL for this character.</i>', lang), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        except Exception:
            return
    await _edit_shop_message_media(msg=msg, media_url=image_url, caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

@app.on_callback_query(filters.regex('^shop_back$'))
async def shop_back_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    await _edit_shop_message_media(msg=callback_query.message, media_url=SHOP_IMAGE_URL, caption=SHOP_MAIN_CAPTION, reply_markup=build_shop_keyboard())
    await callback_query.answer()

@app.on_callback_query(filters.regex('^refresh_chars$'))
async def refresh_shop_chars(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = callback_query.from_user.id
    state = user_shop_state.get(user_id)
    if not state:
        return await callback_query.answer(tr('Start from /shop again!', lang), show_alert=True)
    refresh_cost = 5000
    updated_user = await user_collection.find_one_and_update({'id': user_id, 'balance': {'$gte': refresh_cost}}, {'$inc': {'balance': -refresh_cost}}, return_document=ReturnDocument.AFTER)
    if not updated_user:
        return await callback_query.answer(tr('❌ Need 5,000 coins to refresh!', lang), show_alert=True)
    characters = await collection.find({'rarity': state['rarity']}).to_list(length=200)
    if not characters:
        return await callback_query.answer(tr('No characters found!', lang), show_alert=True)
    random.shuffle(characters)
    state['index'] = 0
    state['characters'] = characters[:5]
    await show_character(client, callback_query.message, user_id)
    await callback_query.answer(tr('🔄 Shop refreshed!', lang))

@app.on_callback_query(filters.regex('^next_char$'))
async def next_character(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = callback_query.from_user.id
    state = user_shop_state.get(user_id)
    if not state:
        return await callback_query.answer(tr('Start from /shop again!', lang), True)
    if state['index'] >= len(state['characters']) - 1:
        return await callback_query.answer(tr('No more heroes!', lang), True)
    state['index'] += 1
    await show_character(client, callback_query.message, user_id)
    await callback_query.answer()

@app.on_callback_query(filters.regex('^prev_char$'))
async def prev_character(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = callback_query.from_user.id
    state = user_shop_state.get(user_id)
    if not state:
        return await callback_query.answer(tr('Start from /shop again!', lang), True)
    if state['index'] <= 0:
        return await callback_query.answer(tr('Already at first hero!', lang), True)
    state['index'] -= 1
    await show_character(client, callback_query.message, user_id)
    await callback_query.answer()

@app.on_callback_query(filters.regex('^claim_\\d+$'))
async def claim_character(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = callback_query.from_user.id
    if user_id in shop_claim_locks:
        return await callback_query.answer(tr('⏳ Purchase in progress, please wait!', lang), show_alert=True)
    shop_claim_locks.add(user_id)
    try:
        _, index_str = safe_split(callback_query.data, '_', 2)
        state = user_shop_state.get(user_id)
        if not state or not state.get('characters'):
            return await callback_query.answer(tr('Open /shop again!', lang), show_alert=True)
        idx = int(index_str)
        if idx < 0 or idx >= len(state['characters']):
            return await callback_query.answer(tr('Invalid character selection!', lang), show_alert=True)
        char = state['characters'][idx]
        price = RARITY_PRICE.get(char.get('rarity'), 1000)
        updated_user = await user_collection.find_one_and_update({'id': user_id, 'balance': {'$gte': price}}, {'$inc': {'balance': -price}, '$push': {'characters': {'_id': ObjectId(), 'img_url': char.get('img_url'), 'name': char.get('name'), 'anime': char.get('anime'), 'rarity': char.get('rarity'), 'id': char.get('id')}}}, return_document=ReturnDocument.AFTER)
        if not updated_user:
            return await callback_query.answer(tr('❌ Not enough coins or not registered!', lang), show_alert=True)
        await callback_query.answer(tr(f"🎉 You claimed {char.get('name')} for {price:,} coins!", lang), show_alert=True)
    finally:
        shop_claim_locks.discard(user_id)
