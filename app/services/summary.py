"""Сервис генерации саммари по чатам."""

import logging
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
