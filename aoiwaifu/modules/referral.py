from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import html
import re
import time
import urllib.parse
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import MessageNotModified
from aoiwaifu import app, user_collection, db, GLOG, get_effective_lang, t
referrals_collection = db['referrals']
REFERRAL_DOLLARS = 25
REFERRAL_COINS = 1000
SECOND_CHAR_REFERRALS_REQUIRED = 10

async def _get_bot_username(client: Client) -> str:
    if getattr(client, 'me', None) and getattr(client.me, 'username', None):
        return client.me.username
    try:
        me = await client.get_me()
        if me and me.username:
            return me.username
    except Exception:
        pass
    return 'AoiWaifuBot'

async def build_referral_text(bot_username: str, user_id: int, referrals_count: int, lang: str='en') -> str:
    total_dollars = referrals_count * REFERRAL_DOLLARS
    total_coins = referrals_count * REFERRAL_COINS
    ref_link = f'https://t.me/{bot_username}?start=ref_{user_id}'
    char_milestone_status = f'🌟 <code>{referrals_count} Referrals</code>'
    cursor = referrals_collection.find({'referrer_id': user_id}).sort('created_at', -1).limit(5)
    recent_refs = await cursor.to_list(length=5)
    if recent_refs:
        history_lines = []
        for idx, r in enumerate(recent_refs, start=1):
            r_uid = r.get('referred_id', 0)
            r_name = html.escape(str(r.get('referred_name') or f'User {r_uid}')[:18])
            r_date = html.escape(str(r.get('date_str') or ''))
            date_part = f' <i>({r_date})</i>' if r_date else ''
            history_lines.append(f'  {idx}. <a href="tg://user?id={r_uid}"><b>{r_name}</b></a>{date_part}')
        history_block = '\n'.join(history_lines)
    else:
        history_block = '  <i>No referrals yet — share your link below!</i>'
    text = t('refer_caption', lang, ref_dollars=REFERRAL_DOLLARS, ref_coins=REFERRAL_COINS, referrals_count=referrals_count, char_milestone_status=char_milestone_status, ref_link=ref_link)
    return text

def build_referral_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    ref_link = f'https://t.me/{bot_username}?start=ref_{user_id}'
    share_msg = 'Join Aoi Waifu with me and claim free rewards! 🎁 Play games and collect anime waifus!'
    encoded_url = urllib.parse.quote(ref_link, safe='')
    encoded_text = urllib.parse.quote(share_msg, safe='')
    share_url = f'https://t.me/share/url?url={encoded_url}&text={encoded_text}'
    return InlineKeyboardMarkup([[InlineKeyboardButton('🚀 Share', url=share_url), InlineKeyboardButton('📋 Record', callback_data=f'refer_list:{user_id}'), InlineKeyboardButton('🔄 Refresh', callback_data=f'refer_refresh:{user_id}')]])

@app.on_message(filters.command(['refer', 'referral']))
async def refer_command(client: Client, message):
    user_id = message.from_user.id
    user_doc = await user_collection.find_one({'id': user_id})
    referrals_count = int(user_doc.get('referrals_count') or 0) if user_doc else 0
    bot_username = await _get_bot_username(client)
    lang = await get_effective_lang(message, user_id=user_id)
    caption = await build_referral_text(bot_username, user_id, referrals_count, lang=lang)
    keyboard = build_referral_keyboard(bot_username, user_id)
    await message.reply_text(text=tr(caption, lang), reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_callback_query(filters.regex('^refer_refresh:(\\d+)$'))
async def refer_refresh_callback(client: Client, callback_query: CallbackQuery):
    target_user_id = int(callback_query.matches[0].group(1))
    user_doc = await user_collection.find_one({'id': target_user_id})
    referrals_count = int(user_doc.get('referrals_count') or 0) if user_doc else 0
    bot_username = await _get_bot_username(client)
    lang = await get_effective_lang(callback_query, user_id=target_user_id)
    caption = await build_referral_text(bot_username, target_user_id, referrals_count, lang=lang)
    keyboard = build_referral_keyboard(bot_username, target_user_id)
    try:
        await callback_query.edit_message_text(text=tr(caption, lang), reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        pass
    finally:
        await callback_query.answer(tr('🔄 Referral stats refreshed!', lang))

@app.on_callback_query(filters.regex('^refer_list:(\\d+)$'))
async def refer_list_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    target_user_id = int(callback_query.matches[0].group(1))
    cursor = referrals_collection.find({'referrer_id': target_user_id}).sort('created_at', -1).limit(25)
    records = await cursor.to_list(length=25)
    bot_username = await _get_bot_username(client)
    ref_link = f'https://t.me/{bot_username}?start=ref_{target_user_id}'
    if not records:
        rec_text = "<i>You haven't referred anyone yet. Share your link to start earning!</i>"
    else:
        lines = []
        for idx, r in enumerate(records, start=1):
            r_uid = r.get('referred_id', 0)
            r_name = html.escape(str(r.get('referred_name') or f'User {r_uid}')[:20])
            r_uname = r.get('referred_username')
            uname_str = f' (@{html.escape(r_uname)})' if r_uname else ''
            r_date = html.escape(str(r.get('date_str') or ''))
            lines.append(f'{idx}. <a href="tg://user?id={r_uid}"><b>{r_name}</b></a>{uname_str} — <code>{r_uid}</code>\n    └ 📅 <i>{r_date}</i> • 🎁 <code>+${REFERRAL_DOLLARS} &amp; +{REFERRAL_COINS:,} coins</code>')
        rec_text = '\n'.join(lines)
    text = f'╭━━━〔 📋 𝐑𝐄𝐅𝐄𝐑𝐑𝐀𝐋 𝐑𝐄𝐂𝐎𝐑𝐃 〕━━━╮\nTotal Invited Users: <b>{len(records)}</b>\n╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n<blockquote>{rec_text}\n\n🔗 <b>Invite Link:</b> <code>{ref_link}</code></blockquote>'
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data=f'refer_refresh:{target_user_id}')]])
    try:
        await callback_query.edit_message_text(text=tr(text, lang), reply_markup=kb, parse_mode=enums.ParseMode.HTML)
    except MessageNotModified:
        pass
    finally:
        await callback_query.answer()

