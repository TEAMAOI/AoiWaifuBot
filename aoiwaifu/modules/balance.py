"""User economy commands (/balance, /bal, /dailygift, /weekly, /pay)."""

from datetime import datetime, timedelta
import html
import time
from pymongo import ReturnDocument
from pyrogram import Client, enums, filters
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import Message

from aoiwaifu import app, user_collection
from aoiwaifu.admin.blocklist import is_user_blocklisted
from aoiwaifu.unit.aoi_lang import get_effective_lang, tr

pay_in_flight = set()
lock = {}


async def get_balance(user_id):
    uid = int(user_id)
    user_data = await user_collection.find_one({"id": uid}, {"balance": 1, "tokens": 1})
    if user_data:
        return (int(user_data.get("balance", 0) or 0), int(user_data.get("tokens", 0) or 0))
    return (0, 0)


async def credit_user_currency(
    user_id: int,
    coins: int = 0,
    dollars: int = 0,
    payout_key: str | None = None,
    session=None,
) -> dict:
    """Safely credit Coins (balance) and Tokens (tokens) to a user."""
    uid = int(user_id)
    coins_delta = int(coins or 0)
    dollars_delta = int(dollars or 0)
    if uid <= 0 or (coins_delta == 0 and dollars_delta == 0):
        cur_coins, cur_dollars = await get_balance(uid) if uid > 0 else (0, 0)
        return {
            "ok": uid > 0,
            "credited": False,
            "already_credited": False,
            "balance": cur_coins,
            "tokens": cur_dollars,
        }
    session_kwargs = {"session": session} if session is not None else {}
    await user_collection.update_one(
        {"id": uid},
        {"$inc": {"balance": coins_delta, "tokens": dollars_delta}},
        upsert=True,
        **session_kwargs,
    )
    new_coins, new_dollars = await get_balance(uid)
    return {
        "ok": True,
        "credited": True,
        "already_credited": False,
        "balance": new_coins,
        "tokens": new_dollars,
    }


@app.on_message(filters.command("dailygift"))
async def daily_gift(client: Client, message: Message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    if user_id in lock and time.time() - lock[user_id] < 5:
        await message.reply_text(tr("⏰ Please wait before using this command again.", lang))
        return
    lock[user_id] = time.time()

    user_data = await user_collection.find_one({"id": user_id}, {"last_daily": 1, "balance": 1})
    today = datetime.now().date()
    if user_data and "last_daily" in user_data:
        last_daily = user_data["last_daily"]
        if isinstance(last_daily, datetime):
            last_daily = last_daily.date()
        elif isinstance(last_daily, str):
            last_daily = datetime.fromisoformat(last_daily).date()
        if last_daily == today:
            await message.reply_text(
                tr("🎁 You have already claimed your daily gift today! Come back tomorrow.", lang)
            )
            return

    daily_amount = 100
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": daily_amount}, "$set": {"last_daily": datetime.now()}},
        upsert=True,
    )
    new_balance, _ = await get_balance(user_id)
    user_name = html.escape(message.from_user.first_name or "User")
    await message.reply_text(
        tr(f"🎁 {user_name}, you received your daily gift!\n💰 +{daily_amount} coins (Total: {new_balance:,} coins)", lang)
    )


@app.on_message(filters.command("weekly"))
async def weekly_gift(client: Client, message: Message):
    lang = await get_effective_lang(message)
    user_id = message.from_user.id
    if user_id in lock and time.time() - lock[user_id] < 5:
        await message.reply_text(tr("⏰ Please wait before using this command again.", lang))
        return
    lock[user_id] = time.time()

    user_data = await user_collection.find_one({"id": user_id}, {"last_weekly": 1, "balance": 1})
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    if user_data and "last_weekly" in user_data:
        last_weekly = user_data["last_weekly"]
        if isinstance(last_weekly, str):
            last_weekly = datetime.fromisoformat(last_weekly)
        if last_weekly >= week_start:
            next_week = week_start + timedelta(days=7)
            days_left = max(1, (next_week - now).days)
            await message.reply_text(
                tr(f"🎁 You have already claimed your weekly gift! Next gift available in {days_left} days.", lang)
            )
            return

    weekly_amount = 2000
    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": weekly_amount}, "$set": {"last_weekly": datetime.now()}},
        upsert=True,
    )
    new_balance, _ = await get_balance(user_id)
    user_name = html.escape(message.from_user.first_name or "User")
    await message.reply_text(
        tr(f"🎉 {user_name}, you received your weekly gift!\n💰 +{weekly_amount} coins (Total: {new_balance:,} coins)", lang)
    )


