# ==============================================================================
# How to Use:
#   - Purpose: Manages character gifting (/gift) between users and records
#     temporary in-memory gift logs (non-Mongo) for the VIP Admin Panel.
#   - Components: gift command handler, confirm/cancel callback, auto_cancel_gift.
#   - Roots / Routes:
#       * Command: /gift <character_id> (reply to recipient)
#       * Callbacks: confirm_gift, cancel_gift
#   - Usage: Loaded automatically by aoiwaifu/__main__.py.
# ==============================================================================

from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from aoiwaifu import user_collection, ZYRO
from aoiwaifu.admin.blocklist import is_user_blocklisted

pending_gifts = {}


async def auto_cancel_gift(sender_id, receiver_id):
    await asyncio.sleep(3600)
    if (sender_id, receiver_id) in pending_gifts and (not pending_gifts[sender_id, receiver_id]['processed']):
        pending_gifts.pop((sender_id, receiver_id), None)
        print(f'Gift from {sender_id} to {receiver_id} auto-cancelled after 1 hour.')


@ZYRO.on_message(filters.command('gift'))
async def gift(client, message):
    lang = await get_effective_lang(message)
    sender_id = message.from_user.id
    if await is_user_blocklisted(sender_id):
        return await message.reply_text(tr('🚫 Blocklisted users cannot send or receive character gifts.', lang))
    for _sender_id, _ in pending_gifts.keys():
        if _sender_id == sender_id:
            await message.reply_text(tr('You already have a gift processing. Please confirm or cancel it before sending another gift.', lang), parse_mode=ParseMode.HTML)
            return
    if not message.reply_to_message:
        await message.reply_text(tr("You need to reply to a user's message to gift a character!", lang), parse_mode=ParseMode.HTML)
        return
    receiver_user = message.reply_to_message.from_user
    receiver_id = receiver_user.id
    if getattr(receiver_user, 'is_bot', False):
        return await message.reply_text(tr('❌ <b>Not Allowed!</b> You cannot gift characters to a bot account.', lang), parse_mode=ParseMode.HTML)
    if await is_user_blocklisted(receiver_id):
        return await message.reply_text(tr('🚫 This user is blocklisted and cannot receive character gifts.', lang))
    receiver_username = message.reply_to_message.from_user.username
    receiver_first_name = message.reply_to_message.from_user.first_name
    if sender_id == receiver_id:
        await message.reply_text(tr("You can't gift a character to yourself!", lang), parse_mode=ParseMode.HTML)
        return
    if len(message.command) != 2:
        await message.reply_text(tr('You need to provide a character ID!', lang), parse_mode=ParseMode.HTML)
        return
    character_id = message.command[1]
    sender = await user_collection.find_one({'id': sender_id})
    if not sender:
        return await message.reply_text(tr('⚠️ Your profile was not found. Use /start first, then try /gift again.', lang))
    sender_characters = sender.get('characters') or []
    if not isinstance(sender_characters, list):
        return await message.reply_text(tr('⚠️ Your character collection data is invalid. Please contact support.', lang))
    character = next((char for char in sender_characters if isinstance(char, dict) and str(char.get('id')) == str(character_id)), None)
    if not character:
        await message.reply_text(tr("You don't have this character in your collection!", lang), parse_mode=ParseMode.HTML)
        return
    pending_gifts[sender_id, receiver_id] = {
        'character': character,
        'sender_first_name': message.from_user.first_name or 'User',
        'receiver_username': receiver_username,
        'receiver_first_name': receiver_first_name,
        'processed': False,
    }
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('✅ Confirm Gift', callback_data='confirm_gift')], [InlineKeyboardButton('❌ Cancel Gift', callback_data='cancel_gift')]])
    caption = f"🎁 <b>Gift Character</b>\n🌸 <b>{character.get('name', 'Unknown')}</b>\n"
    if character.get('img_url'):
        await message.reply_photo(photo=character['img_url'], caption=tr(caption, lang), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    else:
        await message.reply_text(tr(caption, lang), parse_mode=ParseMode.HTML, reply_markup=keyboard)
    asyncio.create_task(auto_cancel_gift(sender_id, receiver_id))


@ZYRO.on_callback_query(filters.create(lambda _, __, query: query.data in ['confirm_gift', 'cancel_gift']))
async def on_callback_query(client, callback_query):
    lang = await get_effective_lang(callback_query)
    sender_id = callback_query.from_user.id
    for (_sender_id, receiver_id), gift_item in pending_gifts.items():
        if _sender_id == sender_id:
            break
    else:
        await callback_query.answer(tr('This is not for you!', lang), show_alert=True)
        return
    if callback_query.data == 'confirm_gift':
        try:
            receiver_user = await client.get_users(receiver_id)
        except Exception:
            receiver_user = None
        if receiver_user and getattr(receiver_user, 'is_bot', False):
            pending_gifts.pop((sender_id, receiver_id), None)
            await callback_query.answer(tr('❌ Not Allowed! Characters cannot be gifted to bot accounts.', lang), show_alert=True)
            return
        if await is_user_blocklisted(sender_id) or await is_user_blocklisted(receiver_id):
            pending_gifts.pop((sender_id, receiver_id), None)
            await callback_query.answer(tr('🚫 Gift cancelled: a participant is blocklisted.', lang), show_alert=True)
            return
        if gift_item['processed']:
            await callback_query.answer(tr('This gift has already been processed.', lang), show_alert=True)
            return
        gift_item['processed'] = True
        sender = await user_collection.find_one({'id': sender_id})
        receiver = await user_collection.find_one({'id': receiver_id})
        if not sender:
            await callback_query.answer(tr('❌ Your profile was not found. Gift cancelled.', lang), show_alert=True)
            pending_gifts.pop((sender_id, receiver_id), None)
            return
        sender_characters = sender.get('characters') or []
        if not isinstance(sender_characters, list):
            await callback_query.answer(tr('⚠️ Your character collection is invalid. Contact support.', lang), show_alert=True)
            pending_gifts.pop((sender_id, receiver_id), None)
            return
        gift_character = gift_item.get('character')
        if not isinstance(gift_character, dict) or not any((isinstance(char, dict) and str(char.get('id')) == str(gift_character.get('id')) for char in sender_characters)):
            await callback_query.answer(tr('❌ This character is no longer in your collection. Gift cancelled.', lang), show_alert=True)
            pending_gifts.pop((sender_id, receiver_id), None)
            return
        _removed_one = False
        _filtered_sender_chars = []
        for char in sender_characters:
            if not _removed_one and isinstance(char, dict) and (str(char.get('id')) == str(gift_character.get('id'))):
                _removed_one = True
                continue
            _filtered_sender_chars.append(char)
        sender_characters = _filtered_sender_chars
        await user_collection.update_one({'id': sender_id}, {'$set': {'characters': sender_characters}})
        if receiver:
            await user_collection.update_one({'id': receiver_id}, {'$push': {'characters': gift_character}})
        else:
            await user_collection.insert_one({'id': receiver_id, 'username': gift_item['receiver_username'], 'first_name': gift_item['receiver_first_name'], 'characters': [gift_item['character']]})

        # Record in temporary in-memory Gift Logs (NOT stored in MongoDB)
