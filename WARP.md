# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Telegram Bot v2.0 for collecting messages from group chats with a built-in web admin panel. Messages are stored in PostgreSQL with support for different message types (text, photos, videos, stickers, etc.).

## Common Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot locally
python main.py

# Test health check
curl http://localhost:8000/health
```

### Environment Variables
- `TELEGRAM_TOKEN` — Required, from @BotFather
- `DATABASE_URL` — Required, PostgreSQL connection string
- `PORT` — Optional, default 8000 (Railway sets this automatically)
- `LOG_LEVEL` — Optional, default INFO
- `ADMIN_USERNAME` — Optional, for basic auth on admin panel
- `ADMIN_PASSWORD` — Optional, for basic auth on admin panel

## Architecture

### Project Structure
```
tg-bot-scraper/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration via env vars
│   ├── database.py        # Connection pool management
│   ├── models.py          # SQL queries and data access
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py    # Message handlers
│   │   └── bot.py         # Bot initialization
│   └── web/
│       ├── __init__.py
│       ├── routes.py      # Web routes and API
│       └── templates/     # Jinja2 HTML templates
├── main.py                # Entry point
└── requirements.txt
```

### Key Modules

**app/config.py** — Configuration dataclass loaded from environment variables with validation.

**app/database.py** — AsyncConnectionPool management with context managers for connections and cursors.

**app/models.py** — All SQL queries, table creation, migrations, and data access functions for the admin panel.

**app/bot/handlers.py** — Message and edited_message handlers. Saves all message types (not just text) to the database.

**app/bot/bot.py** — Bot application factory and lifecycle management (start/stop).

**app/web/routes.py** — aiohttp routes for:
- `/` — Dashboard with stats
- `/chats` — List of all chats
- `/chats/{id}` — Messages for a specific chat
- `/users` — List of users
- `/health` — Health check for Railway
- `/api/*` — JSON API endpoints

### Database Schema

**chats** — Group metadata (id, type, title, username, timestamps)

**users** — User metadata (id, is_bot, name, username, language_code, is_premium)

**messages** — Extended message storage:
- `message_type` — text, photo, video, sticker, document, etc.
- `text` / `caption` — Message content
- `reply_to_message_id` — For reply chains
- `forward_from_chat_id` — For forwards
- `edited_at` — Tracks edits
- `raw_message` — Full JSON for future analysis

### Message Flow
1. Bot receives update (message or edited_message)
2. Filters: only group/supergroup chats with from_user
3. Detects message type
4. Upserts user and chat records
5. Saves message with metadata
6. Logs operation

## Admin Panel

Web interface for viewing collected data. Features:
- Dark theme UI
- Stats dashboard
- Chat list with message counts
- Message viewer with type filters
- User list
- Optional basic auth (set ADMIN_USERNAME and ADMIN_PASSWORD)

Access at `http://localhost:PORT` or your Railway domain.

## Deployment (Railway)

Uses existing `Procfile` and `railway.json`. No changes needed.

Health check endpoint is at `/health`.

## Important Notes

1. **Privacy Mode must be DISABLED** in @BotFather for the bot to receive messages
2. Bot collects ALL message types, not just text
3. Edited messages are tracked (updates existing record)
4. Database migrations run automatically on startup
