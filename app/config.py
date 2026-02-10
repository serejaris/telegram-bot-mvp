"""Конфигурация приложения через переменные окружения."""

import os
from dataclasses import dataclass
from typing import Optional


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
    
    # Спец-функции под конкретные чаты
    vibecoder_chat_id: Optional[int] = None

    # Auto-decline join requests from "fresh" accounts.
    fresh_account_id_threshold: int = 7_000_000_000
    join_request_clean_interval_sec: int = 60
    join_request_clean_batch_limit: int = 100
    declined_requests_log_path: str = "logs/declined_requests.log"
    
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
            vibecoder_chat_id=int(os.getenv("VIBECODER_CHAT_ID"))
            if os.getenv("VIBECODER_CHAT_ID")
            else None,

            fresh_account_id_threshold=int(os.getenv("FRESH_ACCOUNT_ID_THRESHOLD", "7000000000")),
            join_request_clean_interval_sec=int(os.getenv("JOIN_REQUEST_CLEAN_INTERVAL_SEC", "60")),
            join_request_clean_batch_limit=int(os.getenv("JOIN_REQUEST_CLEAN_BATCH_LIMIT", "100")),
            declined_requests_log_path=os.getenv("DECLINED_REQUESTS_LOG_PATH", "logs/declined_requests.log"),
        )
    
    @property
    def has_auth(self) -> bool:
        """Проверяет, настроена ли авторизация."""
        return bool(self.admin_username and self.admin_password)

    @property
    def has_openrouter(self) -> bool:
        """Проверяет, настроен ли OpenRouter."""
        return bool(self.openrouter_api_key)


# Глобальный экземпляр конфигурации
config: Optional[Config] = None


def get_config() -> Config:
    """Возвращает глобальную конфигурацию."""
    global config
    if config is None:
        config = Config.from_env()
    return config
