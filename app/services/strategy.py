"""Сервис генерации контент-стратегии для чатов."""

import logging
from typing import Dict, Any, List

from ..models import get_messages_for_period, get_chat_by_id
from .openrouter import generate_completion

logger = logging.getLogger(__name__)

STRATEGY_SYSTEM_PROMPT = """Ты — контент-стратег. Анализируешь сообщения из чатов и каналов, даёшь практичные рекомендации по контенту на русском языке."""

STRATEGY_PROMPT_TEMPLATE = """Проанализируй сообщения из {chat_type_ru} за {period_ru}.

Название: {chat_title}
Тип: {chat_type_ru}
Период: {date_range}
Сообщений проанализировано: {count}

Сообщения:
{messages}

Дай отчёт на русском:

## Что зашло
- Какие темы вызвали больше активности/реакций (2-3 пункта)

## Рекомендации
- Что автору стоит делать больше/меньше (2-3 совета)

## Идеи для постов
- 3 конкретные идеи на основе интересов аудитории

Максимум 300 слов."""


def _format_messages_for_strategy(messages: List[Dict[str, Any]]) -> str:
    """Форматирует сообщения для промпта стратегии."""
    lines = []
    for msg in messages:
        time_str = msg["sent_at"].strftime("%d.%m %H:%M")
        author = msg["author"]
        text = msg["text"][:300] if msg["text"] else ""
        msg_type = msg.get("type", "text")

        if msg_type != "text":
            lines.append(f"[{time_str}] @{author}: [{msg_type}] {text}")
        else:
            lines.append(f"[{time_str}] @{author}: {text}")

    return "\n".join(lines)


async def generate_content_strategy(chat_id: int, period: str = "week") -> Dict[str, Any]:
    """Генерирует контент-стратегию для чата.

    Args:
        chat_id: ID чата
        period: "week" (7 дней) или "month" (30 дней)

    Returns:
        Dict с полями: success, chat_type, period, date_range, messages_analyzed, report, error
    """
    # Валидация периода
    if period not in ("week", "month"):
        return {
            "success": False,
            "error": "Неверный период. Используйте 'week' или 'month'",
        }

    days = 7 if period == "week" else 30
    period_ru = "неделю" if period == "week" else "месяц"

    # Получаем информацию о чате
    chat = await get_chat_by_id(chat_id)
    if not chat:
        return {
            "success": False,
            "error": "Чат не найден",
        }

    chat_type = chat.get("type", "group")
    chat_type_ru = "канала" if chat_type == "channel" else "группы"
    chat_title = chat.get("title") or f"Chat {chat_id}"

    # Получаем сообщения за период
    messages = await get_messages_for_period(chat_id, days=days, limit=500)

    if not messages:
        return {
            "success": False,
            "error": f"Нет сообщений за последн{'юю неделю' if period == 'week' else 'ий месяц'}",
        }

    # Формируем диапазон дат
    # Сообщения отсортированы по убыванию (новые первые)
    date_from = messages[-1]["sent_at"]
    date_to = messages[0]["sent_at"]
    date_range = f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"

    # Форматируем сообщения (переворачиваем для хронологического порядка)
    formatted_messages = _format_messages_for_strategy(list(reversed(messages)))

    # Формируем промпт
    prompt = STRATEGY_PROMPT_TEMPLATE.format(
        chat_type_ru=chat_type_ru,
        period_ru=period_ru,
        chat_title=chat_title,
        date_range=date_range,
        count=len(messages),
        messages=formatted_messages,
    )

    # Генерируем отчёт
    logger.info(f"Generating strategy for chat {chat_id}, period={period}, {len(messages)} messages")
    report = await generate_completion(
        prompt=prompt,
        system_prompt=STRATEGY_SYSTEM_PROMPT,
        max_tokens=800,
        timeout=45.0,
    )

    if not report:
        return {
            "success": False,
            "error": "Не удалось сгенерировать отчёт. Попробуйте позже.",
            "chat_type": chat_type,
            "period": period,
            "date_range": date_range,
            "messages_analyzed": len(messages),
        }

    return {
        "success": True,
        "error": None,
        "chat_type": chat_type,
        "period": period,
        "date_range": date_range,
        "messages_analyzed": len(messages),
        "report": report,
    }
