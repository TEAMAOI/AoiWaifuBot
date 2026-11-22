"""Admin economy & user data management commands (/add, /kill)."""

import html
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from aoiwaifu import app, require_power, user_collection
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr


async def _get_balance(user_id: int) -> tuple[int, int]:
    user_data = await user_collection.find_one({"id": int(user_id)}, {"balance": 1, "tokens": 1})
    if user_data:
        return (int(user_data.get("balance", 0) or 0), int(user_data.get("tokens", 0) or 0))
    return (0, 0)


def _parse_add_amount(raw_val: str) -> int:
    s = str(raw_val or "").strip().lower().replace(",", "").replace("_", "").lstrip("$")
    mult = 1
    if s.endswith("k"):
        mult = 1000
        s = s[:-1]
    elif s.endswith("m"):
        mult = 1_000_000
        s = s[:-1]
    elif s.endswith("b"):
        mult = 1_000_000_000
        s = s[:-1]
    return int(float(s) * mult)


@app.on_message(filters.command("kill"))
@require_power("VIP")
async def kill_handler(client: Client, message: Message):
    lang = await get_effective_lang(message)
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply_text(tr("Please reply to a user's message to use the /kill command.", lang))
        return

    user_id = message.reply_to_message.from_user.id
    command_args = message.text.split()
    if len(command_args) < 2:
        await message.reply_text(
            tr("Please specify an option: `c` to delete character, `f` to delete full data, or `b` to deduct balance.", lang)
        )
        return

    option = command_args[1].lower()
    try:
        if option == "f":
            await user_collection.delete_one({"id": user_id})
            await message.reply_text(tr("The full data of the user has been deleted.", lang))
        elif option == "c":
            if len(command_args) < 3:
                await message.reply_text(tr("Please specify a character ID to remove.", lang))
                return
            char_id = command_args[2]
            user = await user_collection.find_one({"id": user_id})
            if user and "characters" in user:
                characters = user["characters"]
                updated_characters = [c for c in characters if str(c.get("id")) != str(char_id)]
                if len(updated_characters) == len(characters):
                    await message.reply_text(
                        tr(f"No character with ID {char_id} found in the user's collection.", lang)
                    )
                    return
                await user_collection.update_one({"id": user_id}, {"$set": {"characters": updated_characters}})
                await message.reply_text(
                    tr(f"Character with ID {char_id} has been removed from the user's collection.", lang)
                )
            else:
                await message.reply_text(tr("No characters found in the user's collection.", lang))
        elif option == "b":
            if len(command_args) < 3:
                await message.reply_text(tr("Please specify an amount to deduct from balance.", lang))
                return
            try:
                amount = int(command_args[2])
            except ValueError:
                await message.reply_text(tr("Invalid amount. Please enter a valid number.", lang))
                return
            user_data = await user_collection.find_one({"id": user_id}, {"balance": 1})
            if user_data and "balance" in user_data:
                new_balance = max(0, int(user_data["balance"]) - amount)
                await user_collection.update_one({"id": user_id}, {"$set": {"balance": new_balance}})
                await message.reply_text(
                    tr(f"{amount} has been deducted from the user's balance. New balance: {new_balance}", lang)
                )
            else:
                await message.reply_text(tr("The user has no balance to deduct from.", lang))
        else:
            await message.reply_text(
                tr("Invalid option. Use `c {id}` for character, `f` for full data, or `b {amount}` to deduct balance.", lang)
            )
    except Exception as e:
        await message.reply_text(tr(f"An error occurred: {e}", lang))


@app.on_message(filters.command("add"))
@require_power("VIP")
async def admin_add_currency_handler(client: Client, message: Message):
    """
    Usage:
      /add c <value> [user_id/@username]  -> Adds Coins (balance)
      /add b <value> [user_id/@username]  -> Adds Tokens (tokens)
    """
    lang = await get_effective_lang(message)
    args = message.command or []
    if len(args) < 3:
        await message.reply_text(
            tr(
                "⚡ <b>Admin Currency Command</b>\n\n"
                "<b>Usage:</b>\n"
                "• <code>/add c 10000</code> — Add <b>Coins (💰)</b>\n"
                "• <code>/add b 5000</code> — Add <b>Tokens (🪙)</b>\n\n"
                "<i>Tip: Reply to a user or pass their User ID / @username as a 3rd argument.</i>",
                lang,
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    kind = args[1].strip().lower()
    try:
        amount = _parse_add_amount(args[2])
        if amount == 0:
            raise ValueError("Zero amount")
    except Exception:
        await message.reply_text(
            tr("❌ Invalid value! Example: <code>/add c 10000</code> or <code>/add b 5000</code>", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    target_id = message.from_user.id
    target_name = message.from_user.first_name or "Admin"
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name or str(target_id)
    elif len(args) >= 4:
        raw_target = args[3].strip()
        if raw_target.lstrip("-").isdigit():
            target_id = int(raw_target)
            target_name = f"User {target_id}"
        else:
            uname = raw_target.lstrip("@")
            u_doc = await user_collection.find_one({"username": uname}, {"id": 1, "first_name": 1})
            if not u_doc:
                await message.reply_text(tr(f"❌ User @{html.escape(uname)} not found in database.", lang))
                return
            target_id = int(u_doc["id"])
            target_name = u_doc.get("first_name") or f"@{uname}"

    if kind in ("c", "coin", "coins"):
        await user_collection.update_one({"id": target_id}, {"$inc": {"balance": amount}}, upsert=True)
        added_label = f"💰 +{amount:,} Coins" if amount > 0 else f"💰 {amount:,} Coins"
    elif kind in ("b", "d", "$", "dollar", "dollars", "token", "tokens", "balance", "bank"):
        await user_collection.update_one({"id": target_id}, {"$inc": {"tokens": amount}}, upsert=True)
        added_label = f"🪙 +{amount:,} Tokens" if amount > 0 else f"🪙 {amount:,} Tokens"
    elif kind in ("both", "all"):
        await user_collection.update_one(
            {"id": target_id}, {"$inc": {"balance": amount, "tokens": amount}}, upsert=True
        )
        added_label = f"💰 +{amount:,} Coins & 🪙 +{amount:,} Tokens"
    else:
        await message.reply_text(
            tr("❌ Unknown type! Use <code>c</code> for Coins or <code>b</code> for Tokens.", lang),
            parse_mode=enums.ParseMode.HTML,
        )
        return

    new_coins, new_tokens = await _get_balance(target_id)
    safe_target = html.escape(str(target_name))
    await message.reply_text(
        tr(
            f"╭━━━〔 ⚡ 𝐀𝐃𝐌𝐈𝐍 𝐂𝐑𝐄𝐃𝐈𝐓 〕━━━╮\n"
            f"│ 👤 <b>Target:</b> {safe_target} (<code>{target_id}</code>)\n"
            f"│ ✨ <b>Updated:</b> {added_label}\n"
            f"├━━━━━━━━━━━━━━━━━━━━━━\n"
            f"│ 💰 <b>Coins:</b> <code>{new_coins:,}</code>\n"
            f"│ 🪙 <b>Tokens:</b> <code>{new_tokens:,}</code>\n"
            f"╰━━━━━━━━━━━━━━━━━━━━━━╯",
            lang,
        ),
        parse_mode=enums.ParseMode.HTML,
    )
