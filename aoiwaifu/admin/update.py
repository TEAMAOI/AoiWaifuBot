from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pymongo import ReturnDocument
from aoiwaifu import collection, SUDO, app, user_collection, require_power
from aoiwaifu.unit.aoi_rarity import rarity_map
SUDO_USERS = SUDO

@app.on_message(filters.command('gdelete'))
@require_power('delete_character')
async def delete_handler(client, message):
    lang = await get_effective_lang(message)
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply_text(tr('Incorrect format... Please use: /gdelete ID', lang))
            return
        character_id = args[1]
        character = await collection.find_one_and_delete({'id': character_id})
        if character:
            update_result = await user_collection.update_many({'characters.id': character_id}, {'$pull': {'characters': {'id': character_id}}})
            await message.reply_text(tr(f'Character with ID {character_id} deleted successfully from the database.\nRemoved from {update_result.modified_count} user collections.', lang))
        else:
            await message.reply_text(tr(f'Character with ID {character_id} not found in the database.', lang))
    except Exception as e:
        await message.reply_text(tr(f'Error: {str(e)}', lang))
import time

@app.on_message(filters.command('gupdate'))
@require_power('update_character')
async def update(client: Client, message: Message):
    lang = await get_effective_lang(message)
    try:
        args = message.text.split()
        if len(args) != 4:
            await message.reply_text(tr('Incorrect format. Please use: /gupdate id field new_value', lang))
            return
        character_id = args[1]
        field_to_update = args[2]
        new_value = args[3]
        valid_fields = ['img_url', 'name', 'anime', 'rarity']
        if field_to_update not in valid_fields:
            await message.reply_text(tr(f"Invalid field. Please use one of the following: {', '.join(valid_fields)}", lang))
            return
        if field_to_update in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field_to_update == 'rarity':
            try:
                new_value = rarity_map[int(new_value)]
            except (KeyError, ValueError):
                await message.reply_text(tr(f'Invalid rarity number. Choose a number from 1 to {len(rarity_map)}.', lang))
                return
        result = await collection.update_one({'id': character_id}, {'$set': {field_to_update: new_value}})
        if result.modified_count == 0:
            await message.reply_text(tr('Character not found or no changes made.', lang))
            return
        users_cursor = user_collection.find({'characters.id': character_id})
        total_users = await user_collection.count_documents({'characters.id': character_id})
        if total_users == 0:
            await message.reply_text(tr('sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇ ✅', lang))
            return
        progress_message = await message.reply_text(tr('Updating: 0% completed...', lang))
        updated_count = 0
        progress_threshold = 10
        next_progress_update = progress_threshold
        async for user in users_cursor:
            await user_collection.update_one({'_id': user['_id'], 'characters.id': character_id}, {'$set': {f'characters.$.{field_to_update}': new_value}})
            updated_count += 1
            progress = updated_count / total_users * 100
            if progress >= next_progress_update:
                await progress_message.edit_text(tr(f'Updating: {int(progress)}% completed...', lang))
                next_progress_update += progress_threshold
                await asyncio.sleep(0.2)
        await progress_message.edit_text(tr('Updating: 100% completed.', lang))
        await message.reply_text(tr(f'sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇ ✅ \nTotal users updated: {updated_count}/{total_users}', lang))
    except Exception as e:
        await message.reply_text(tr(f'Error: {str(e)}', lang))
import time

@app.on_message(filters.command('maxupdate'))
@require_power('update_character')
async def update_multiple(client: Client, message: Message):
    lang = await get_effective_lang(message)
    try:
        args = message.text.split()
        if len(args) < 4:
            await message.reply_text(tr('Incorrect format. Use: /maxupdate id1,id2,id3 field new_value', lang))
            return
        character_ids = args[1].split(',')
        field_to_update = args[2]
        new_value = ' '.join(args[3:])
        valid_fields = ['img_url', 'vid_url', 'name', 'anime', 'rarity']
        if field_to_update not in valid_fields:
            await message.reply_text(tr(f"Invalid field. Use one of: {', '.join(valid_fields)}", lang))
            return
        if field_to_update in ['name', 'anime']:
            new_value = new_value.replace('-', ' ').title()
        elif field_to_update == 'rarity':
            try:
                new_value = rarity_map[int(new_value)]
            except (KeyError, ValueError):
                await message.reply_text(tr(f'Invalid rarity number. Choose a number from 1 to {len(rarity_map)}.', lang))
                return
        total_characters = len(character_ids)
        updated_characters = 0
        total_users_updated = 0
        progress_message = await message.reply_text(tr('Updating: 0% completed...', lang))
        next_progress_update = 10
        for i, character_id in enumerate(character_ids, start=1):
            result = await collection.update_one({'id': character_id}, {'$set': {field_to_update: new_value}})
            if result.modified_count == 0:
                continue
            users_cursor = user_collection.find({'characters.id': character_id})
            async for user in users_cursor:
                await user_collection.update_one({'_id': user['_id'], 'characters.id': character_id}, {'$set': {f'characters.$.{field_to_update}': new_value}})
                total_users_updated += 1
            updated_characters += 1
            progress = i / total_characters * 100
            if progress >= next_progress_update:
                await progress_message.edit_text(tr(f'Updating: {int(progress)}% completed...', lang))
                next_progress_update += 10
                await asyncio.sleep(0.2)
        await progress_message.edit_text(tr('Updating: 100% completed.', lang))
        await message.reply_text(tr(f'sᴜᴄᴄᴇssғᴜʟʟʏ ᴜᴘᴅᴀᴛᴇ ✅ \nTotal characters updated: {updated_characters}/{total_characters}. Total users updated: {total_users_updated}.', lang))
    except Exception as e:
        await message.reply_text(tr(f'Error: {str(e)}', lang))

