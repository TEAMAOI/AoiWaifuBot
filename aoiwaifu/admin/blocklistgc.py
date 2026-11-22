from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
from aoiwaifu import app, db, require_power
from pyrogram import filters
from pyrogram.types import Message
blocked_groups_collection = db['blocked_character_drop_groups']

def _parse_group_id(message: Message):
    if len(message.command) < 2:
        return None
    try:
        group_id = int(message.command[1])
    except (TypeError, ValueError):
        return None
    return group_id if group_id < 0 else None

@app.on_message(filters.command('addblocklistgc'))
@require_power('VIP')
async def add_blocklist_group(client, message: Message):
    lang = await get_effective_lang(message)
    group_id = _parse_group_id(message)
    if group_id is None:
        await message.reply_text(tr('❌ Invalid group ID.\nUsage: /addblocklistgc -1001234567890', lang))
        return
    chat = await blocked_groups_collection.find_one({'_id': group_id})
    if chat:
        await message.reply_text(tr(f'ℹ️ Group `{group_id}` is already on the character-drop blocklist.', lang))
        return
    await blocked_groups_collection.update_one({'_id': group_id}, {'$set': {'chat_id': group_id, 'blocked_by': message.from_user.id}}, upsert=True)
    notice = '🚫 <b>This group has been blocklisted by the bot administrator.</b>\n\nCharacter drops are disabled in this group, so no characters can appear for grabbing.'
    try:
        await client.send_message(group_id, notice, parse_mode='html')
        await message.reply_text(tr(f'✅ Group `{group_id}` has been added to the character-drop blocklist. Notification sent.', lang))
    except Exception as exc:
        await message.reply_text(tr(f"✅ Group `{group_id}` was added to the blocklist, but I couldn't send the notification. Please make sure the bot is still in that group and can send messages.", lang))
        print(f'Could not notify blocklisted group {group_id}: {exc}')

@app.on_message(filters.command('removeblocklistgc'))
@require_power('VIP')
async def remove_blocklist_group(client, message: Message):
    lang = await get_effective_lang(message)
    group_id = _parse_group_id(message)
    if group_id is None:
        await message.reply_text(tr('❌ Invalid group ID.\nUsage: /removeblocklistgc -1001234567890', lang))
        return
    result = await blocked_groups_collection.delete_one({'_id': group_id})
    if not result.deleted_count:
        await message.reply_text(tr(f'ℹ️ Group `{group_id}` is not on the character-drop blocklist.', lang))
        return
    await message.reply_text(tr(f'✅ Group `{group_id}` has been removed from the character-drop blocklist. Character drops can resume when the next spawn threshold is reached.', lang))

@app.on_message(filters.command('blocklistgc'))
@require_power('VIP')
async def list_blocklist_groups(client, message: Message):
    lang = await get_effective_lang(message)
    groups = await blocked_groups_collection.find({}).to_list(length=100)
    if not groups:
        await message.reply_text(tr('✅ The character-drop blocklist is empty.', lang))
        return
    group_ids = [str(item.get('chat_id', item.get('_id'))) for item in groups]
    text = '🚫 <b>Character-Drop Blocklist</b>\n\n' + '\n'.join((f'• <code>{group_id}</code>' for group_id in group_ids))
    await message.reply_text(tr(text, lang), parse_mode='html')
