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
