#!/usr/bin/env python3
"""Batch-decline fresh chat join requests stored in DB.

Intended for manual runs / backfill. In production, the service runs the same
logic periodically via JobQueue.
"""

import asyncio
import os
import sys
from pathlib import Path

# Load .env if exists (same pattern as scripts/vibecoder_summary.py)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Add project root to path (for `import app...`)
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot

from app.config import get_config
from app.database import init_pool, close_pool
from app.models import init_database, get_pending_fresh_join_requests
from app.bot.handlers import process_pending_fresh_join_requests


async def main() -> None:
    cfg = get_config()
    if not cfg.vibecoder_chat_id:
        print("Error: VIBECODER_CHAT_ID is required")
        return

    await init_pool(cfg.database_url)
    await init_database()

    pending = await get_pending_fresh_join_requests(
        cfg.vibecoder_chat_id,
        cfg.fresh_account_id_threshold,
        cfg.join_request_clean_batch_limit,
    )
    if not pending:
        print("Declined 0/0 pending requests")
        await close_pool()
        return

    async with Bot(cfg.telegram_token) as bot:
        declined, processed = await process_pending_fresh_join_requests(
            bot,
            cfg.vibecoder_chat_id,
            cfg.fresh_account_id_threshold,
            cfg.join_request_clean_batch_limit,
            cfg.declined_requests_log_path,
        )

    await close_pool()
    print(f"Declined {declined}/{processed} pending requests")


if __name__ == "__main__":
    asyncio.run(main())

