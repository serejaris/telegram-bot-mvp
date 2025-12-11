```
  _______   _                                 ____        _
 |__   __| | |                               |  _ \      | |
    | | ___| | ___  __ _ _ __ __ _ _ __ ___  | |_) | ___ | |_
    | |/ _ \ |/ _ \/ _` | '__/ _` | '_ ` _ \ |  _ < / _ \| __|
    | |  __/ |  __/ (_| | | | (_| | | | | | || |_) | (_) | |_
    |_|\___|_|\___|\__, |_|  \__,_|_| |_| |_||____/ \___/ \__|
                    __/ |
                   |___/
```

# Telegram Bot MVP for Message Collection

This bot is an MVP (Minimum Viable Product) for collecting text messages from Telegram group chats and saving them to a PostgreSQL database.

## API Endpoints

### Health Check (No Authorization)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check service and DB status |

### Web Pages (Basic Auth required if configured)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard with statistics |
| GET | `/chats` | List of all chats |
| GET | `/chats/{chat_id}` | Messages of a specific chat |
| GET | `/users` | List of users |

### JSON API (Basic Auth required if configured)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | General statistics (chats, users, messages) |
| GET | `/api/chats` | List of chats with message count |
| GET | `/api/chats/{chat_id}/messages` | Chat messages (`?limit=100&offset=0&type=text`) |
| GET | `/api/chats/{chat_id}/messages/daily` | Daily messages (**required**: `?date=YYYY-MM-DD`, UTC+3) |

> **Note:** `chat_id` for groups/supergroups is always negative (e.g., `-1001234567890`)

### Request Examples
```bash
# Health check
curl https://your-domain.railway.app/health

# API with authorization
curl -u admin:password https://your-domain.railway.app/api/stats

# Daily chat messages
curl -u admin:password "https://your-domain.railway.app/api/chats/-1001234567890/messages/daily?date=2024-12-01"
```

## Features

- Listens to all text messages in group chats
- Saves information about messages, users, and chats to PostgreSQL
- Uses asynchronous approach for high performance
- Prevents message duplicates using UPSERT operations
- Works in long-polling mode for easy deployment

## Requirements

- Python 3.12+
- PostgreSQL 12+
- Telegram Bot Token (get via @BotFather)

## Deployment Options

### 🚀 Railway (Recommended for Production)

For deployment on Railway, see the detailed guide: [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)

**Quick Start on Railway:**
1. Fork the repository on GitHub
2. Create a project on [railway.app](https://railway.app)
3. Connect GitHub repository
4. Add PostgreSQL service
5. Set `TELEGRAM_TOKEN` variable
6. Done! 🎉

### 💻 Local Run

## Installation and Setup

### 1. Create Tables in PostgreSQL

Execute the following SQL script in your PostgreSQL database:

```sql
-- Chats table
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    type VARCHAR(255) NOT NULL,
    title TEXT,
    username VARCHAR(255) UNIQUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_bot BOOLEAN NOT NULL,
    first_name TEXT,
    last_name TEXT,
    username VARCHAR(255) UNIQUE,
    language_code VARCHAR(10),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    text TEXT,
    sent_at TIMESTAMPTZ NOT NULL,
    raw_message JSONB,

    PRIMARY KEY (chat_id, message_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for query optimization
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_chats_username ON chats(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
```

**Note:** Tables are also created automatically on the first bot run if they do not exist.

### 2. Environment Variables Configuration

Set the following environment variables:

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export DATABASE_URL="postgresql://username:password@localhost:5432/database_name"
```

Or create a `.env` file (don't forget to add it to `.gitignore`):

```
TELEGRAM_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python main.py
```

## Important Settings

### Disable Privacy Mode

**CRITICAL:** For the bot to work in group chats, you must disable Privacy Mode via @BotFather:

1. Open chat with @BotFather
2. Send command `/setprivacy`
3. Select your bot
4. Choose `Disable` to disable Privacy Mode

Without this setting, the bot will not receive messages in group chats!

### Adding Bot to Group Chat

1. Add the bot to the desired group chat
2. Ensure the bot has rights to read messages
3. The bot will automatically start saving all text messages

## Database Structure

### `chats` Table
- `id` - Chat ID in Telegram
- `type` - chat type (group, supergroup)
- `title` - chat title
- `username` - chat username (if any)
- `first_seen_at` - time of first chat detection
- `last_updated_at` - time of last update

### `users` Table
- `id` - User ID in Telegram
- `is_bot` - whether the user is a bot
- `first_name` - first name
- `last_name` - last name
- `username` - username
- `language_code` - language code
- `first_seen_at` - time of first user detection

### `messages` Table
- `message_id` - Message ID within the chat
- `chat_id` - Chat ID (foreign key)
- `user_id` - User ID (foreign key)
- `text` - message text
- `sent_at` - time of message sending
- `raw_message` - full message data in JSON format

## Logging

The bot keeps detailed logs of all operations. The logging level can be changed in the code by modifying the `level` parameter in `logging.basicConfig()`.

## Monitoring

The bot includes a built-in HTTP server for status monitoring:

- **Health Check**: `GET /health` or `GET /`
- **Port**: Automatically determined from the `PORT` variable (for Railway)

Example health check response:
```json
{
  "status": "healthy",
  "database": "connected", 
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Stopping the Bot

To stop the bot, use `Ctrl+C`. The bot will correctly close database connections.

## MVP Limitations

This version is an MVP and includes only basic data collection functionality. Future versions plan to add:

- Command processing
- Integration with LLM for message analysis
- Queue system for processing large data volumes
- Webhook mode for production deployment
- Additional message types (images, documents, etc.)

## Troubleshooting

### Bot is not receiving messages
- Ensure Privacy Mode is disabled in @BotFather
- Check that the bot is added to the group chat
- Verify the bot token is correct

### Database connection errors
- Check correctness of DATABASE_URL
- Ensure PostgreSQL is running and accessible
- Check database access rights

### Message duplicates
- The bot uses UPSERT operations to prevent duplicates
- If duplicates still appear, check uniqueness of primary keys
