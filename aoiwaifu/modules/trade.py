from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import asyncio
import uuid
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from aoiwaifu import user_collection, ZYRO
from aoiwaifu.admin.blocklist import is_user_blocklisted
pending_trades = {}
lock = []

async def auto_cancel_trade(trade_id, sender_id, receiver_id):
    await asyncio.sleep(600)
    if trade_id in pending_trades and (not pending_trades[trade_id]['processed']):
        del pending_trades[trade_id]
        if sender_id in lock:
            lock.remove(sender_id)
        if receiver_id in lock:
            lock.remove(receiver_id)
        print(f'Trade {trade_id} from {sender_id} to {receiver_id} auto-cancelled after 10 minutes.')

@ZYRO.on_message(filters.command('trade'))
async def trade(client, message):
    lang = await get_effective_lang(message)
    sender_id = message.from_user.id
    if await is_user_blocklisted(sender_id):
        return await message.reply_text(tr('🚫 Blocklisted users cannot trade characters.', lang))
    if sender_id in lock:
        await message.reply_text(tr('You already have a trade in progress. Please confirm or cancel it before starting a new trade.', lang), parse_mode=ParseMode.HTML)
        return
    if not message.reply_to_message:
        await message.reply_text(tr("You need to reply to a user's message to trade a character!", lang), parse_mode=ParseMode.HTML)
        return
    receiver_id = message.reply_to_message.from_user.id
    if await is_user_blocklisted(receiver_id):
        return await message.reply_text(tr('🚫 This user is blocklisted and cannot trade characters.', lang))
    receiver_username = message.reply_to_message.from_user.username
    receiver_first_name = message.reply_to_message.from_user.first_name
    if sender_id == receiver_id:
        await message.reply_text(tr("You can't trade a character with yourself!", lang), parse_mode=ParseMode.HTML)
        return
    if receiver_id in lock:
        await message.reply_text(tr(f'{message.reply_to_message.from_user.mention} is already in a trade. Please wait until their current trade is completed.', lang), parse_mode=ParseMode.HTML)
        return
    if len(message.command) != 3:
        await message.reply_text(tr("You need to provide your character ID and the other user's character ID! Usage: /trade <my_char_id> <user_char_id>", lang), parse_mode=ParseMode.HTML)
        return
    sender_char_id, receiver_char_id = (message.command[1], message.command[2])
    sender = await user_collection.find_one({'id': sender_id})
    receiver = await user_collection.find_one({'id': receiver_id})
    if not sender or not receiver:
        await message.reply_text(tr('One of the users is not found in the database!', lang), parse_mode=ParseMode.HTML)
        return
    sender_characters = sender.get('characters') or []
    receiver_characters = receiver.get('characters') or []
    if not isinstance(sender_characters, list) or not isinstance(receiver_characters, list):
        return await message.reply_text(tr("⚠️ One user's character collection data is invalid. Please contact support.", lang), parse_mode=ParseMode.HTML)
    sender_char = next((char for char in sender_characters if isinstance(char, dict) and str(char.get('id')) == str(sender_char_id)), None)
    if not sender_char:
        await message.reply_text(tr(f"You don't have the character with ID <b>{sender_char_id}</b> in your collection!", lang), parse_mode=ParseMode.HTML)
        return
    receiver_char = next((char for char in receiver_characters if isinstance(char, dict) and str(char.get('id')) == str(receiver_char_id)), None)
    if not receiver_char:
        await message.reply_text(tr(f"{message.reply_to_message.from_user.mention} doesn't have the character with ID <b>{receiver_char_id}</b> in their collection!", lang), parse_mode=ParseMode.HTML)
        return
    trade_id = str(uuid.uuid4())
    lock.append(sender_id)
    lock.append(receiver_id)
    pending_trades[trade_id] = {'sender_id': sender_id, 'sender_char': sender_char, 'receiver_id': receiver_id, 'receiver_char': receiver_char, 'receiver_username': receiver_username, 'receiver_first_name': receiver_first_name, 'processed': False, 'message_id': None}
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Confirm Trade', callback_data=f'confirm_trade_{trade_id}')], [InlineKeyboardButton('Cancel Trade', callback_data=f'cancel_trade_{trade_id}')]])
    trade_message = await message.reply_text(tr(f"{message.reply_to_message.from_user.mention}, do you agree to trade your character (ID: {receiver_char_id}) with {message.from_user.mention}'s character (ID: {sender_char_id})?", lang), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    pending_trades[trade_id]['message_id'] = trade_message.id
    asyncio.create_task(auto_cancel_trade(trade_id, sender_id, receiver_id))

@ZYRO.on_callback_query(filters.create(lambda _, __, query: query.data.startswith(('confirm_trade_', 'cancel_trade_'))))
async def on_trade_callback(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = callback_query.from_user.id
    data = callback_query.data
    trade_id = data.split('_', 2)[-1]
    trade = pending_trades.get(trade_id)
    if not trade:
        await callback_query.answer(tr('This trade is no longer available.', lang), show_alert=True)
        return
    if trade['processed']:
        await callback_query.answer(tr('This trade has already been processed.', lang), show_alert=True)
        return
    if data.startswith('confirm_trade_'):
        if await is_user_blocklisted(trade['sender_id']) or await is_user_blocklisted(trade['receiver_id']):
            await callback_query.answer(tr('🚫 Trade cancelled: a participant is blocklisted.', lang), show_alert=True)
            trade['processed'] = True
            pending_trades.pop(trade_id, None)
            return
        if user_id != trade['receiver_id']:
            await callback_query.answer(tr('Only the trade recipient can confirm this trade!', lang), show_alert=True)
            return
        trade['processed'] = True
        sender = await user_collection.find_one({'id': trade['sender_id']})
        receiver = await user_collection.find_one({'id': trade['receiver_id']})
        if not sender or not receiver:
            trade['processed'] = False
            await callback_query.answer(tr("⚠️ One user's profile is missing. Trade cannot be completed.", lang), show_alert=True)
            return
        sender_characters = sender.get('characters') or []
        receiver_characters = receiver.get('characters') or []
        if not isinstance(sender_characters, list) or not isinstance(receiver_characters, list):
            trade['processed'] = False
            await callback_query.answer(tr('⚠️ Character collection data is invalid. Contact support.', lang), show_alert=True)
            return
        sender_id_char = str(trade['sender_char'].get('id'))
        receiver_id_char = str(trade['receiver_char'].get('id'))
        if not any((isinstance(ch, dict) and str(ch.get('id')) == sender_id_char for ch in sender_characters)):
            await callback_query.answer(tr("❌ Sender's character is no longer available. Trade cancelled.", lang), show_alert=True)
            pending_trades.pop(trade_id, None)
            if trade['sender_id'] in lock:
                lock.remove(trade['sender_id'])
            if trade['receiver_id'] in lock:
                lock.remove(trade['receiver_id'])
            return
        if not any((isinstance(ch, dict) and str(ch.get('id')) == receiver_id_char for ch in receiver_characters)):
            await callback_query.answer(tr("❌ Recipient's character is no longer available. Trade cancelled.", lang), show_alert=True)
            pending_trades.pop(trade_id, None)
            if trade['sender_id'] in lock:
                lock.remove(trade['sender_id'])
            if trade['receiver_id'] in lock:
                lock.remove(trade['receiver_id'])
            return
        _rem_s = False
        _new_s = []
        for ch in sender_characters:
            if not _rem_s and isinstance(ch, dict) and (str(ch.get('id')) == sender_id_char):
                _rem_s = True
                continue
            _new_s.append(ch)
        sender_characters = _new_s
        _rem_r = False
        _new_r = []
        for ch in receiver_characters:
            if not _rem_r and isinstance(ch, dict) and (str(ch.get('id')) == receiver_id_char):
                _rem_r = True
                continue
            _new_r.append(ch)
        receiver_characters = _new_r
        sender_characters.append(trade['receiver_char'])
        receiver_characters.append(trade['sender_char'])
        await user_collection.update_one({'id': trade['sender_id']}, {'$set': {'characters': sender_characters}})
        await user_collection.update_one({'id': trade['receiver_id']}, {'$set': {'characters': receiver_characters}})
        if trade['sender_id'] in lock:
            lock.remove(trade['sender_id'])
        if trade['receiver_id'] in lock:
            lock.remove(trade['receiver_id'])
        del pending_trades[trade_id]
        await callback_query.message.edit_text(tr(f"Trade successful! Characters have been swapped between [{trade['receiver_first_name']}](tg://user?id={trade['receiver_id']}) and [{callback_query.from_user.first_name}](tg://user?id={trade['sender_id']}).", lang), parse_mode=ParseMode.HTML, reply_markup=None)
    elif data.startswith('cancel_trade_'):
        if user_id not in [trade['sender_id'], trade['receiver_id']]:
            await callback_query.answer(tr('This is not your trade!', lang), show_alert=True)
            return
        trade['processed'] = True
        if trade['sender_id'] in lock:
            lock.remove(trade['sender_id'])
        if trade['receiver_id'] in lock:
            lock.remove(trade['receiver_id'])
        del pending_trades[trade_id]
        await callback_query.message.edit_text(tr('❌️ Trade cancelled.', lang), parse_mode=ParseMode.HTML, reply_markup=None)
