from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import time
import secrets
import string
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aoiwaifu import app, user_collection, require_power, db, application
from aoiwaifu.admin.blocklist import is_user_blocklisted
transfer_in_progress = False
active_transfer = None
processing_locks = set()
TRANSFER_TIMEOUT = 60
transfer_logs = db['transfer_logs']

async def create_ttl_index():
    try:
        await transfer_logs.create_index('createdAt', expireAfterSeconds=3600)
    except Exception:
        pass
original_post_init = getattr(application, 'post_init', None)

async def transfer_post_init(app_ptb):
    if original_post_init:
        await original_post_init(app_ptb)
    asyncio.create_task(create_ttl_index())
application.post_init = transfer_post_init

def is_transfer_active_and_valid():
    global active_transfer, transfer_in_progress
    if not transfer_in_progress or not active_transfer:
        return False
    if time.time() - active_transfer['timestamp'] > TRANSFER_TIMEOUT:
        transfer_in_progress = False
        active_transfer = None
        return False
    return True

def generate_transfer_id():
    return 'TR_' + ''.join((secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)))

@app.on_message(filters.command('transfer'))
@require_power('VIP')
async def transfer_collection(client: Client, message: Message):
    lang = await get_effective_lang(message)
    global transfer_in_progress, active_transfer
    args = message.command[1:]
    if len(args) != 2:
        return await message.reply_text(tr('Incorrect format. Use: `/transfer user_id owner_id`', lang))
    user_id = args[0]
    owner_id = args[1]
    if not user_id.isdigit() or not owner_id.isdigit():
        return await message.reply_text(tr('Please provide valid numeric IDs.', lang))
    if user_id == owner_id:
        return await message.reply_text(tr('User ID and Owner ID must be different.', lang))
    if is_transfer_active_and_valid():
        return await message.reply_text(tr(f"⚠️ A transfer is already in progress (requested by user ID `{active_transfer['requester_id']}`). Please complete or cancel it first, or wait for it to expire.", lang))
    user = await user_collection.find_one({'id': {'$in': [int(user_id), str(user_id)]}})
    if not user:
        return await message.reply_text(tr('User not found.', lang))
    owner = await user_collection.find_one({'id': {'$in': [int(owner_id), str(owner_id)]}})
    if not owner:
        return await message.reply_text(tr('Owner not found.', lang))
    if await is_user_blocklisted(int(user_id)) or await is_user_blocklisted(int(owner_id)):
        return await message.reply_text(tr('🚫 Character transfers to or from a blocklisted user are disabled.', lang))
    user_chars = user.get('characters', [])
    if not user_chars:
        return await message.reply_text(tr(f'❌ User `{user_id}` has no characters to transfer.', lang))
    from_id = message.from_user.id
    transfer_id = generate_transfer_id()
    transfer_in_progress = True
    active_transfer = {'transfer_id': transfer_id, 'user_id': user_id, 'owner_id': owner_id, 'requester_id': from_id, 'timestamp': time.time()}
    text = f'⚠️ **Confirm Character Transfer?**\n\n👤 From: `{user_id}` (has {len(user_chars)} characters)\n➡️ To: `{owner_id}`\n🆔 Transfer ID: `{transfer_id}`\n\nClick the appropriate button below to proceed or cancel. This prompt will expire in 60 seconds.'
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('✅ Confirm Transfer', callback_data=f'confirm_tr:{transfer_id}'), InlineKeyboardButton('❌ Cancel', callback_data=f'cancel_tr:{transfer_id}')]])
    await message.reply_text(tr(text, lang), reply_markup=keyboard)

@app.on_callback_query(filters.regex('^confirm_tr:(\\w+)$'))
async def confirm_transfer_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    global transfer_in_progress, active_transfer
    transfer_id = callback_query.data.split(':')[1]
    if transfer_id in processing_locks:
        return await callback_query.answer(tr('⚠️ Transfer already in progress. Please wait...', lang), show_alert=True)
    processing_locks.add(transfer_id)
    try:
        if not is_transfer_active_and_valid() or not active_transfer or active_transfer['transfer_id'] != transfer_id:
            await callback_query.edit_message_text(tr('❌ This transfer request has expired or is invalid.', lang))
            return
        requester_id = active_transfer['requester_id']
        if callback_query.from_user.id != requester_id:
            await callback_query.answer(tr("You're not authorized to confirm this transfer.", lang), show_alert=True)
            return
        user_id = active_transfer['user_id']
        owner_id = active_transfer['owner_id']
        if await is_user_blocklisted(int(user_id)) or await is_user_blocklisted(int(owner_id)):
            await callback_query.answer(tr('🚫 Transfer cancelled: a participant is blocklisted.', lang), show_alert=True)
            transfer_in_progress = False
            active_transfer = None
            return
        user = await user_collection.find_one({'id': {'$in': [int(user_id), user_id]}})
        owner = await user_collection.find_one({'id': {'$in': [int(owner_id), owner_id]}})
        if not user or not owner:
            await callback_query.edit_message_text(tr('❌ User or Owner not found.', lang))
            transfer_in_progress = False
            active_transfer = None
            return
        user_chars = user.get('characters', [])
        if not user_chars:
            await callback_query.edit_message_text(tr(f'❌ User `{user_id}` has no characters to transfer.', lang))
            transfer_in_progress = False
            active_transfer = None
            return
        await user_collection.update_one({'id': {'$in': [int(owner_id), owner_id]}}, {'$push': {'characters': {'$each': user_chars}}})
        await user_collection.update_one({'id': {'$in': [int(user_id), user_id]}}, {'$set': {'characters': []}})
        transfer_doc = {'_id': transfer_id, 'user_id': user_id, 'owner_id': owner_id, 'characters': user_chars, 'timestamp': time.time(), 'createdAt': datetime.utcnow(), 'status': 'completed'}
        await transfer_logs.insert_one(transfer_doc)
        await callback_query.edit_message_text(tr(f'✅ **Transfer Successful!**\n\n👤 From: `{user_id}`\n➡️ To: `{owner_id}`\n📦 Characters Transferred: `{len(user_chars)}`\n\n🆔 **Transfer ID:** `{transfer_id}`\n🕒 *This transfer can be reverted within 1 hour using `/backtransfer {transfer_id}`*', lang))
        transfer_in_progress = False
        active_transfer = None
    finally:
        processing_locks.discard(transfer_id)