async def process_referral(client: Client, new_user, ref_arg: str, is_new_start: bool=True):
    """
    Process referral reward when a user starts the bot via:
    /start ref_<user_id>, /start ref=<user_id>, /start start=ref=<user_id>, or /start <user_id>.
    Gives referrer $25 waifu dollars and 1,000 coins and records full history.
    """
    if not ref_arg or not new_user:
        return
    clean_arg = ref_arg.strip()
    if clean_arg.startswith(('g_', 'game_', 'du_')):
        return
    m = re.search('(?:ref[_=-]?|r[_=-]?)?(\\d{5,15})', clean_arg, re.IGNORECASE)
    if not m:
        return
    referrer_id = int(m.group(1))
    new_user_id = new_user.id
    if not referrer_id or referrer_id == new_user_id:
        return
    already_ref = await referrals_collection.find_one({'referred_id': new_user_id})
    if already_ref:
        return
    existing_user = await user_collection.find_one({'id': new_user_id})
    if existing_user and existing_user.get('referred_by'):
        return
    if not is_new_start and existing_user:
        if len(existing_user.get('characters', [])) > 0 or existing_user.get('balance', 0) > 100:
            return
    referrer_doc = await user_collection.find_one({'id': referrer_id})
    referrer_name = (referrer_doc.get('first_name') if referrer_doc else None) or ''
    if not referrer_name:
        try:
            tg_ref = await client.get_users(referrer_id)
            if tg_ref:
                referrer_name = tg_ref.first_name or tg_ref.username or f'User {referrer_id}'
        except Exception:
            referrer_name = f'User {referrer_id}'
    now = time.time()
    date_str = datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')
    new_user_name = str(new_user.first_name or 'User')
    new_user_uname = str(new_user.username or '')
    await referrals_collection.insert_one({'referrer_id': referrer_id, 'referrer_name': referrer_name, 'referred_id': new_user_id, 'referred_name': new_user_name, 'referred_username': new_user_uname, 'dollars': REFERRAL_DOLLARS, 'coins': REFERRAL_COINS, 'created_at': now, 'date_str': date_str})
    await user_collection.update_one({'id': new_user_id}, {'$set': {'referred_by': referrer_id, 'referred_by_name': referrer_name, 'referred_at': date_str}}, upsert=True)
    await user_collection.update_one({'id': referrer_id}, {'$inc': {'tokens': REFERRAL_DOLLARS, 'balance': REFERRAL_COINS, 'referrals_count': 1}, '$push': {'referral_history': {'user_id': new_user_id, 'name': new_user_name, 'username': new_user_uname, 'date': date_str}}}, upsert=True)
    updated_ref_doc = await user_collection.find_one({'id': referrer_id})
    new_count = int(updated_ref_doc.get('referrals_count', 1)) if updated_ref_doc else 1
    safe_new_name = html.escape(new_user_name)
    safe_ref_name = html.escape(referrer_name)
    milestone_note = ''
    if new_count >= SECOND_CHAR_REFERRALS_REQUIRED:
        milestone_note = ''
    notify_referrer_text = f'🎉 <b>New Referral Joined!</b>\n\n👤 <b>Invited User:</b> <a href="tg://user?id={new_user_id}"><b>{safe_new_name}</b></a> (<code>{new_user_id}</code>)\n📅 <b>Date:</b> <code>{date_str}</code>\n\n🎁 <b>Your Referral Bonus:</b>\n├ 💵 <b>+${REFERRAL_DOLLARS} Waifu Dollars</b>\n└ 💰 <b>+{REFERRAL_COINS:,} Coins</b>\n\n👥 <b>Total Friends Referred:</b> <code>{new_count} Users</code>{milestone_note}'
    try:
        await client.send_message(chat_id=referrer_id, text=notify_referrer_text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass
    notify_new_user_text = f"""🎁 <b>Referral Connected!</b>\nYou joined Aoi Waifu via <a href="tg://user?id={referrer_id}"><b>{safe_ref_name}</b></a>'s referral link!"""
    try:
        await client.send_message(chat_id=new_user_id, text=notify_new_user_text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass
    log_text = f'🔗 <b>#NEW_REFERRAL_LOG</b>\n\n├ 👤 <b>Referrer:</b> <a href="tg://user?id={referrer_id}"><b>{safe_ref_name}</b></a> (<code>{referrer_id}</code>)\n├ 🆕 <b>Referred User:</b> <a href="tg://user?id={new_user_id}"><b>{safe_new_name}</b></a> (<code>{new_user_id}</code>)\n├ 🎁 <b>Reward Given:</b> <code>+${REFERRAL_DOLLARS} &amp; +{REFERRAL_COINS:,} coins</code>\n└ 📊 <b>Referrer Total Invites:</b> <code>{new_count}</code>'
    try:
        await client.send_message(chat_id=GLOG, text=log_text, parse_mode=enums.ParseMode.HTML)
    except Exception:
        pass
