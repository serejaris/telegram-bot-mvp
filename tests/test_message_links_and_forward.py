"""Ссылки (url/text_link) и источник пересылки: извлечение из Message и поля API daily/export.

Интеграционные тесты требуют пустую PostgreSQL базу в TEST_DATABASE_URL (схема public пересоздаётся).
"""

import os
from datetime import datetime, timezone

import pytest
from aiohttp.test_utils import TestClient, TestServer
from telegram import (
    Chat, Message, MessageEntity, MessageOriginChannel, MessageOriginChat, MessageOriginUser, User,
)

from app import config as config_module
from app.config import Config
from app.database import close_pool, get_cursor, init_pool
from app.models import CREATE_TABLES_SQL, extract_links, get_forward_chat_id, init_database, save_message
from app.web.routes import create_web_app

CHAT = Chat(id=-1001, type=Chat.SUPERGROUP, title="Vibecoders")
AUTHOR = User(id=42, is_bot=False, first_name="Ann", username="ann")
CHANNEL = Chat(id=-1009, type=Chat.CHANNEL, title="AI News", username="ainews")
DATE = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)  # 2026-09-30 15:00 MSK


def make_message(message_id=1, **kwargs) -> Message:
    return Message(message_id=message_id, date=DATE, chat=CHAT, from_user=AUTHOR, **kwargs)


# ---------- extract_links ----------

def test_extract_links_visible_url_after_emoji_uses_utf16_offsets():
    # 🔥 занимает 2 UTF-16 единицы, offset entity считается в UTF-16
    text = "🔥 see https://example.com/a now"
    msg = make_message(text=text, entities=[MessageEntity(MessageEntity.URL, offset=7, length=21)])
    assert extract_links(msg) == ["https://example.com/a"]


def test_extract_links_hidden_text_link_returns_target_not_anchor():
    msg = make_message(
        text="читайте тут",
        entities=[MessageEntity(MessageEntity.TEXT_LINK, offset=8, length=3, url="https://hidden.example/x")],
    )
    assert extract_links(msg) == ["https://hidden.example/x"]


def test_extract_links_from_caption_ignores_other_entities_and_dedups():
    caption = "@bot https://a.io и https://a.io"
    msg = make_message(
        caption=caption,
        caption_entities=[
            MessageEntity(MessageEntity.MENTION, offset=0, length=4),
            MessageEntity(MessageEntity.URL, offset=5, length=12),
            MessageEntity(MessageEntity.URL, offset=20, length=12),
            MessageEntity(MessageEntity.TEXT_LINK, offset=18, length=1, url="https://b.io"),
        ],
    )
    assert extract_links(msg) == ["https://a.io", "https://b.io"]


def test_extract_links_without_entities_is_empty():
    assert extract_links(make_message(text="no links here")) == []


# ---------- get_forward_chat_id ----------

def test_forward_chat_id_by_origin_type():
    from_channel = make_message(text="x", forward_origin=MessageOriginChannel(DATE, CHANNEL, 77))
    from_chat = make_message(text="x", forward_origin=MessageOriginChat(DATE, CHANNEL))
    from_user = make_message(text="x", forward_origin=MessageOriginUser(DATE, AUTHOR))
    assert get_forward_chat_id(from_channel) == -1009
    assert get_forward_chat_id(from_chat) == -1009
    assert get_forward_chat_id(from_user) is None
    assert get_forward_chat_id(make_message(text="x")) is None


# ---------- API daily/export (PostgreSQL) ----------

DB_URL = os.getenv("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
async def client():
    await init_pool(DB_URL, max_size=2)
    async with get_cursor() as cur:
        await cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        # Схема до появления links: проверяем, что миграция добавит колонку
        await cur.execute(CREATE_TABLES_SQL.replace("    links JSONB,\n", ""))
        await cur.execute("""
            INSERT INTO users (id, is_bot, first_name) VALUES (42, false, 'Ann');
            INSERT INTO chats (id, type, title) VALUES (-1001, 'supergroup', 'Vibecoders');
            INSERT INTO messages (message_id, chat_id, user_id, text, sent_at)
            VALUES (100, -1001, 42, 'old message', '2026-09-30 10:00:00+00');
        """)
    await init_database()

    config_module.config = Config(telegram_token="test", database_url=DB_URL)
    test_client = TestClient(TestServer(create_web_app()))
    await test_client.start_server()
    yield test_client
    await test_client.close()
    config_module.config = None
    await close_pool()


@needs_db
async def test_daily_and_export_return_forward_source_and_links(client):
    forwarded = make_message(
        message_id=101,
        text="🔥 новость https://openai.com/blog и подробнее",
        entities=[
            MessageEntity(MessageEntity.URL, offset=11, length=23),
            MessageEntity(MessageEntity.TEXT_LINK, offset=37, length=9, url="https://hidden.example/x"),
        ],
        forward_origin=MessageOriginChannel(DATE, CHANNEL, 77),
    )
    await save_message(forwarded)
    edited = make_message(message_id=102, text="draft")
    await save_message(edited)
    edited = make_message(
        message_id=102,
        text="тут",
        entities=[MessageEntity(MessageEntity.TEXT_LINK, offset=0, length=3, url="https://edited.example")],
        edit_date=DATE,
    )
    await save_message(edited, is_edit=True)

    daily = await client.get("/api/chats/-1001/messages/daily", params={"date": "2026-09-30"})
    export = await client.get("/api/chats/-1001/messages/export", params={"from": "2026-09-30", "to": "2026-09-30"})
    assert daily.status == 200 and export.status == 200
    daily_msgs = {m["message_id"]: m for m in (await daily.json())["messages"]}
    export_msgs = {m["message_id"]: m for m in (await export.json())["messages"]}
    assert daily_msgs == export_msgs

    fwd = daily_msgs[101]
    assert fwd["forward_from_chat_id"] == -1009
    assert fwd["forward_from_chat_title"] == "AI News"
    assert fwd["forward_from_chat_username"] == "ainews"
    assert fwd["links"] == ["https://openai.com/blog", "https://hidden.example/x"]
    # Старые поля на месте
    assert fwd["text"].startswith("🔥 новость") and fwd["user"]["id"] == 42 and fwd["reactions"] == []

    assert daily_msgs[102]["links"] == ["https://edited.example"]
    assert daily_msgs[102]["forward_from_chat_id"] is None

    # Сообщение до миграции: links неизвестны, источника пересылки нет
    old = daily_msgs[100]
    assert old["links"] is None
    assert old["forward_from_chat_id"] is None and old["forward_from_chat_title"] is None
