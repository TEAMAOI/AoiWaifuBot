from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t
from aoiwaifu import *
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, CallbackQuery, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant
from itertools import groupby
import math
from html import escape
from pyrogram import enums
import asyncio

async def check_support_channel(client: Client, user_id: int) -> bool:
    if user_id == x:
        return True
    try:
        await client.get_chat_member(SUPPORT_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        print(f'Bot needs admin privileges in {SUPPORT_CHANNEL} to check membership.')
        return False
    except Exception as e:
        print(f'Error checking support channel membership: {e}')
        return False

async def fetch_user_characters(user_id):
    user = await user_collection.find_one({'id': user_id})
    if not user:
        return (None, 'You have not guessed any characters yet. Use /start and try again.')
    raw_characters = user.get('characters') or []
    if not isinstance(raw_characters, list):
        return (None, '⚠️ Your character collection data is invalid. Please contact support.')
    characters = [c for c in raw_characters if isinstance(c, dict) and c.get('id') is not None]
    if not characters:
        return (None, 'No valid characters found in your collection.')
    return (characters, None)

@app.on_message(filters.command('pin'))
async def pin_character_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if not message.from_user:
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(tr('Usage: /pin <character_id>\nExample: /pin 205', lang))
    user_id = message.from_user.id
    character_id = str(message.command[1])
    user = await user_collection.find_one({'id': user_id})
    if not user:
        return await message.reply_text(tr('Your collection is empty.', lang))
    owned = any((isinstance(char, dict) and str(char.get('id')) == character_id for char in user.get('characters') or []))
    if not owned:
        return await message.reply_text(tr("You don't own this character.", lang))
    pinned = [str(cid) for cid in user.get('pinned_characters') or []]
    if character_id in pinned:
        return await message.reply_text(tr(f'Character #{character_id} is already pinned.', lang))
    if len(pinned) >= 10:
        return await message.reply_text(tr('You can pin a maximum of 10 characters. Use /unpin <id> first.', lang))
    pinned.append(character_id)
    await user_collection.update_one({'id': user_id}, {'$set': {'pinned_characters': pinned}})
    try:
        from aoiwaifu.modules.inlinequery import user_collection_cache
        user_collection_cache.pop(str(user_id), None)
    except Exception:
        pass
    await message.reply_text(tr(f'📌 Character #{character_id} pinned. It will appear at the top of your inline collection.', lang))

@app.on_message(filters.command('unpin'))
async def unpin_character_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if not message.from_user:
        return
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text(tr('Usage: /unpin <character_id>\nExample: /unpin 205', lang))
    user_id = message.from_user.id
    character_id = str(message.command[1])
    user = await user_collection.find_one({'id': user_id})
    pinned = [str(cid) for cid in user.get('pinned_characters') or []] if user else []
    if character_id not in pinned:
        return await message.reply_text(tr(f'Character #{character_id} is not pinned.', lang))
    pinned.remove(character_id)
    await user_collection.update_one({'id': user_id}, {'$set': {'pinned_characters': pinned}})
    try:
        from aoiwaifu.modules.inlinequery import user_collection_cache
        user_collection_cache.pop(str(user_id), None)
    except Exception:
        pass
    await message.reply_text(tr(f'📌 Character #{character_id} unpinned.', lang))

@app.on_message(filters.command('pinlist'))
async def pinlist_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if not message.from_user:
        return
    user = await user_collection.find_one({'id': message.from_user.id})
    pinned = [str(cid) for cid in user.get('pinned_characters') or []] if user else []
    if not pinned:
        return await message.reply_text(tr("You haven't pinned any characters yet. Use /pin <character_id>.", lang))
    owned_by_id = {}
    for char in user.get('characters') or []:
        if isinstance(char, dict) and char.get('id') is not None:
            owned_by_id.setdefault(str(char['id']), char)
    lines = ['📌 <b>Your Pinned Characters</b>']
    for index, character_id in enumerate(pinned, 1):
        char = owned_by_id.get(character_id)
        if char:
            lines.append(f"{index}. <b>{escape(str(char.get('name', 'Unknown Character')))}</b> — {escape(str(char.get('rarity', 'Unknown')))} <code>#{escape(character_id)}</code>")
        else:
            lines.append(f'{index}. <code>#{escape(character_id)}</code>')
    lines.append(f'\n{len(pinned)}/10 pinned')
    await message.reply_text(tr('\n'.join(lines), lang), parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.command(['harem', 'collection']))
async def harem_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    page = 0
    user = await user_collection.find_one({'id': user_id})
    filter_rarity = user.get('filter_rarity', None) if user else None
    msg = await display_harem(client, message, user_id, page, filter_rarity, is_initial=True)
    if msg:
        await asyncio.sleep(180)
        try:
            await msg.delete()
        except Exception as e:
            print(f'Error deleting message: {e}')

async def display_harem(client, message, user_id, page, filter_rarity, is_initial=False, callback_query=None, force_refresh_photo=False):
    # Initialize language before any operation that can fail, so error handlers can use it too.
    lang = await get_effective_lang(callback_query or message, user_id=user_id)
    try:
        user_db = await user_collection.find_one({'id': user_id})
        fallback_name = message.from_user.first_name if is_initial and getattr(message, 'from_user', None) and message.from_user.first_name else 'Collector'
        user_first_name = (user_db.get('first_name') if user_db else None) or fallback_name
        characters, error = await fetch_user_characters(user_id)
        if error:
            if is_initial:
                return await message.reply_text(tr(error, lang))
            else:
                try:
                    await callback_query.message.edit_caption(caption=tr(error, lang))
                except Exception:
                    await callback_query.message.edit_text(tr(error, lang))
            return
        characters = sorted(characters, key=lambda x: (x.get('anime', ''), x.get('id', '')))
        if filter_rarity:
            filtered_characters = [c for c in characters if c.get('rarity') == filter_rarity]
            if not filtered_characters:
                keyboard = [[InlineKeyboardButton('Remove Filter', callback_data=f'remove_filter:{user_id}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                empty_filter_text = f'No characters found with rarity: <b>{escape(str(filter_rarity))}</b>. Click below to remove the filter.'
                if is_initial:
                    return await message.reply_text(tr(empty_filter_text, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                else:
                    try:
                        await callback_query.message.edit_caption(caption=tr(empty_filter_text, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                    except Exception:
                        await callback_query.message.edit_text(tr(empty_filter_text, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                return
            characters = filtered_characters
        total_characters = len(characters)
        amv_characters = len([c for c in characters if 'vid_url' in c])
        character_counts = {k: len(list(v)) for k, v in groupby(characters, key=lambda x: str(x.get('id', '')))}
        unique_characters = list({str(character.get('id')): character for character in characters}.values())
        total_pages = max(1, math.ceil(len(unique_characters) / 15))
        if page < 0 or page >= total_pages:
            page = 0
        lang = await get_effective_lang(callback_query or message, user_id=user_id)
        harem_message = f"╭━〔 🌸 <b>{escape(user_first_name)}'s Harem</b> • Page {page + 1}/{total_pages} 〕━╮\n"
        if filter_rarity:
            harem_message += t('harem_filtered_by', lang, rarity=escape(str(filter_rarity)))
        harem_message += '<blockquote>'
        current_characters = unique_characters[page * 15:(page + 1) * 15]
        current_grouped_characters = {k: list(v) for k, v in groupby(current_characters, key=lambda x: x.get('anime', 'Unknown Anime'))}
        for anime, chars in current_grouped_characters.items():
            total_anime_chars = await collection.count_documents({'anime': anime})
            harem_message += f'\n⛩️ <b>{escape(str(anime))}</b> <i>({len(chars)}/{total_anime_chars})</i>\n'
            for character in chars:
                count = character_counts.get(str(character.get('id')), 1)
                rarity_emoji = rarity_map2.get(character.get('rarity'), '❔')
                harem_message += f"  ✦ ⌠{rarity_emoji}⌡ <code>{escape(str(character.get('id', '?')))}</code> <b>{escape(str(character.get('name', 'Unknown Character')))}</b> (x{count})\n"
        harem_message += '</blockquote>\n╰━━━━━━━━━━━━━━━━━━╯'
        keyboard = [
            [
                InlineKeyboardButton(f'🎴 Harem ({total_characters})', switch_inline_query_current_chat=f'collection.{user_id}'),
                InlineKeyboardButton(f'💌 AMV ({amv_characters})', switch_inline_query_current_chat=f'collection.{user_id}.AMV'),
            ],
            [
                InlineKeyboardButton(t('btn_refresh', lang), callback_data=f"harem_refresh:{page}:{user_id}:{filter_rarity or 'None'}"),
            ],
        ]
        if total_pages > 1:
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton('⬅️', callback_data=f"harem:{page - 1}:{user_id}:{filter_rarity or 'None'}"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton('➡️', callback_data=f"harem:{page + 1}:{user_id}:{filter_rarity or 'None'}"))
            keyboard.append(nav_buttons)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Pick favorite character photo, else first available character photo, else PHOTO_URL[0]
        harem_photo = None
        fav_ids = (user_db.get('favorites') or []) if user_db else []
        if fav_ids:
            fav_char = next((c for c in characters if str(c.get('id')) == str(fav_ids[0]) and c.get('img_url')), None)
            if fav_char:
                harem_photo = fav_char['img_url']
        if not harem_photo:
            harem_photo = next((c.get('img_url') for c in current_characters if c.get('img_url')), None) or PHOTO_URL[0]

        if is_initial:
            try:
                return await message.reply_photo(photo=harem_photo, caption=tr(harem_message, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            except Exception:
                return await message.reply_text(tr(harem_message, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        else:
            try:
                await callback_query.message.edit_caption(caption=tr(harem_message, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
            except Exception:
                try:
                    await callback_query.message.edit_text(tr(harem_message, lang), reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
                except Exception:
                    pass
    except Exception as e:
        print(f'Error in display_harem: {e}')
        error_msg = 'An error occurred. Please try again later.'
        if is_initial:
            await message.reply_text(tr(error_msg, lang))
        elif callback_query:
            try:
                await callback_query.message.edit_caption(caption=tr(error_msg, lang))
            except Exception:
                await callback_query.message.edit_text(tr(error_msg, lang))

@app.on_callback_query(filters.regex('^remove_filter'))
async def remove_filter_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    try:
        _, user_id = callback_query.data.split(':')
        user_id = int(user_id)
        if callback_query.from_user.id != user_id:
            await callback_query.answer(tr("It's not your Harem!", lang), show_alert=True)
            return
        await user_collection.update_one({'id': user_id}, {'$set': {'filter_rarity': None}}, upsert=True)
        await callback_query.message.delete()
        await callback_query.answer(tr('Filter removed. Showing all rarities.', lang), show_alert=True)
    except Exception as e:
        print(f'Error in remove_filter callback: {e}')

@app.on_callback_query(filters.regex('^harem:'))
async def harem_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    try:
        data = callback_query.data
        _, page, user_id, filter_rarity = data.split(':')
        page = int(page)
        user_id = int(user_id)
        filter_rarity = None if filter_rarity == 'None' else filter_rarity
        if callback_query.from_user.id != user_id:
            await callback_query.answer(tr("It's not your Harem!", lang), show_alert=True)
            return
        await display_harem(client, callback_query.message, user_id, page, filter_rarity, is_initial=False, callback_query=callback_query, force_refresh_photo=False)
    except Exception as e:
        print(f'Error in harem callback: {e}')

@app.on_callback_query(filters.regex('^harem_refresh:'))
async def harem_refresh_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    try:
        data = callback_query.data
        _, page, user_id, filter_rarity = data.split(':')
        page = int(page)
        user_id = int(user_id)
        filter_rarity = None if filter_rarity == 'None' else filter_rarity
        if callback_query.from_user.id != user_id:
            await callback_query.answer(tr("It's not your Harem!", lang), show_alert=True)
            return
        await callback_query.answer(tr('🔄 Refreshing your Dress-Up Avatar...', lang))
        await display_harem(client, callback_query.message, user_id, page, filter_rarity, is_initial=False, callback_query=callback_query, force_refresh_photo=True)
    except Exception as e:
        print(f'Error in harem_refresh callback: {e}')

@app.on_message(filters.command('hmode'))
async def hmode_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    keyboard = []
    row = []
    for i, (rarity, emoji) in enumerate(rarity_map2.items(), 1):
        row.append(InlineKeyboardButton(emoji, callback_data=f'set_rarity:{user_id}:{rarity}'))
        if i % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('All', callback_data=f'set_rarity:{user_id}:None')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(tr('Select a rarity to filter your harem:', lang), reply_markup=reply_markup)

@app.on_callback_query(filters.regex('^set_rarity'))
async def set_rarity_callback(client: Client, callback_query: CallbackQuery):
    lang = await get_effective_lang(callback_query)
    try:
        _, user_id, filter_rarity = callback_query.data.split(':')
        user_id = int(user_id)
        filter_rarity = None if filter_rarity == 'None' else filter_rarity
        if callback_query.from_user.id != user_id:
            await callback_query.answer(tr("It's not your Harem!", lang), show_alert=True)
            return
        await user_collection.update_one({'id': user_id}, {'$set': {'filter_rarity': filter_rarity}}, upsert=True)
        if filter_rarity:
            await callback_query.message.edit_text(tr(f'Rarity filter set to: **{filter_rarity}**', lang))
        else:
            await callback_query.message.edit_text(tr('Rarity filter cleared. Showing all rarities.', lang))
        await callback_query.answer(tr(f"Rarity filter set to {(filter_rarity if filter_rarity else 'All')}", lang), show_alert=True)
    except Exception as e:
        print(f'Error in set_rarity callback: {e}')
