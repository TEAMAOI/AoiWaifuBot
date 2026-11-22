# ==============================================================================
# How to Use:
#   - Purpose: Daily character claim handler (/claim, /hclaim) using dynamic
#     MongoDB-configured claimable rarities.
#   - Components: format_time_delta, get_unique_characters, mclaim.
#   - Roots / Routes:
#       * Commands: /claim, /hclaim
#       * DB Collections: db.user_collection_lmaoooo, db.anime_characters_lol,
#         db.bot_dynamic_settings
#   - Usage: Loaded automatically by aoiwaifu/__main__.py.
# ==============================================================================

from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import asyncio
from pyrogram import Client, filters, types as t_types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from aoiwaifu import ZYRO as bot
from aoiwaifu import user_collection, collection, user_nguess_progress, user_guess_progress, SUPPORT_CHAT_ID as chat, SUPPORT_CHAT

claim_lock = {}


async def format_time_delta(delta):
    seconds = delta.total_seconds()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{int(hours)}h {int(minutes)}m {int(seconds)}s' if hours or minutes or seconds else '0s'


async def get_unique_characters(user_id, target_rarities=None):
    if target_rarities is None:
        from aoiwaifu import rarity_map
        target_rarities = [rarity_map[index] for index in (1, 2, 3) if index in rarity_map]
    try:
        user_data = await user_collection.find_one({'id': user_id}, {'characters.id': 1})
        claimed_ids = [char['id'] for char in user_data.get('characters', []) if isinstance(char, dict) and 'id' in char] if user_data else []
        pipeline = [
            {'$match': {'rarity': {'$in': target_rarities}, 'id': {'$nin': claimed_ids}}},
            {'$sample': {'size': 1}},
        ]
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        if not characters:
            # Fallback if user already claimed all unique cards in those rarities
            pipeline_any = [
                {'$match': {'rarity': {'$in': target_rarities}}},
                {'$sample': {'size': 1}},
            ]
            cursor_any = collection.aggregate(pipeline_any)
            characters = await cursor_any.to_list(length=None)
        return characters if characters else []
    except Exception as e:
        print(f'Error retrieving unique characters: {e}')
        return []


@bot.on_message(filters.command(['hclaim', 'claim']))
async def mclaim(_, message: t_types.Message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    mention = message.from_user.mention
    target_chat = str(chat or '-1004367817195')
    if str(message.chat.id) != target_chat:
        join_button = InlineKeyboardMarkup([[InlineKeyboardButton('💬 Join Support Chat', url=SUPPORT_CHAT or 'https://t.me/aoinetworksupport')]])
        return await message.reply_text(tr('🔔 ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪɴ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ!', lang), reply_markup=join_button)
    if user_id in claim_lock:
        await message.reply_text(tr('Your claim request is already being processed. Please wait.', lang))
        return
    claim_lock[user_id] = True
    try:
        user_data = await user_collection.find_one({'id': user_id})
        if not user_data:
            user_data = {'id': user_id, 'username': message.from_user.username, 'first_name': message.from_user.first_name, 'characters': [], 'last_daily_reward': None}
            await user_collection.insert_one(user_data)
        last_claimed_date = user_data.get('last_daily_reward')
        if last_claimed_date and hasattr(last_claimed_date, 'date') and last_claimed_date.date() == datetime.utcnow().date():
            remaining_time = timedelta(days=1) - (datetime.utcnow() - last_claimed_date)
            formatted_time = await format_time_delta(remaining_time)
            return await message.reply_text(tr(f"⏳ *You've already claimed today! Next reward in:* `{formatted_time}`", lang))
        unique_characters = await get_unique_characters(user_id)
        if not unique_characters:
            return await message.reply_text(tr('🚫 *No characters available to claim at the moment. Please try again later.*', lang))
        await user_collection.update_one({'id': user_id}, {'$push': {'characters': {'$each': unique_characters}}, '$set': {'last_daily_reward': datetime.utcnow()}})
        for character in unique_characters:
            await message.reply_photo(photo=character['img_url'], caption=tr(f"🎊 ℂ𝕆ℕ𝔾ℝ𝔸𝕋𝕌𝕃𝔸𝕋𝕀𝕆ℕ𝕊 {mention}! 🎉\n🌸 𝐍𝐚𝐦𝐞 : {character['name']}\n🌈 𝐑𝐚𝐫𝐢𝐭𝐲 : {character['rarity']}\n⛩️ 𝐀𝐧𝐢𝐦𝐞 : {character['anime']}\n💫 ℭ𝔬𝔪𝔢 𝔟𝔞𝔠𝔨 𝔱𝔬𝔪𝔬𝔯𝔯𝔬𝔴 𝔣𝔬𝔯 𝔞𝔫𝔬𝔱𝔥𝔢𝔯 𝔠𝔩𝔞𝔦𝔪!", lang))
    except Exception as e:
        print(f'Error in mclaim command: {e}')
        await message.reply_text(tr('❌ *An unexpected error occurred.*', lang))
    finally:
        claim_lock.pop(user_id, None)
