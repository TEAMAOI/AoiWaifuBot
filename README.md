# 🌸 AoiWaifu Bot

A clean, modular Telegram **Anime Character Catcher & Waifu Collector Bot** built with **Kurigram/Pyrogram**, **python-telegram-bot**, and **MongoDB**.

## 🚀 One-Click Deploy on Aoi Hosting

[![Deploy on Aoi Hosting](https://host-repository.vercel.app/deploy-button.svg)](https://host-repository.vercel.app/deploy?template=https://github.com/OWNER/REPO)

> **Note:** After pushing this repo to GitHub, replace `OWNER/REPO` in the button URL above with your actual GitHub `username/repo`.

## ✨ Features

- **Group Character Drops & Catching**: Automatic character spawns in groups with `/guess`, `/protecc`, `/collect`, `/grab`, `/hunt`.
- **Harem & Collection Management**: `/harem`, `/hmode` rarity filter, `/fav`, `/pin`, `/unpin`, `/pinlist`, and full inline search.
- **Economy & Trading**: `/balance`, `/dailygift`, `/weekly`, `/pay`, `/shop`, `/hclaim`, `/trade`, `/gift`, `/redeem`, `/refer`.
- **Rankings & Search**: `/profile`, `/rank`, `/ctop`, `/TopGroups`, `/check`, `/sips`, `/rarity`, `/total`.
- **Multi-Language Support**: 10 built-in languages via `/lang` and `/settings`.
- **ImgBB Character Upload**: Admin `/gupload` and `/reupload` powered by ImgBB API keys.
- **Clean Separation of Concerns**: User modules in `aoiwaifu/modules/` and all admin/sudo commands organized cleanly in `aoiwaifu/admin/`.

## 📁 Project Structure

```text
aoiwaifu/
├── config.py        # Centralized environment-based configuration
├── __init__.py      # Clients, MongoDB collections, and shared state
├── __main__.py      # Loads both user modules and admin modules
├── modules/         # Public user commands (guess, harem, profile, shop, trade, etc.)
├── admin/           # All admin/sudo/owner commands (upload, update, sudo, bcast, blocklist, etc.)
├── unit/            # Core utilities (i18n, rarity, ban, sudo, logging, spawn helper)
└── langs/           # 10 language JSON files
```

## 🛠️ Manual Setup

1. **Clone the repository** and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure environment variables**:
   Copy `.env.example` to `.env` and fill in your credentials (`API_ID`, `API_HASH`, `TOKEN`, `MONGO_URL`, `OWNER_ID`, `IMGBB_API_KEYS`, etc.).
3. **Run the bot**:
   ```bash
   python -m aoiwaifu
   ```

## ⚙️ Required Environment Variables

| Variable | Description |
| :--- | :--- |
| `API_ID` | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `TOKEN` | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `MONGO_URL` | MongoDB connection URI |
| `OWNER_ID` | Bot Owner Telegram User ID |
| `IMGBB_API_KEYS` | ImgBB API key(s) for `/gupload` and `/reupload` (comma-separated supported) |
| `GLOG` | Log channel username or chat ID |
| `CHARA_CHANNEL_ID` | Character database channel username or chat ID |

See `.env.example` or `aoi.json` for all optional variables.
