# ==============================================================================
# How to Use:
#   - Purpose: Manages sudo users and granular power flags, including automatic
#     VIP session revocation (Auto-Logout) whenever VIP power is turned off.
#   - Components: add_sudo, remove_sudo, edit_sudo, toggle_power, sudo_list.
#   - Roots / Routes:
#       * Commands: /saddsudo, /sremovesudo, /seditsudo, /sudolist
#       * Callbacks: toggle_<uid>_<power>, close_keyboard
#       * DB Collection: db.sudo_users
#   - Usage: Loaded automatically by aoiwaifu/__main__.py.
# ==============================================================================

from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import MongoClient
from aoiwaifu import OWNER_ID, SUDO
from aoiwaifu import app, db, require_power
from functools import wraps
from aoiwaifu.unit.aoi_parse_fix import SudoUsersHybrid

sudo_users = SudoUsersHybrid(db['sudo_users'], SUDO, OWNER_ID)
ALL_POWERS = ['add_character', 'delete_character', 'update_character', 'approve_request', 'approve_inventory_request', 'VIP']


@app.on_message(filters.command('saddsudo') & filters.reply)
@require_power('VIP')
async def add_sudo(client, message):
    lang = await get_effective_lang(message)
    replied_user_id = message.reply_to_message.from_user.id
    existing_user = await sudo_users.find_one({'_id': replied_user_id})
    if existing_user:
        await message.reply_text(tr(f'User `{replied_user_id}` is already a sudo.', lang))
        return
    await sudo_users.update_one({'_id': replied_user_id}, {'$set': {'powers': {'add_character': True}}}, upsert=True)
    await message.reply_text(tr(f"User `{replied_user_id}` has been added as a sudo with 'add_character' power.", lang))


@app.on_message(filters.command('sremovesudo'))
@require_power('VIP')
async def remove_sudo(client, message):
    lang = await get_effective_lang(message)
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1 and message.command[1].isdigit():
        user_id = int(message.command[1])
    else:
        await message.reply_text(tr('❌ Please reply to a user or provide a valid user ID.', lang))
        return
    existing_user = await sudo_users.find_one({'_id': user_id})
    if not existing_user:
        await message.reply_text(tr(f'⚠️ User `{user_id}` is not a sudo.', lang))
        return
    await sudo_users.delete_one({'_id': user_id})
    await message.reply_text(tr(f'✅ User [{user_id}](tg://user?id={user_id}) has been removed from sudo.', lang))


@app.on_message(filters.command('seditsudo') & filters.reply)
@require_power('VIP')
async def edit_sudo(client, message):
    lang = await get_effective_lang(message)
    replied_user_id = message.reply_to_message.from_user.id
    user_data = await sudo_users.find_one({'_id': replied_user_id})
    if not user_data:
        await message.reply_text(tr('This user is not a sudo.', lang))
        return
    buttons = []
    powers = user_data.get('powers', {})
    for i, power in enumerate(ALL_POWERS):
        current_status = 'Yes' if powers.get(power, False) else 'No'
        buttons.append([InlineKeyboardButton(f'{power}', callback_data='noop'), InlineKeyboardButton(f'{current_status}', callback_data=f'toggle_{replied_user_id}_{power}')])
    buttons.append([InlineKeyboardButton('Closed', callback_data='close_keyboard')])
    keyboard = InlineKeyboardMarkup(buttons)
    await message.reply_text(tr(f'Edit powers for `{replied_user_id}`:', lang), reply_markup=keyboard)


@app.on_callback_query(filters.regex('^toggle_(\\d+)_(\\w+)$'))
@require_power('VIP')
async def toggle_power(client, callback_query):
    lang = await get_effective_lang(callback_query)
    user_id = int(callback_query.matches[0].group(1))
    power = callback_query.matches[0].group(2)
    user_data = await sudo_users.find_one({'_id': user_id})
    if not user_data:
        await callback_query.answer(tr('User not found.', lang), show_alert=True)
        return
    current_status = user_data.get('powers', {}).get(power, False)
    new_status = not current_status
    await sudo_users.update_one({'_id': user_id}, {'$set': {f'powers.{power}': new_status}})

    # If VIP power was turned OFF, immediately auto-logout any active VIP Admin Panel session!

    await callback_query.answer(tr(f"Power '{power}' updated to {('Yes' if new_status else 'No')}.", lang), show_alert=True)
    user_data = await sudo_users.find_one({'_id': user_id})
    powers = user_data.get('powers', {})
    buttons = []
    for p in ALL_POWERS:
        status = 'Yes' if powers.get(p, False) else 'No'
        buttons.append([InlineKeyboardButton(f'{p}', callback_data='noop'), InlineKeyboardButton(f'{status}', callback_data=f'toggle_{user_id}_{p}')])
    buttons.append([InlineKeyboardButton('Closed', callback_data='close_keyboard')])
    keyboard = InlineKeyboardMarkup(buttons)
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)


@app.on_callback_query(filters.regex('^close_keyboard$'))
@require_power('VIP')
async def close_keyboard(client, callback_query):
    lang = await get_effective_lang(callback_query)
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.answer(tr('Keyboard closed.', lang), show_alert=True)


def require_power(required_power):

    def decorator(func):

        @wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            lang = await get_effective_lang(message)
            if isinstance(message, CallbackQuery):
                user_id = message.from_user.id
                if user_id == OWNER_ID:
                    return await func(client, message, *args, **kwargs)
                user_data = await sudo_users.find_one({'_id': user_id})
                if not user_data or not user_data.get('powers', {}).get(required_power, False):
                    await message.answer(tr(f'You do not have the `{required_power}` power required to use this button.', lang), show_alert=True)
                    return
                return await func(client, message, *args, **kwargs)
            user_id = message.from_user.id
            if user_id == OWNER_ID:
                return await func(client, message, *args, **kwargs)
            user_data = await sudo_users.find_one({'_id': user_id})
            if not user_data or not user_data.get('powers', {}).get(required_power, False):
                await message.reply_text(tr(f'You do not have the `{required_power}` power required to use this command.', lang))
                return
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator


@app.on_message(filters.command('sudolist'))
async def sudo_list(client, message):
    lang = await get_effective_lang(message)
    if message.from_user.id != OWNER_ID:
        await message.reply_text(tr('You do not have permission to use this command.', lang))
        return
    users = await sudo_users.find().to_list(length=None)
    if not users:
        await message.reply_text(tr('There are no sudo users.', lang))
        return
    sudo_list_text = '🛠 **Sudo Users List:**\n\n'
    for user in users:
        user_id = user.get('_id')
        try:
            user_info = await client.get_users(user_id)
            first_name = user_info.first_name
        except Exception:
            first_name = 'Unknown'
        sudo_list_text += f'➤ [{first_name}](tg://user?id={user_id}) (`{user_id}`)\n'
    await message.reply_text(tr(sudo_list_text, lang))
