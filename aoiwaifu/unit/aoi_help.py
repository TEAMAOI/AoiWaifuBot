"""Interactive Help Menu definitions for AoiWaifu Bot."""

HELP_DATA = {
    "guess": {
        "HELP_NAME": "🎯 Catch",
        "HELP": (
            "Catch anime characters that spawn in groups:\n\n"
            "• `/guess <name>` (or `/protecc`, `/collect`, `/grab`, `/hunt`) — Catch the spawned character and earn coins."
        ),
    },
    "harem": {
        "HELP_NAME": "🌸 Harem",
        "HELP": (
            "Manage and browse your character collection:\n\n"
            "• `/harem` or `/collection` — View your collected characters\n"
            "• `/hmode` — Filter your harem by rarity\n"
            "• `/fav <id>` — Set your favorite character\n"
            "• `/pin <id>` / `/unpin <id>` / `/pinlist` — Pin up to 10 characters at the top of inline harem"
        ),
    },
    "profile": {
        "HELP_NAME": "👤 Profile",
        "HELP": (
            "View collector stats and rankings:\n\n"
            "• `/profile` or `/stats` — View your collector profile, rank, and rarity breakdown\n"
            "• `/rank` — View global top collectors\n"
            "• `/ctop` — Top collectors in the current group\n"
            "• `/TopGroups` — Top 10 groups globally"
        ),
    },
    "balance": {
        "HELP_NAME": "💰 Economy",
        "HELP": (
            "Manage your coins and rewards:\n\n"
            "• `/balance` or `/bal` — Check your Coins & Tokens\n"
            "• `/dailygift` — Claim your daily coin reward\n"
            "• `/weekly` — Claim your weekly coin reward\n"
            "• `/pay <amount>` — Send coins to another user (reply or pass ID/@username)\n"
            "• `/shop` — Buy characters with coins\n"
            "• `/hclaim` or `/claim` — Claim your daily character"
        ),
    },
    "trade": {
        "HELP_NAME": "🤝 Trade & Gift",
        "HELP": (
            "Exchange characters with other collectors:\n\n"
            "• `/trade <your_char_id> <their_char_id>` — Reply to a user to propose a trade\n"
            "• `/gift <char_id>` — Reply to a user to gift a character\n"
            "• `/redeem <code>` — Redeem a character code\n"
            "• `/refer` — Invite friends and earn coin rewards"
        ),
    },
    "search": {
        "HELP_NAME": "🔍 Search",
        "HELP": (
            "Explore the character database:\n\n"
            "• `/check <id>` — View details of a character by ID\n"
            "• `/sips <name>` — Search characters by name with inline preview\n"
            "• `/rarity` — View all character rarities\n"
            "• `/total` — Total characters in the database\n"
            "• `/addchar <name> <anime>` — Reply to an image to request adding a character\n"
            "• Inline mode: type `@BotUsername <query>` in any chat"
        ),
    },
    "lang": {
        "HELP_NAME": "🌐 Language",
        "HELP": (
            "Customize bot language:\n\n"
            "• `/lang` or `/settings` — Choose from 10 supported languages for DM or Group"
        ),
    },
    "admin": {
        "HELP_NAME": "🛡️ Admin",
        "HELP": (
            "Admin & Sudo commands (located in `aoiwaifu/admin/`):\n\n"
            "• `/gupload <name> <anime> <rarity>` — Upload character (ImgBB)\n"
            "• `/gupdate`, `/maxupdate`, `/gdelete`, `/rdelete`, `/reupload` — Manage characters\n"
            "• `/find`, `/findani` — Find next available ID or search anime\n"
            "• `/ctime <count>` — Set group character spawn message threshold\n"
            "• `/cgen <char_id> <limit>` — Generate a character redeem code\n"
            "• `/add`, `/kill`, `/transfer`, `/backtransfer` — Manage user data & currency\n"
            "• `/blocklist`, `/removeblocklist`, `/addblocklistgc`, `/removeblocklistgc` — Blocklists\n"
            "• `/bcast`, `/saddsudo`, `/sremovesudo`, `/seditsudo`, `/sudolist`, `/list`, `/groups`, `/backup`, `/eval`"
        ),
    },
}