@app.on_message(filters.command(["balance", "bal"]))
async def balance(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in lock and time.time() - lock[user_id] < 2:
        return
    lock[user_id] = time.time()
    lang = await get_effective_lang(message, user_id=user_id)
    user_balance, user_tokens = await get_balance(user_id)
    user_name = html.escape(message.from_user.first_name or "User")
    response = (
        f"╭━━━〔 💰 𝐖𝐀𝐋𝐋𝐄𝐓 〕━━━╮\n"
        f"<blockquote>👤 <b>Collector:</b> {user_name}\n"
        f"💰 <b>Coins:</b> <code>{user_balance:,}</code>\n"
        f"🪙 <b>Tokens:</b> <code>{user_tokens:,}</code></blockquote>\n"
        f"╰━━━━━━━━━━━━━━━━━╯"
    )
    await message.reply_text(tr(response, lang), parse_mode=enums.ParseMode.HTML)


@app.on_message(filters.command("pay"))
async def pay(client: Client, message: Message):
    lang = await get_effective_lang(message)
    sender_id = message.from_user.id
    if await is_user_blocklisted(sender_id):
        return await message.reply_text(tr("🚫 Your account is blocklisted. Payments are disabled.", lang))
    if sender_id in lock and time.time() - lock[sender_id] < 3:
        await message.reply_text(tr("⏰ Please wait before sending another payment.", lang))
        return
    if sender_id in pay_in_flight:
        await message.reply_text(tr("⏳ Your previous payment is still processing.", lang))
        return

    args = message.command or []
    recipient_id = None
    recipient_name = None
    amount_raw = None

    if message.reply_to_message and message.reply_to_message.from_user:
        if len(args) < 2:
            await message.reply_text(tr("Usage: Reply to a user with `/pay <amount>`", lang))
            return
        recipient_id = message.reply_to_message.from_user.id
        recipient_name = message.reply_to_message.from_user.first_name or str(recipient_id)
        amount_raw = args[1]
    elif len(args) >= 3:
        target = args[1].strip()
        amount_raw = args[2]
        if target.lstrip("-").isdigit():
            recipient_id = int(target)
            recipient_name = f"User {recipient_id}"
        else:
            uname = target.lstrip("@")
            doc = await user_collection.find_one({"username": uname}, {"id": 1, "first_name": 1})
            if not doc:
                await message.reply_text(tr("❌ Recipient not found.", lang))
                return
            recipient_id = int(doc["id"])
            recipient_name = doc.get("first_name") or f"@{uname}"
    else:
        await message.reply_text(tr("Usage: `/pay <amount>` (reply) or `/pay <user_id/@username> <amount>`", lang))
        return

    if recipient_id == sender_id:
        await message.reply_text(tr("❌ You cannot pay yourself.", lang))
        return
    if await is_user_blocklisted(recipient_id):
        await message.reply_text(tr("🚫 Recipient is blocklisted and cannot receive payments.", lang))
        return

    try:
        amount = int(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text(tr("❌ Please enter a valid positive amount.", lang))
        return

    pay_in_flight.add(sender_id)
    lock[sender_id] = time.time()
    try:
        debited = await user_collection.find_one_and_update(
            {"id": sender_id, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount}},
            return_document=ReturnDocument.AFTER,
        )
        if not debited:
            await message.reply_text(tr("❌ Insufficient balance.", lang))
            return

        await user_collection.update_one(
            {"id": recipient_id},
            {"$inc": {"balance": amount}},
            upsert=True,
        )
        sender_name = html.escape(message.from_user.first_name or "User")
        safe_recipient = html.escape(str(recipient_name))
        await message.reply_text(
            tr(
                f"✅ <b>Payment Successful!</b>\n"
                f"💸 {sender_name} sent <code>{amount:,}</code> coins to {safe_recipient}.",
                lang,
            ),
            parse_mode=enums.ParseMode.HTML,
        )
        try:
            await client.send_message(
                recipient_id,
                tr(f"💰 You received <code>{amount:,}</code> coins from {sender_name}!", lang),
                parse_mode=enums.ParseMode.HTML,
            )
        except PeerIdInvalid:
            pass
        except Exception:
            pass
    finally:
        pay_in_flight.discard(sender_id)
