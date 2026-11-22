from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import os
import asyncio
import requests
from pyrogram import filters
from aoiwaifu import ZYRO, collection, require_power, GLOG
UPLOAD_API = 'https://api.imgbb.com/1/upload'

def upload_to_imgbb(file_path: str) -> str:
    """Upload a local file to ImgBB, trying configured API keys in order."""
    api_keys = [key.strip() for key in os.getenv('IMGBB_API_KEYS', os.getenv('IMGBB_API_KEY', '')).split(',') if key.strip()]
    if not api_keys:
        raise Exception('ImgBB API keys are not configured. Set IMGBB_API_KEYS or IMGBB_API_KEY.')
    errors = []
    for index, api_key in enumerate(api_keys, start=1):
        try:
            with open(file_path, 'rb') as image_file:
                response = requests.post(UPLOAD_API, data={'key': api_key}, files={'image': image_file}, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('url'):
                    return data['data']['url']
                errors.append(f"key #{index}: {data.get('error', {}).get('message', 'unexpected ImgBB response')}")
            else:
                errors.append(f'key #{index}: HTTP {response.status_code} - {response.text[:200]}')
        except Exception as exc:
            errors.append(f'key #{index}: {str(exc)[:200]}')
    raise Exception('All configured ImgBB keys failed: ' + ' | '.join(errors))

async def find_char(char_id: str):
    """
    Try multiple ID formats because MongoDB may store as string "60"
    or zero-padded "60" or integer 60.
    """
    char = await collection.find_one({'id': char_id})
    if char:
        return char
    padded = char_id.zfill(2)
    if padded != char_id:
        char = await collection.find_one({'id': padded})
        if char:
            return char
    try:
        char = await collection.find_one({'id': int(char_id)})
        if char:
            return char
    except ValueError:
        pass
    return None

@ZYRO.on_message(filters.command(['reupload']))
@require_power('add_character')
async def reupload_handler(client, message):
    """
    Usage:
      /reupload 60
      /reupload 30 60 61 100
    """
    lang = await get_effective_lang(message)
    args = message.text.split()[1:]
    if not args:
        return await message.reply_text(tr('❌ **Wrong format!**\n\nUsage:\n`/reupload 60`\n`/reupload 30 60 61 100`', lang))
    status_msg = await message.reply_text(tr(f'⏳ Processing **{len(args)}** character(s)…', lang))
    results = []
    success = 0
    fail = 0
    for char_id in args:
        char_id = char_id.strip()
        path = None
        sent_msg = None
        try:
            char = await find_char(char_id)
            if not char:
                results.append(f'❌ `{char_id}` — not found in DB')
                fail += 1
                continue
            stored_id = char.get('id')
            name = char.get('name', '?')
            old_url = char.get('img_url', '')
            if not old_url:
                results.append(f'❌ `{char_id}` ({name}) — no img_url in DB')
                fail += 1
                continue
            try:
                sent_msg = await client.send_photo(chat_id=GLOG, photo=old_url, caption=tr(f'#reupload id:{char_id}', lang))
            except Exception as send_err:
                results.append(f'❌ `{char_id}` ({name}) — Telegram send failed: `{str(send_err)[:80]}`')
                fail += 1
                continue
            tmp_file = f'/tmp/reupload_{char_id}.jpg'
            path = await client.download_media(sent_msg.photo.file_id, file_name=tmp_file)
            if not path or not os.path.exists(path):
                raise Exception('Download from Telegram returned empty file')
            file_size = os.path.getsize(path)
            if file_size < 100:
                raise Exception(f'Downloaded file too small ({file_size} bytes) — image may be invalid')
            new_url = upload_to_imgbb(path)
            update_result = await collection.update_one({'id': stored_id}, {'$set': {'img_url': new_url, 'status': 'working'}})
            if update_result.matched_count == 0:
                raise Exception(f'DB match failed for id={stored_id!r} (type={type(stored_id).__name__})')
            if update_result.modified_count == 0:
                results.append(f'⚠️ `{char_id}` ({name}) — matched but not modified (same URL?)')
            else:
                results.append(f'✅ `{char_id}` **{name}**\n   └ `{new_url}`')
                success += 1
        except Exception as e:
            results.append(f'❌ `{char_id}` — `{str(e)[:120]}`')
            fail += 1
        finally:
            if sent_msg:
                try:
                    await sent_msg.delete()
                except Exception:
                    pass
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
            await asyncio.sleep(0.5)
    summary = '\n'.join(results)
    await status_msg.edit(tr(f'**📦 Reupload Complete**\n✅ Success: **{success}**  |  ❌ Failed: **{fail}**\n\n{summary}', lang))
