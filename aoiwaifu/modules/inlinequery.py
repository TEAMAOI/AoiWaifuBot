from aoiwaifu.unit.aoi_lang import get_user_lang, get_chat_lang, get_effective_lang, set_user_lang, set_chat_lang, has_user_set_lang, t, tr
import re
import time
from html import escape
from cachetools import TTLCache

from telegram import (
    Update,
    User,
    InlineQuery,
    InlineQueryResultPhoto,
    InlineQueryResultVideo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import InlineQueryHandler, ContextTypes

from aoiwaifu import app, application, user_collection
from aoiwaifu.unit.aoi_inline import *

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)


async def inlinequery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_effective_lang(update)
    inline_query = update.inline_query
    query = inline_query.query or ""
    stripped_query = query.strip()
    lower_query = stripped_query.lower()
    offset = int(inline_query.offset) if inline_query.offset else 0

    # /sips See button: show only the 10 matching characters from the selected page.
    see_match = re.match(r"^see\.(.+)\.(\d+)$", stripped_query, re.IGNORECASE)
    see_page = int(see_match.group(2)) if see_match else None
    if see_match:
        query = see_match.group(1).strip()
        stripped_query = query
        lower_query = query.lower()


    if query.startswith("collection."):
        user_id, *search_terms = (
            query.split(" ")[0].split(".")[1],
            " ".join(query.split(" ")[1:]),
        )
        if user_id.isdigit():
            # Always read the latest collection and /hmode setting.
            # This avoids stale inline results after a user changes their filter.
            user = await user_collection.find_one({"id": int(user_id)})
            if user:
                user_collection_cache[user_id] = user
                all_characters = list(
                    {
                        str(char["id"]): char
                        for char in (user.get("characters") or [])
                        if isinstance(char, dict) and "id" in char
                    }.values()
                )
                filter_rarity = user.get("filter_rarity")
                if filter_rarity:
                    all_characters = [
                        char for char in all_characters
                        if char.get("rarity") == filter_rarity
                    ]
                if search_terms and " ".join(search_terms).strip():
                    regex = re.compile(" ".join(search_terms), re.IGNORECASE)
                    all_characters = [
                        char
                        for char in all_characters
                        if regex.search(char.get("name", ""))
                        or regex.search(char.get("anime", ""))
                    ]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        user = None
        if query:
            all_characters = await search_characters(query)
        else:
            all_characters = (
                all_characters_cache.get("all_characters")
                or await get_all_characters()
            )
            all_characters_cache["all_characters"] = all_characters

    if ".AMV" in query:
        all_characters = [char for char in all_characters if "vid_url" in char]
    else:
        all_characters = [char for char in all_characters if "img_url" in char]

    # Keep pinned characters first, in the user's chosen pin order.
    # Rarity filtering above runs first, so pins of other rarities stay hidden.
    if user and query.startswith("collection."):
        pinned_ids = [
            str(cid) for cid in (user.get("pinned_characters") or [])
        ]
        pin_order = {character_id: index for index, character_id in enumerate(pinned_ids)}
        all_characters.sort(
            key=lambda char: (
                0 if str(char.get("id")) in pin_order else 1,
                pin_order.get(str(char.get("id")), len(pin_order)),
            )
        )

    if see_page is not None:
        page_offset = (see_page - 1) * 10
        characters = all_characters[page_offset : page_offset + 10]
        next_offset = ""
    else:
        characters = all_characters[offset : offset + 50]
        next_offset = (
            str(offset + len(characters))
            if offset + len(characters) < len(all_characters)
            else ""
        )

    results = []

    for character in characters:
        char_name = escape(str(character.get("name", "Unknown")))
        char_anime = escape(str(character.get("anime", "Unknown")))
        char_rarity = escape(str(character.get("rarity", "Unknown")))
        char_id = escape(str(character.get("id", "Unknown")))

        if user:
            user_character_count = sum(
                1
                for char in user["characters"]
                if "id" in char and char["id"] == character["id"]
            )
            owner_name = escape(str(user.get("first_name", "Collector")))
            caption = (
                f"╭━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐇𝐀𝐑𝐄𝐌 〕━╮\n"
                f"👤 <b>Collector:</b> <a href='tg://user?id={user['id']}'>{owner_name}</a>\n\n"
                f"<blockquote>💮 <b>Name:</b> {char_name} <code>(x{user_character_count})</code>\n"
                f"🌸 <b>Anime:</b> {char_anime}\n"
                f"💎 <b>Rarity:</b> {char_rarity}\n"
                f"🆔 <b>ID:</b> <code>#{char_id}</code></blockquote>\n"
                f"╰━━━━━━━━━━━━━━━━━━╯"
            )
        else:
            caption = (
                f"╭━〔 🌸 𝐀𝐎𝐈 𝐖𝐀𝐈𝐅𝐔 ✦ 𝐂𝐀𝐑𝐃 〕━╮\n\n"
                f"<blockquote>💮 <b>Name:</b> {char_name}\n"
                f"🌸 <b>Anime:</b> {char_anime}\n"
                f"💎 <b>Rarity:</b> {char_rarity}\n"
                f"🆔 <b>ID:</b> <code>#{char_id}</code></blockquote>\n\n"
                f"╰━━━━━━━━━━━━━━━━━━╯"
            )

        result_id = f"{character.get('id', 'unknown')}_{time.time_ns()}"

        if "vid_url" in character:
            results.append(
                InlineQueryResultVideo(
                    id=result_id,
                    video_url=character["vid_url"],
                    mime_type="video/mp4",
                    thumbnail_url=character.get(
                        "thum_url", "https://envs.sh/6Y3.jpg"
                    ),
                    title=str(character.get("name", "Unknown")),
                    description=(
                        f"🌸 {character.get('anime', 'Unknown')} | "
                        f"💎 {character.get('rarity', 'Unknown')}"
                    ),
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Who Have It", callback_data=f"whohaveit_{char_id}")]]),
                )
            )
        elif "img_url" in character:
            results.append(
                InlineQueryResultPhoto(
                    id=result_id,
                    photo_url=character["img_url"],
                    thumbnail_url=character["img_url"],
                    title=str(character.get("name", "Unknown")),
                    description=(
                        f"🌸 {character.get('anime', 'Unknown')} | "
                        f"💎 {character.get('rarity', 'Unknown')}"
                    ),
                    caption=caption,
                    parse_mode="HTML",
                )
            )

    # Use the Application bot directly instead of InlineQuery.answer().
    # The bridged InlineQuery object is synthetic and may not retain PTB's bot association.
    await context.bot.answer_inline_query(
        inline_query_id=inline_query.id,
        results=results,
        next_offset=next_offset,
        cache_time=5,
    )


# PTB Application owns the InlineQueryHandler.
application.add_handler(InlineQueryHandler(inlinequery, block=False))


@app.on_inline_query(group=100)
async def bridge_pyrogram_inline_to_ptb(client, inline_query):
    """
    Pyrogram remains the single Telegram update receiver.
    The actual inline handler is executed by python-telegram-bot Application.
    This avoids a second polling consumer for the same bot token.
    """
    lang = await get_effective_lang(inline_query)
    from_user = inline_query.from_user
    ptb_user = User(
        id=from_user.id,
        first_name=from_user.first_name or "User",
        is_bot=bool(from_user.is_bot),
        last_name=from_user.last_name,
        username=from_user.username,
        language_code=from_user.language_code,
    )

    ptb_inline_query = InlineQuery(
        id=inline_query.id,
        from_user=ptb_user,
        query=inline_query.query or "",
        offset=inline_query.offset or "",
        chat_type=(getattr(inline_query.chat_type, "value", inline_query.chat_type) if inline_query.chat_type else None),
    )

    ptb_update = Update(
        update_id=abs(hash(inline_query.id)) % 2147483647,
        inline_query=ptb_inline_query,
    )
    ptb_update.set_bot(application.bot)

    await application.process_update(ptb_update)
