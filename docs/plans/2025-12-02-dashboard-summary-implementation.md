# Dashboard + AI Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать веб-дашборд на русском языке с AI-саммари по чатам за последние сутки.

**Architecture:** Расширяем существующий aiohttp сервер новыми роутами и сервисами. OpenRouter для LLM. Синхронный MVP — кнопка саммари блокирует UI на время генерации.

**Tech Stack:** Python 3.12, aiohttp, Jinja2, httpx (для OpenRouter API), PostgreSQL

---

## Task 1: Добавить httpx в зависимости

**Files:**
- Modify: `requirements.txt`

**Step 1: Добавить httpx**

```
# Telegram Bot Library
python-telegram-bot[job-queue]==21.0.1

# PostgreSQL Database Driver
psycopg[binary]==3.1.18
psycopg-pool==3.2.2

# Web Server & Templates
aiohttp==3.9.1
aiohttp-jinja2==1.6
Jinja2>=3.1.2

# HTTP Client for OpenRouter API
httpx>=0.27.0
```

**Step 2: Установить зависимость**

Run: `pip install httpx>=0.27.0`
Expected: Successfully installed httpx

---

## Task 2: Расширить конфигурацию

**Files:**
- Modify: `app/config.py`

**Step 1: Добавить OpenRouter настройки в Config**

В файле `app/config.py` добавить новые поля в dataclass Config:

```python
@dataclass
class Config:
    """Конфигурация приложения."""

    telegram_token: str
    database_url: str
    port: int = 8000
    log_level: str = "INFO"

    # Опциональная базовая авторизация для админки
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None

    # OpenRouter API
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4o-mini"
```

**Step 2: Обновить from_env метод**

```python
    @classmethod
    def from_env(cls) -> "Config":
        """Загружает конфигурацию из переменных окружения."""
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        database_url = os.getenv("DATABASE_URL")

        if not telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")

        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        return cls(
            telegram_token=telegram_token,
            database_url=database_url,
            port=int(os.getenv("PORT", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            admin_username=os.getenv("ADMIN_USERNAME"),
            admin_password=os.getenv("ADMIN_PASSWORD"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
        )
```

**Step 3: Добавить property has_openrouter**

```python
    @property
    def has_openrouter(self) -> bool:
        """Проверяет, настроен ли OpenRouter."""
        return bool(self.openrouter_api_key)
```

---

## Task 3: Создать OpenRouter клиент

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/openrouter.py`

**Step 1: Создать __init__.py**

```python
"""Сервисы приложения."""
```

**Step 2: Создать openrouter.py**

```python
"""Клиент для OpenRouter API."""

import logging
from typing import Optional

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


async def generate_completion(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 1000,
    timeout: float = 30.0,
) -> Optional[str]:
    """Генерирует ответ через OpenRouter API.

    Args:
        prompt: Пользовательский промпт
        system_prompt: Системный промпт (опционально)
        max_tokens: Максимальное количество токенов в ответе
        timeout: Таймаут запроса в секундах

    Returns:
        Текст ответа или None при ошибке
    """
    config = get_config()

    if not config.has_openrouter:
        logger.warning("OpenRouter API key not configured")
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {config.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config.openrouter_model,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"OpenRouter response received, {len(content)} chars")
            return content

    except httpx.TimeoutException:
        logger.error("OpenRouter request timed out")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter HTTP error: {e.response.status_code}")
        return None
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return None
```

---

## Task 4: Добавить SQL запросы для дашборда

**Files:**
- Modify: `app/models.py`

**Step 1: Добавить функцию get_dashboard_data**

В конец файла `app/models.py` добавить:

```python
@dataclass
class DashboardChat:
    """Данные чата для дашборда."""
    id: int
    title: Optional[str]
    total_messages: int
    today_messages: int
    last_message_text: Optional[str]
    last_message_author: Optional[str]
    last_message_at: Optional[datetime]
    top_users: List[Dict[str, Any]]


