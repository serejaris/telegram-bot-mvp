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
        )
    
    @property
    def has_auth(self) -> bool:
        """Проверяет, настроена ли авторизация."""
        return bool(self.admin_username and self.admin_password)


# Глобальный экземпляр конфигурации
config: Optional[Config] = None


def get_config() -> Config:
    """Возвращает глобальную конфигурацию."""
    global config
    if config is None:
        config = Config.from_env()
    return config
