"""Сервис аналитики активности чатов."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ..models import get_daily_message_counts, get_chat_by_id
from .openrouter import generate_completion

logger = logging.getLogger(__name__)

ANALYTICS_SYSTEM_PROMPT = """Ты — аналитик активности чата. Даёшь краткие, фактические комментарии по статистике сообщений."""

ANALYTICS_PROMPT_TEMPLATE = """Дай краткий комментарий (2-3 предложения) по статистике сообщений за неделю.

Тип чата: {chat_type}
Период: {date_from} — {date_to}
Данные по дням: {daily_data}
Всего сообщений: {total}
Среднее в день: {average:.1f}

Укажи:
- Где пики и спады активности
- Возможные причины (день недели, выходные и т.д.)

Будь лаконичен, максимум 50 слов."""


def _fill_missing_days(daily_counts: List[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
    """Заполняет пропущенные дни нулями."""
    if not daily_counts:
        # Если нет данных, создаём пустой массив за последние N дней
        result = []
        today = datetime.now().date()
        for i in range(days - 1, -1, -1):
            day = today - timedelta(days=i)
            result.append({"date": day.isoformat(), "count": 0})
        return result

    # Создаём словарь существующих данных
    existing = {item["date"]: item["count"] for item in daily_counts}

    # Определяем диапазон дат
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    result = []
    current = start_date
    while current <= today:
        date_str = current.isoformat()
        result.append({
            "date": date_str,
            "count": existing.get(date_str, 0)
        })
        current += timedelta(days=1)

    return result


async def generate_chat_analytics(chat_id: int) -> Dict[str, Any]:
    """Генерирует аналитику чата за последнюю неделю.

    Returns:
        Dict с полями: success, chat_type, period, daily_messages, total, average, ai_comment, error
    """
    # Получаем информацию о чате
    chat = await get_chat_by_id(chat_id)
    if not chat:
        return {
            "success": False,
            "error": "Чат не найден",
        }

    chat_type = chat.get("type", "group")

    # Получаем статистику по дням
    daily_counts = await get_daily_message_counts(chat_id, days=7)

    # Заполняем пропущенные дни
    daily_messages = _fill_missing_days(daily_counts, days=7)

    # Вычисляем метрики
    total = sum(d["count"] for d in daily_messages)
    average = total / 7 if daily_messages else 0

    # Период
    if daily_messages:
        date_from = daily_messages[0]["date"]
        date_to = daily_messages[-1]["date"]
        period = f"{date_from} — {date_to}"
    else:
        period = "нет данных"

    # Если нет сообщений, возвращаем без AI-комментария
    if total == 0:
        return {
            "success": True,
            "chat_type": chat_type,
            "period": period,
            "daily_messages": daily_messages,
            "total": total,
            "average": average,
            "ai_comment": None,
            "error": None,
        }

    # Генерируем AI-комментарий
    daily_data = ", ".join([f"{d['date']}: {d['count']}" for d in daily_messages])

    prompt = ANALYTICS_PROMPT_TEMPLATE.format(
        chat_type="канал" if chat_type == "channel" else "группа",
        date_from=date_from,
        date_to=date_to,
        daily_data=daily_data,
        total=total,
        average=average,
    )

    logger.info(f"Generating analytics for chat {chat_id}")
    ai_comment = await generate_completion(
        prompt=prompt,
        system_prompt=ANALYTICS_SYSTEM_PROMPT,
        max_tokens=150,
        timeout=30.0,
    )

    return {
        "success": True,
        "chat_type": chat_type,
        "period": period,
        "daily_messages": daily_messages,
        "total": total,
        "average": average,
        "ai_comment": ai_comment,
        "error": None if ai_comment else "Не удалось получить AI-комментарий",
    }