async def get_dashboard_data() -> List[DashboardChat]:
    """Получает данные для дашборда: чаты с полной статистикой."""
    async with get_cursor() as cur:
        # Получаем чаты с базовой статистикой
        await cur.execute("""
            SELECT
                c.id,
                c.title,
                COUNT(m.message_id) as total_messages,
                COUNT(m.message_id) FILTER (WHERE m.sent_at >= CURRENT_DATE) as today_messages
            FROM chats c
            LEFT JOIN messages m ON c.id = m.chat_id
            GROUP BY c.id, c.title
            ORDER BY total_messages DESC
        """)
        chats_data = await cur.fetchall()

        result = []
        for chat_row in chats_data:
            chat_id = chat_row[0]

            # Последнее сообщение
            await cur.execute("""
                SELECT
                    m.text,
                    COALESCE(u.username, u.first_name, 'Unknown') as author,
                    m.sent_at
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.id
                WHERE m.chat_id = %s AND m.text IS NOT NULL
                ORDER BY m.sent_at DESC
                LIMIT 1
            """, (chat_id,))
            last_msg = await cur.fetchone()

            # Топ пользователей за неделю
            await cur.execute("""
                SELECT
                    COALESCE(u.username, u.first_name, 'Unknown') as name,
                    COUNT(*) as count
                FROM messages m
                JOIN users u ON m.user_id = u.id
                WHERE m.chat_id = %s
                  AND m.sent_at >= NOW() - INTERVAL '7 days'
                GROUP BY u.id, u.username, u.first_name
                ORDER BY count DESC
                LIMIT 3
            """, (chat_id,))
            top_users = [{"name": row[0], "count": row[1]} for row in await cur.fetchall()]

            result.append(DashboardChat(
                id=chat_row[0],
                title=chat_row[1],
                total_messages=chat_row[2],
                today_messages=chat_row[3],
                last_message_text=last_msg[0] if last_msg else None,
                last_message_author=last_msg[1] if last_msg else None,
                last_message_at=last_msg[2] if last_msg else None,
                top_users=top_users,
            ))

        return result


async def get_messages_for_summary(chat_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    """Получает сообщения за последние 24 часа для генерации саммари."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT
                m.text,
                COALESCE(u.username, u.first_name, 'Unknown') as author,
                m.sent_at
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND m.sent_at >= NOW() - INTERVAL '24 hours'
              AND m.text IS NOT NULL
            ORDER BY m.sent_at ASC
            LIMIT %s
        """, (chat_id, limit))

        rows = await cur.fetchall()
        return [
            {"text": row[0], "author": row[1], "sent_at": row[2]}
            for row in rows
        ]
```

**Step 2: Добавить импорт List, Dict, Any если отсутствует**

Убедиться что в начале файла есть:

```python
from typing import Optional, List, Dict, Any
```

---

## Task 5: Создать сервис генерации саммари

**Files:**
- Create: `app/services/summary.py`

**Step 1: Создать summary.py**

```python
"""Сервис генерации саммари по чатам."""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..models import get_messages_for_summary, get_chat_by_id
from .openrouter import generate_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — аналитик чатов. Анализируй сообщения из групповых чатов и создавай краткие, информативные саммари на русском языке."""

SUMMARY_PROMPT_TEMPLATE = """Проанализируй сообщения из группового чата за последние сутки.

Чат: {chat_title}
Период: {date_from} — {date_to}
Сообщений: {count}

Сообщения:
{messages}

Дай краткое саммари на русском языке:
1. Основные темы обсуждения (2-3 пункта)
2. Ключевые решения или договорённости (если есть)
3. Важные вопросы без ответа (если есть)

