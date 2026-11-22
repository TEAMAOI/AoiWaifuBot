from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import MessageNotModified
import asyncio
import html
from aoiwaifu import app as Client
from aoiwaifu import user_collection, top_global_groups_collection
from aoiwaifu.admin.blocklist import get_blocklisted_id_variants
PHOTO_URL = ['https://files.catbox.moe/jk69z5.png']

def leaderboard_header(title, subtitle):
    return f'🎀 <b>ＡＬＹＡ  ＷＡＩ𝐅Ｕ</b> 🎀\n╭──────────────╮\n  🏆 <b>{title}</b>\n  <i>{subtitle}</i>\n╰──────────────╯\n\n'

def leaderboard_buttons(active_button=None):
    return InlineKeyboardMarkup([[InlineKeyboardButton('✅ Top' if active_button == 'top' else '🏆 Top', callback_data='top'), InlineKeyboardButton('✅ Groups' if active_button == 'top_group' else '👥 Groups', callback_data='top_group')], [InlineKeyboardButton('✅ Coins' if active_button == 'mtop' else '💰 Coins', callback_data='mtop'), InlineKeyboardButton('✅ Dollar' if active_button == 'tokens' else '💵 Dollar', callback_data='tokens')], [InlineKeyboardButton('✅ Diwali' if active_button == 'diwali' else '🪔 Diwali', callback_data='diwali')]])

async def resolve_user_display_name(client: Client, user_id: int, current_first_name: str=None, current_username: str=None) -> str:
    """Use names already stored in MongoDB; avoid slow Telegram API lookups."""
    if current_first_name and str(current_first_name).strip() and str(current_first_name).strip().lower() not in ('unknown', 'none'):
        return str(current_first_name).strip()
    return f'Player {user_id}' if user_id else 'Collector'

def add_rank_line(rank, name, value, user_id=None, label=''):
    safe_name = html.escape(str(name or 'Collector')[:18])
    safe_name = f'<b>{safe_name}</b>'
    medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, f'<b>{rank:02}</b>')
    suffix = f'  <i>{label}</i>' if label else ''
    return f'{medal} {safe_name}  ➜  <b>{value}</b>{suffix}\n'

@Client.on_message(filters.command('rank'))
async def rank(client, message):
    lang = await get_effective_lang(message)

    # Send the visual response immediately; update this same message after DB work.
    loading_caption = leaderboard_header('GLOBAL COLLECTOR RANK', 'Syncing the leaderboard…') + '⏳ <b>Logging...</b>\n\n<i>Fetching the top collectors. Please wait.</i>'
    progress = await message.reply_photo(
        photo=PHOTO_URL[0],
        caption=loading_caption,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=leaderboard_buttons('top')
    )

    try:
        pipeline = [
            {'$project': {
                '_id': 0, 'id': 1, 'first_name': 1, 'username': 1,
                'char_count': {'$size': {'$ifNull': ['$characters', []]}}
            }},
            {'$sort': {'char_count': -1, 'id': 1}},
            {'$limit': 10}
        ]
        leaderboard_data = await user_collection.aggregate(pipeline).to_list(length=10)
        caption = leaderboard_header('GLOBAL COLLECTOR RANK', 'The top 10 collectors in Aoi Waifu')
        if not leaderboard_data:
            caption += '🌸 <i>No collectors yet. Be the first to claim the crown!</i>\n'
        else:
            resolved_names = await asyncio.gather(*[
                resolve_user_display_name(client, u.get('id'), u.get('first_name'), u.get('username'))
                for u in leaderboard_data
            ])
            for i, (user, name) in enumerate(zip(leaderboard_data, resolved_names), start=1):
                caption += add_rank_line(i, name, user.get('char_count', 0))
        caption += '\n<i>Every character counts. Keep collecting and climb the leaderboard! ✨</i>'
        await progress.edit_caption(
            caption=tr(caption, lang),
            parse_mode=enums.ParseMode.HTML,
            reply_markup=leaderboard_buttons('top')
        )
    except Exception:
        await progress.edit_caption(
            caption=leaderboard_header('LEADERBOARD UNAVAILABLE', 'We could not load the rankings right now.') +
                    '⚠️ <i>Please try /rank again in a moment.</i>',
            parse_mode=enums.ParseMode.HTML,
            reply_markup=leaderboard_buttons('top')
        )

async def update_caption(callback_query, caption, active_button):
    try:
        await callback_query.edit_message_caption(caption=caption, parse_mode=enums.ParseMode.HTML, reply_markup=leaderboard_buttons(active_button))
    except MessageNotModified:
        pass
    finally:
        await callback_query.answer()

