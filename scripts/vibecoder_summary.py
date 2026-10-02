#!/usr/bin/env python3
"""Скрипт для получения саммари чата вайбкодеров за последние сутки."""

import os
import sys
import httpx
from pathlib import Path

# Load .env if exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def get_config():
    """Get configuration from environment."""
    api_url = os.getenv("API_URL", "https://telegram-bot-mvp-production.up.railway.app")
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    chat_id = os.getenv("VIBECODER_CHAT_ID")

    if not username or not password:
        print("Error: ADMIN_USERNAME and ADMIN_PASSWORD required in .env")
        sys.exit(1)

    return api_url, username, password, chat_id


def find_vibecoder_chat(client: httpx.Client, api_url: str) -> int | None:
    """Find VibeCoder chat ID from API."""
    response = client.get(f"{api_url}/api/chats")
    response.raise_for_status()

    chats = response.json()
    for chat in chats:
        title = (chat.get("title") or "").lower()
        if "вайбкод" in title or "vibecod" in title:
            return chat["id"]

    return None


def get_summary(client: httpx.Client, api_url: str, chat_id: int) -> dict:
    """Get chat summary from API."""
    response = client.post(
        f"{api_url}/api/chats/{chat_id}/summary",
        timeout=60.0  # LLM generation can be slow
    )
    response.raise_for_status()
    return response.json()


def main():
    api_url, username, password, chat_id = get_config()

    with httpx.Client(auth=(username, password)) as client:
        # Find chat ID if not provided
        if not chat_id:
            print("Finding VibeCoder chat...")
            chat_id = find_vibecoder_chat(client, api_url)
            if not chat_id:
                print("Error: VibeCoder chat not found. Set VIBECODER_CHAT_ID in .env")
                sys.exit(1)

        print(f"Chat ID: {chat_id}")
        print("Generating summary (this may take a moment)...\n")

        result = get_summary(client, api_url, int(chat_id))

        if result.get("success"):
            print("=" * 60)
            print(f"📅 Период: {result.get('period')}")
            print(f"📊 Сообщений: {result.get('messages_count')}")
            print("=" * 60)
            print()
            print(result.get("summary"))
            print()
        else:
            print(f"Error: {result.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