Будь лаконичен, максимум 200 слов."""


def format_messages_for_prompt(messages: List[Dict[str, Any]]) -> str:
    """Форматирует сообщения для промпта."""
    lines = []
    for msg in messages:
        time_str = msg["sent_at"].strftime("%H:%M")
        author = msg["author"]
        text = msg["text"][:500]  # Ограничиваем длину одного сообщения
        lines.append(f"[{time_str}] @{author}: {text}")
    return "\n".join(lines)


async def generate_chat_summary(chat_id: int) -> Dict[str, Any]:
    """Генерирует саммари для чата за последние 24 часа.

    Returns:
        Dict с полями: success, summary, error, messages_count, period
    """
    # Получаем информацию о чате
    chat = await get_chat_by_id(chat_id)
    if not chat:
        return {
            "success": False,
            "error": "Чат не найден",
            "summary": None,
            "messages_count": 0,
            "period": None,
        }

    # Получаем сообщения за 24 часа
    messages = await get_messages_for_summary(chat_id, limit=500)

    if not messages:
        return {
            "success": False,
            "error": "Нет сообщений за последние 24 часа",
            "summary": None,
            "messages_count": 0,
            "period": None,
        }

    # Формируем период
    date_from = messages[0]["sent_at"]
    date_to = messages[-1]["sent_at"]
    period = f"{date_from.strftime('%d.%m.%Y %H:%M')} — {date_to.strftime('%d.%m.%Y %H:%M')}"

    # Формируем промпт
    formatted_messages = format_messages_for_prompt(messages)
    prompt = SUMMARY_PROMPT_TEMPLATE.format(
        chat_title=chat.get("title") or f"Chat {chat_id}",
        date_from=date_from.strftime("%d.%m.%Y %H:%M"),
        date_to=date_to.strftime("%d.%m.%Y %H:%M"),
        count=len(messages),
        messages=formatted_messages,
    )

    # Генерируем саммари
    logger.info(f"Generating summary for chat {chat_id}, {len(messages)} messages")
    summary = await generate_completion(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=500,
        timeout=30.0,
    )

    if not summary:
        return {
            "success": False,
            "error": "Не удалось сгенерировать саммари. Попробуйте позже.",
            "summary": None,
            "messages_count": len(messages),
            "period": period,
        }

    return {
        "success": True,
        "error": None,
        "summary": summary,
        "messages_count": len(messages),
        "period": period,
    }
```

---

## Task 6: Добавить API роуты для дашборда

**Files:**
- Modify: `app/web/routes.py`

**Step 1: Добавить импорты**

В начало файла добавить:

```python
from ..models import (
    get_stats,
    get_chats_with_stats,
    get_chat_messages,
    get_chat_messages_by_date,
    get_chat_by_id,
    get_users,
    get_dashboard_data,  # NEW
)
from ..services.summary import generate_chat_summary  # NEW
```

**Step 2: Добавить API endpoint для дашборда**

После функции `api_chat_messages_daily` добавить:

```python
@require_auth
async def api_dashboard(request: web.Request) -> web.Response:
    """API: данные для дашборда."""
    try:
        from ..models import get_dashboard_data
        chats = await get_dashboard_data()

        config = get_config()

        return json_response({
            "chats": [
                {
                    "id": c.id,
                    "title": c.title or f"Chat {c.id}",
                    "total_messages": c.total_messages,
                    "today_messages": c.today_messages,
                    "last_message": {
                        "text": c.last_message_text[:100] if c.last_message_text else None,
                        "author": c.last_message_author,
                        "sent_at": c.last_message_at.isoformat() if c.last_message_at else None,
                    } if c.last_message_text else None,
                    "top_users_week": c.top_users,
                }
                for c in chats
            ],
            "has_openrouter": config.has_openrouter,
        })
    except Exception as e:
        logger.error(f"API dashboard error: {e}")
        return json_response({"error": str(e)}, status=500)
```

**Step 3: Добавить API endpoint для саммари**

```python
@require_auth
async def api_chat_summary(request: web.Request) -> web.Response:
    """API: генерация саммари для чата."""
    try:
        chat_id = int(request.match_info["chat_id"])

        config = get_config()
        if not config.has_openrouter:
            return json_response({
                "success": False,
                "error": "OpenRouter API не настроен",
            }, status=503)

        result = await generate_chat_summary(chat_id)

        status = 200 if result["success"] else 400
        return json_response(result, status=status)

    except ValueError:
        return json_response({"error": "invalid chat_id"}, status=400)
    except Exception as e:
        logger.error(f"API summary error: {e}")
        return json_response({"error": str(e)}, status=500)
```

**Step 4: Зарегистрировать новые роуты**

В функции `create_web_app()` добавить новые роуты в секцию API:

```python
    # API
    app.router.add_get("/api/stats", api_stats)
    app.router.add_get("/api/chats", api_chats)
    app.router.add_get("/api/chats/{chat_id}/messages", api_chat_messages)
    app.router.add_get("/api/chats/{chat_id}/messages/daily", api_chat_messages_daily)
    app.router.add_get("/api/dashboard", api_dashboard)  # NEW
    app.router.add_post("/api/chats/{chat_id}/summary", api_chat_summary)  # NEW
```

---

## Task 7: Обновить HTML шаблон дашборда

**Files:**
- Modify: `app/web/templates/dashboard.html`

**IMPORTANT:** Выполнить с навыком `frontend-design:frontend-design`

**Requirements:**
- Язык интерфейса: русский
- Тёмная тема (уже есть в base.html)
- Карточки чатов с:
  - Название чата
  - Количество сообщений (всего / сегодня)
  - Последнее сообщение (текст, автор, время)
  - Топ-3 активных за неделю
  - Кнопка "Получить саммари за сутки"
- При клике на кнопку:
  - Показать спиннер "Генерирую саммари..."
  - Отправить POST /api/chats/{id}/summary
  - Показать результат под карточкой
- Если OpenRouter не настроен — скрыть кнопки саммари

**Existing styles:** Использовать CSS из base.html (stat-card, badge, etc.)

---

## Task 8: Создать директорию services

**Files:**
- Create directory: `app/services/`

**Step 1: Создать директорию**

Run: `mkdir -p app/services`

---

## Execution Order

1. Task 8: Создать директорию services
2. Task 1: Добавить httpx в зависимости
3. Task 2: Расширить конфигурацию
4. Task 3: Создать OpenRouter клиент
5. Task 4: Добавить SQL запросы для дашборда
6. Task 5: Создать сервис генерации саммари
7. Task 6: Добавить API роуты для дашборда
8. Task 7: Обновить HTML шаблон дашборда (использовать frontend-design skill)

---

## Verification

После выполнения всех задач:

1. Запустить приложение:
   ```bash
   OPENROUTER_API_KEY=your_key python main.py
   ```

2. Открыть http://localhost:8000/
3. Проверить что дашборд показывает чаты на русском
4. Нажать "Получить саммари" на любом чате
5. Дождаться генерации и проверить результат