@Client.on_callback_query(filters.regex('^top$'))
async def top_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    cursor = user_collection.aggregate([{'$project': {'_id': 0, 'id': 1, 'first_name': 1, 'username': 1, 'char_count': {'$size': {'$ifNull': ['$characters', []]}}}}, {'$sort': {'char_count': -1}}, {'$limit': 10}])
    leaderboard_data = await cursor.to_list(length=10)
    caption = leaderboard_header('CHARACTER COLLECTION', 'The most dedicated collectors')
    if not leaderboard_data:
        caption += '🌸 <i>No collectors to show yet. Be the first!</i>\n'
    else:
        resolved_names = await asyncio.gather(*[resolve_user_display_name(client, u.get('id'), u.get('first_name'), u.get('username')) for u in leaderboard_data])
        for i, (user, name) in enumerate(zip(leaderboard_data, resolved_names), start=1):
            caption += add_rank_line(i, name, user.get('char_count', 0), user.get('id'))
    caption += '\n<i>Collect more waifus to climb the leaderboard ✨</i>'
    await update_caption(callback_query, caption, 'top')

@Client.on_callback_query(filters.regex('^top_group$'))
async def top_group_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    cursor = top_global_groups_collection.aggregate([{'$project': {'group_name': 1, 'count': 1}}, {'$sort': {'count': -1}}, {'$limit': 10}])
    leaderboard_data = await cursor.to_list(length=10)
    caption = leaderboard_header('GROUP LEADERBOARD', 'Communities collecting together')
    if not leaderboard_data:
        caption += '🌸 <i>No group rankings available yet.</i>\n'
    else:
        for i, group in enumerate(leaderboard_data, start=1):
            caption += add_rank_line(i, group.get('group_name'), group.get('count', 0), label='characters')
    caption += '\n<i>Invite your friends and grow your collection together 💫</i>'
    await update_caption(callback_query, caption, 'top_group')

@Client.on_callback_query(filters.regex('^mtop$'))
async def mtop_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    blocked_ids = await get_blocklisted_id_variants()
    top_users = await user_collection.find({'id': {'$nin': blocked_ids}}).sort('balance', -1).limit(10).to_list(length=10)
    caption = leaderboard_header('COIN CHAMPIONS', 'The richest collectors')
    if not top_users:
        caption += '🌸 <i>No coin rankings available yet.</i>\n'
    else:
        resolved_names = await asyncio.gather(*[resolve_user_display_name(client, u.get('id'), u.get('first_name'), u.get('username')) for u in top_users])
        for rank, (user, name) in enumerate(zip(top_users, resolved_names), start=1):
            caption += add_rank_line(rank, name, f"💰 {user.get('balance', 0):,}", user.get('id'), 'coins')
    caption += '\n<i>Keep playing to stack up more coins 💸</i>'
    await update_caption(callback_query, caption, 'mtop')

@Client.on_callback_query(filters.regex('^tokens$'))
async def tokens_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    blocked_ids = await get_blocklisted_id_variants()
    top_users = await user_collection.find({'id': {'$nin': blocked_ids}}).sort('tokens', -1).limit(10).to_list(length=10)
    caption = leaderboard_header('DOLLAR LEADERBOARD', 'Top holders of waifu dollars')
    if not top_users:
        caption += '🌸 <i>No dollar rankings available yet.</i>\n'
    else:
        resolved_names = await asyncio.gather(*[resolve_user_display_name(client, u.get('id'), u.get('first_name'), u.get('username')) for u in top_users])
        for rank, (user, name) in enumerate(zip(top_users, resolved_names), start=1):
            caption += add_rank_line(rank, name, f"💵 ${user.get('tokens', 0):,}", user.get('id'), 'dollars')
    caption += '\n<i>Your dollar balance is stored safely in your wallet 💎</i>'
    await update_caption(callback_query, caption, 'tokens')

@Client.on_callback_query(filters.regex('^diwali$'))
async def diwali_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    blocked_ids = await get_blocklisted_id_variants()
    cursor = user_collection.aggregate([{'$project': {'_id': 0, 'id': 1, 'first_name': 1, 'username': 1, 'diwali_count': {'$size': {'$filter': {'input': {'$ifNull': ['$characters', []]}, 'as': 'character', 'cond': {'$eq': ['$$character.rarity', 'Diwali 🪔']}}}}}}, {'$match': {'diwali_count': {'$gt': 0}, 'id': {'$nin': blocked_ids}}}, {'$sort': {'diwali_count': -1, 'id': 1}}, {'$limit': 10}])
    leaderboard_data = await cursor.to_list(length=10)
    caption = leaderboard_header('DIWALI COLLECTION', 'Top collectors of Diwali characters 🪔')
    if not leaderboard_data:
        caption += '🌸 <i>No Diwali characters collected yet. Be the first!</i>\\n'
    else:
        resolved_names = await asyncio.gather(*[resolve_user_display_name(client, u.get('id'), u.get('first_name'), u.get('username')) for u in leaderboard_data])
        for rank, (user, name) in enumerate(zip(leaderboard_data, resolved_names), start=1):
            caption += add_rank_line(rank, name, user.get('diwali_count', 0), user.get('id'), 'Diwali characters')
    caption += '\\n<i>Collect more Diwali characters to reach the top! ✨</i>'
    await update_caption(callback_query, caption, 'diwali')