@app.on_message(filters.command('findani') & filters.user(SUDO_USERS))
async def find_anime_ids(client: Client, message: Message):
    lang = await get_effective_lang(message)
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text(tr('Please provide an anime name. Usage: /findani {anime name}', lang))
            return
        anime_name = args[1].strip().lower()
        characters_cursor = collection.find({'anime': {'$regex': f'^{anime_name}$', '$options': 'i'}}, {'id': 1})
        character_ids = [str(character['id']) for character in await characters_cursor.to_list(length=None)]
        if not character_ids:
            await message.reply_text(tr(f'No characters found for anime name: {anime_name}', lang))
        else:
            ids_list = ','.join(character_ids)
            await message.reply_text(tr(f"Character IDs for '{anime_name}':\n{ids_list}", lang))
    except Exception as e:
        await message.reply_text(tr(f'Error: {str(e)}', lang))


# Delete every character belonging to a rarity (VIP only).
@app.on_message(filters.command('rdelete'))
@require_power('VIP')
async def rarity_delete_handler(client, message):
    lang = await get_effective_lang(message)
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.reply_text(tr(f'Usage: /rdelete rarity_number (1-{len(rarity_map)})', lang))
        return

    rarity_number = int(args[1])
    rarity_name = rarity_map.get(rarity_number)
    if not rarity_name:
        await message.reply_text(tr(f'Invalid rarity number. Choose 1 to {len(rarity_map)}.', lang))
        return

    count = await collection.count_documents({'rarity': rarity_name})
    if count == 0:
        await message.reply_text(tr(f'No characters found for rarity: {rarity_name}', lang))
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('⚠️ Confirm Delete', callback_data=f'rdel_yes_{rarity_number}_{message.from_user.id}'),
            InlineKeyboardButton('❌ Cancel', callback_data=f'rdel_no_{message.from_user.id}')
        ]
    ])
    await message.reply_text(
        tr(f'⚠️ **WARNING: PERMANENT BULK DELETE**\n\nRarity: {rarity_name}\nCharacters found: {count}\n\nConfirm karne par is rarity ke ALL characters main database aur users ke harem se delete ho jayenge. This action cannot be undone.', lang),
        reply_markup=keyboard
    )


@app.on_callback_query(filters.regex(r'^rdel_(yes_(\d+)|(no))_(\d+)$'))
@require_power('VIP')
async def rarity_delete_confirm(client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    action = callback_query.matches[0].group(1)
    owner_id = int(callback_query.matches[0].group(4))
    if callback_query.from_user.id != owner_id:
        await callback_query.answer(tr('This confirmation belongs to another user.', lang), show_alert=True)
        return

    if action == 'no':
        await callback_query.message.edit_text(tr('❌ Rarity deletion cancelled.', lang))
        await callback_query.answer()
        return

    rarity_number = int(callback_query.matches[0].group(2))
    rarity_name = rarity_map.get(rarity_number)
    if not rarity_name:
        await callback_query.answer(tr('Invalid rarity.', lang), show_alert=True)
        return

    matching = await collection.find({'rarity': rarity_name}, {'id': 1}).to_list(length=None)
    character_ids = [str(item['id']) for item in matching if item.get('id') is not None]
    if not character_ids:
        await callback_query.message.edit_text(tr('No matching characters remain. Nothing was deleted.', lang))
        await callback_query.answer()
        return

    result = await collection.delete_many({'rarity': rarity_name})
    users_result = await user_collection.update_many(
        {'characters.id': {'$in': character_ids}},
        {'$pull': {'characters': {'id': {'$in': character_ids}}}}
    )
    await callback_query.message.edit_text(
        tr(f'✅ **Rarity deletion completed**\n\nRarity: {rarity_name}\nDeleted characters: {result.deleted_count}\nUser collections updated: {users_result.modified_count}', lang)
    )
    await callback_query.answer('Deletion completed.', show_alert=True)