@app.on_callback_query(filters.regex('^cancel_tr:(\\w+)$'))
async def cancel_transfer_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    global transfer_in_progress, active_transfer
    transfer_id = callback_query.data.split(':')[1]
    if not active_transfer or active_transfer['transfer_id'] != transfer_id:
        return await callback_query.answer(tr('❌ This transfer is no longer active or has expired.', lang), show_alert=True)
    requester_id = active_transfer['requester_id']
    if callback_query.from_user.id != requester_id:
        return await callback_query.answer(tr("You can't cancel this action.", lang), show_alert=True)
    transfer_in_progress = False
    active_transfer = None
    await callback_query.edit_message_text(tr('🚫 Transfer cancelled by user.', lang))

@app.on_message(filters.command(['backtransfer', 'untransfer', 'trback']))
@require_power('VIP')
async def back_transfer(client: Client, message: Message):
    lang = await get_effective_lang(message)
    args = message.command[1:]
    if len(args) != 1:
        return await message.reply_text(tr('Incorrect format. Use: `/backtransfer <transfer_id>`', lang))
    transfer_id = args[0]
    log = await transfer_logs.find_one({'_id': transfer_id})
    if not log:
        return await message.reply_text(tr(f'❌ Transfer ID `{transfer_id}` not found in database.', lang))
    if log.get('status') == 'reverted':
        return await message.reply_text(tr(f'❌ Transfer `{transfer_id}` has already been reverted.', lang))
    elapsed = time.time() - log['timestamp']
    if elapsed > 3600:
        hours_elapsed = elapsed / 3600.0
        return await message.reply_text(tr(f'❌ Transfer `{transfer_id}` was done {hours_elapsed:.1f} hours ago.\nRollback is only valid for up to 1 hour.', lang))
    user_id = log['user_id']
    owner_id = log['owner_id']
    transferred_chars = log['characters']
    owner_db = await user_collection.find_one({'id': {'$in': [int(owner_id), str(owner_id)]}})
    if not owner_db:
        return await message.reply_text(tr(f'❌ Receiver owner `{owner_id}` document not found in DB. Cannot revert.', lang))

    def get_char_id(char):
        if isinstance(char, dict):
            return str(char.get('id'))
        return str(char)
    owner_chars = owner_db.get('characters', [])
    new_owner_chars = list(owner_chars)
    reverted_count = 0
    for t_char in transferred_chars:
        t_id = get_char_id(t_char)
        for idx, o_char in enumerate(new_owner_chars):
            if get_char_id(o_char) == t_id:
                new_owner_chars.pop(idx)
                reverted_count += 1
                break
    await user_collection.update_one({'id': {'$in': [int(owner_id), str(owner_id)]}}, {'$set': {'characters': new_owner_chars}})
    user_db = await user_collection.find_one({'id': {'$in': [int(user_id), str(user_id)]}})
    if user_db:
        await user_collection.update_one({'id': {'$in': [int(user_id), str(user_id)]}}, {'$push': {'characters': {'$each': transferred_chars}}})
    else:
        try:
            tg_user = await client.get_users(int(user_id))
            username = tg_user.username
            first_name = tg_user.first_name
        except Exception:
            username = None
            first_name = f'User {user_id}'
        await user_collection.insert_one({'id': int(user_id), 'username': username, 'first_name': first_name, 'characters': transferred_chars})
    await transfer_logs.update_one({'_id': transfer_id}, {'$set': {'status': 'reverted'}})
    await message.reply_text(tr(f'✅ **Transfer Reverted Successfully!**\n\n🆔 **Transfer ID:** `{transfer_id}`\n👤 Returned `{reverted_count}` characters back to original user `{user_id}`.\n➡️ Removed from user `{owner_id}`.', lang))
