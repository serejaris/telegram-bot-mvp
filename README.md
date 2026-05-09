<!-- hq-readme-ru: 2026-05-09 -->
# telegram-bot-mvp

Коротко: Telegram-проект или бот по теме «telegram bot mvp».

## Что здесь

- Назначение: Telegram-проект или бот по теме «telegram bot mvp».
- Основной стек: Python.
- Видимость: публичный репозиторий.
- Статус: активный репозиторий; актуальность проверять по issues и последним коммитам.

## Где смотреть работу

- Задачи и текущие решения: GitHub Issues этого репозитория.
- Код и материалы: файлы в корне и профильные папки проекта.
- Связь с HQ: если проект влияет на продукт, контент или воронку, сверяйте канон в `0_hq` и репозитории-владельце.

## Для агентов

- Сначала прочитайте этот README и открытые issues.
- Не переносите сюда канон соседних проектов без ссылки на источник.
- Перед правками проверьте существующие scripts, package.json/pyproject и локальные инструкции.

---

## Исходный README

# Telegram Bot MVP для сбора сообщений

Этот бот представляет собой MVP (Minimum Viable Product) для сбора текстовых сообщений из групповых чатов Telegram и сохранения их в базу данных PostgreSQL.

## API Endpoints

### Health Check (без авторизации)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Проверка состояния сервиса и БД |

### Web Pages (требуется Basic Auth, если настроен)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard со статистикой |
| GET | `/chats` | Список всех чатов |
| GET | `/chats/{chat_id}` | Сообщения конкретного чата |
| GET | `/users` | Список пользователей |

### JSON API (требуется Basic Auth, если настроен)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Общая статистика (чаты, пользователи, сообщения) |
| GET | `/api/chats` | Список чатов с количеством сообщений |
| GET | `/api/chats/{chat_id}/messages` | Сообщения чата (`?limit=100&offset=0&type=text`) |
| GET | `/api/chats/{chat_id}/messages/daily` | Сообщения за день (**обязательно**: `?date=YYYY-MM-DD`, UTC+3) |

> **Примечание:** `chat_id` для групп/супергрупп всегда отрицательный (например, `-1001234567890`)

### Примеры запросов
```bash
# Health check
curl https://your-domain.railway.app/health

# API с авторизацией
curl -u admin:password https://your-domain.railway.app/api/stats

# Сообщения чата за день
curl -u admin:password "https://your-domain.railway.app/api/chats/-1001234567890/messages/daily?date=2024-12-01"
```

## Функциональность

- Слушает все текстовые сообщения в групповых чатах
- Сохраняет информацию о сообщениях, пользователях и чатах в PostgreSQL
- Использует асинхронный подход для высокой производительности
- Предотвращает дубликаты сообщений с помощью UPSERT операций
- Работает в режиме long-polling для простоты развертывания

## Требования

- Python 3.12+
- PostgreSQL 12+
- Telegram Bot Token (получить через @BotFather)

## Варианты развертывания

### 🚀 Railway (Рекомендуется для продакшена)

Для деплоя на Railway см. подробное руководство: [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md)

**Быстрый старт на Railway:**
1. Форкните репозиторий на GitHub
2. Создайте проект на [railway.app](https://railway.app)
3. Подключите GitHub репозиторий
4. Добавьте PostgreSQL сервис
5. Установите переменную `TELEGRAM_TOKEN`
6. Готово! 🎉

### 💻 Локальный запуск

## Установка и настройка

### 1. Создание таблиц в PostgreSQL

Выполните следующий SQL-скрипт в вашей базе данных PostgreSQL:

```sql
-- Таблица чатов
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    type VARCHAR(255) NOT NULL,
    title TEXT,
    username VARCHAR(255) UNIQUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_bot BOOLEAN NOT NULL,
    first_name TEXT,
    last_name TEXT,
    username VARCHAR(255) UNIQUE,
    language_code VARCHAR(10),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица сообщений
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    text TEXT,
    sent_at TIMESTAMPTZ NOT NULL,
    raw_message JSONB,

    PRIMARY KEY (chat_id, message_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_chats_username ON chats(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
```

**Примечание:** Таблицы также создаются автоматически при первом запуске бота, если они не существуют.

### 2. Настройка переменных окружения

Установите следующие переменные окружения:

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export DATABASE_URL="postgresql://username:password@localhost:5432/database_name"
```

Или создайте файл `.env` (не забудьте добавить его в `.gitignore`):

```
TELEGRAM_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Запуск бота

```bash
python main.py
```

## Важные настройки

### Отключение Privacy Mode

**КРИТИЧЕСКИ ВАЖНО:** Для работы бота в групповых чатах необходимо отключить Privacy Mode через @BotFather:

1. Откройте чат с @BotFather
2. Отправьте команду `/setprivacy`
3. Выберите вашего бота
4. Выберите `Disable` для отключения Privacy Mode

Без этой настройки бот не будет получать сообщения в групповых чатах!

### Добавление бота в групповой чат

1. Добавьте бота в нужный групповой чат
2. Убедитесь, что бот имеет права на чтение сообщений
3. Бот автоматически начнет сохранять все текстовые сообщения

## Структура базы данных

### Таблица `chats`
- `id` - ID чата в Telegram
- `type` - тип чата (group, supergroup)
- `title` - название чата
- `username` - username чата (если есть)
- `first_seen_at` - время первого обнаружения чата
- `last_updated_at` - время последнего обновления

### Таблица `users`
- `id` - ID пользователя в Telegram
- `is_bot` - является ли пользователь ботом
- `first_name` - имя пользователя
- `last_name` - фамилия пользователя
- `username` - username пользователя
- `language_code` - код языка пользователя
- `first_seen_at` - время первого обнаружения пользователя

### Таблица `messages`
- `message_id` - ID сообщения в рамках чата
- `chat_id` - ID чата (внешний ключ)
- `user_id` - ID пользователя (внешний ключ)
- `text` - текст сообщения
- `sent_at` - время отправки сообщения
- `raw_message` - полные данные сообщения в формате JSON

## Логирование

Бот ведет подробные логи всех операций. Уровень логирования можно изменить в коде, изменив параметр `level` в `logging.basicConfig()`.

## Мониторинг

Бот включает встроенный HTTP сервер для мониторинга состояния:

- **Health Check**: `GET /health` или `GET /`
- **Порт**: Автоматически определяется из переменной `PORT` (для Railway)

Пример ответа health check:
```json
{
  "status": "healthy",
  "database": "connected", 
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Остановка бота

Для остановки бота используйте `Ctrl+C`. Бот корректно закроет соединения с базой данных.

## Ограничения MVP

Данная версия является MVP и включает только базовую функциональность сбора данных. В будущих версиях планируется добавить:

- Обработку команд
- Интеграцию с LLM для анализа сообщений
- Систему очередей для обработки больших объемов данных
- Webhook-режим для production развертывания
- Дополнительные типы сообщений (изображения, документы и т.д.)

## Устранение неполадок

### Бот не получает сообщения
- Убедитесь, что Privacy Mode отключен в @BotFather
- Проверьте, что бот добавлен в групповой чат
- Убедитесь, что токен бота корректен

### Ошибки подключения к базе данных
- Проверьте правильность DATABASE_URL
- Убедитесь, что PostgreSQL запущен и доступен
- Проверьте права доступа к базе данных

### Дубликаты сообщений
- Бот использует UPSERT операции для предотвращения дубликатов
- Если дубликаты все же появляются, проверьте уникальность первичных ключей