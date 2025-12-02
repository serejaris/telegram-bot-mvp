"""Роуты веб-приложения: админка и API."""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from functools import wraps

from aiohttp import web
import aiohttp_jinja2
import jinja2

from ..config import get_config
from ..database import get_cursor
from ..models import (
    get_stats,
    get_chats_with_stats,
    get_chat_messages,
    get_chat_messages_by_date,
    get_chat_by_id,
    get_users,
    get_dashboard_data,
)
from ..services.summary import generate_chat_summary

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def json_response(data, **kwargs):
    """JSON response с поддержкой Cyrillic (ensure_ascii=False)."""
    return web.json_response(
        data,
        dumps=lambda x: json.dumps(x, ensure_ascii=False),
        **kwargs
    )


def check_auth(request: web.Request) -> bool:
    """Проверяет базовую авторизацию."""
    config = get_config()
    
    if not config.has_auth:
        return True  # Авторизация не настроена
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False
    
    try:
        encoded = auth_header[6:]
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username == config.admin_username and password == config.admin_password
    except Exception:
        return False


def require_auth(handler):
    """Декоратор для проверки авторизации."""
    @wraps(handler)
    async def wrapper(request: web.Request):
        if not check_auth(request):
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="Admin Panel"'},
                text="Unauthorized"
            )
        return await handler(request)
    return wrapper


# ========== Health Check ==========

async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint для Railway."""
    try:
        async with get_cursor() as cur:
            await cur.execute("SELECT 1")
            result = await cur.fetchone()
        
        if result and result[0] == 1:
            return json_response({
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    return json_response({
        "status": "unhealthy",
        "database": "disconnected",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }, status=500)


# ========== API ==========

@require_auth
async def api_stats(request: web.Request) -> web.Response:
    """API: общая статистика."""
    try:
        stats = await get_stats()
        return json_response({
            "total_chats": stats.total_chats,
            "total_users": stats.total_users,
            "total_messages": stats.total_messages,
            "messages_today": stats.messages_today,
            "messages_by_type": stats.messages_by_type,
        })
    except Exception as e:
        logger.error(f"API stats error: {e}")
        return json_response({"error": str(e)}, status=500)


@require_auth
async def api_chats(request: web.Request) -> web.Response:
    """API: список чатов."""
    try:
        chats = await get_chats_with_stats()
        return json_response([
            {
                "id": c.id,
                "type": c.type,
                "title": c.title,
                "username": c.username,
                "message_count": c.message_count,
                "user_count": c.user_count,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            }
            for c in chats
        ])
    except Exception as e:
        logger.error(f"API chats error: {e}")
        return json_response({"error": str(e)}, status=500)


@require_auth
async def api_chat_messages(request: web.Request) -> web.Response:
    """API: сообщения чата."""
    try:
        chat_id = int(request.match_info["chat_id"])
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))
        message_type = request.query.get("type")
        
        messages = await get_chat_messages(chat_id, limit, offset, message_type)
        
        # Сериализуем datetime
        for msg in messages:
            if msg["sent_at"]:
                msg["sent_at"] = msg["sent_at"].isoformat()
            if msg["edited_at"]:
                msg["edited_at"] = msg["edited_at"].isoformat()
        
        return json_response(messages)
    except Exception as e:
        logger.error(f"API chat messages error: {e}")
        return json_response({"error": str(e)}, status=500)


@require_auth
async def api_chat_messages_daily(request: web.Request) -> web.Response:
    """API: сообщения чата за конкретный день (UTC+3)."""
    try:
        chat_id = int(request.match_info["chat_id"])
        date_str = request.query.get("date")  # format: YYYY-MM-DD
        
        if not date_str:
            return json_response({"error": "date parameter required (YYYY-MM-DD)"}, status=400)
        
        messages = await get_chat_messages_by_date(chat_id, date_str)
        
        # Сериализуем datetime
        for msg in messages:
            if msg["sent_at"]:
                msg["sent_at"] = msg["sent_at"].isoformat()
            if msg["edited_at"]:
                msg["edited_at"] = msg["edited_at"].isoformat()
        
        return json_response({
            "chat_id": chat_id,
            "date": date_str,
            "timezone": "UTC+3",
            "count": len(messages),
            "messages": messages,
        })
    except ValueError:
        return json_response({"error": "invalid chat_id or date format"}, status=400)
    except Exception as e:
        logger.error(f"API daily messages error: {e}")
        return json_response({"error": str(e)}, status=500)


@require_auth
async def api_dashboard(request: web.Request) -> web.Response:
    """API: данные для дашборда."""
    try:
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


# ========== HTML Pages ==========

@require_auth
@aiohttp_jinja2.template("dashboard.html")
async def dashboard(request: web.Request):
    """Главная страница дашборда."""
    chats = await get_dashboard_data()

    return {
        "request": request,
        "chats": chats,
    }


@require_auth
@aiohttp_jinja2.template("chats.html")
async def chats_page(request: web.Request):
    """Страница списка чатов."""
    chats = await get_chats_with_stats()
    return {"request": request, "chats": chats}


@require_auth
@aiohttp_jinja2.template("messages.html")
async def chat_messages_page(request: web.Request):
    """Страница сообщений чата."""
    chat_id = int(request.match_info["chat_id"])
    page = int(request.query.get("page", 1))
    message_type = request.query.get("type")
    limit = 50
    offset = (page - 1) * limit
    
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise web.HTTPNotFound(text="Chat not found")
    
    messages = await get_chat_messages(chat_id, limit, offset, message_type)
    
    return {
        "request": request,
        "chat": chat,
        "messages": messages,
        "page": page,
        "message_type": message_type,
        "has_next": len(messages) == limit,
        "has_prev": page > 1,
    }


@require_auth
@aiohttp_jinja2.template("users.html")
async def users_page(request: web.Request):
    """Страница списка пользователей."""
    page = int(request.query.get("page", 1))
    limit = 50
    offset = (page - 1) * limit
    
    users = await get_users(limit, offset)
    
    return {
        "request": request,
        "users": users,
        "page": page,
        "has_next": len(users) == limit,
        "has_prev": page > 1,
    }


def create_web_app() -> web.Application:
    """Создаёт и настраивает веб-приложение."""
    app = web.Application()
    
    # Настройка Jinja2
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(['html', 'xml']),
    )
    
    # Роуты
    app.router.add_get("/health", health_check)
    app.router.add_get("/", dashboard)
    app.router.add_get("/chats", chats_page)
    app.router.add_get("/chats/{chat_id}", chat_messages_page)
    app.router.add_get("/users", users_page)
    
    # API
    app.router.add_get("/api/stats", api_stats)
    app.router.add_get("/api/chats", api_chats)
    app.router.add_get("/api/chats/{chat_id}/messages", api_chat_messages)
    app.router.add_get("/api/chats/{chat_id}/messages/daily", api_chat_messages_daily)
    app.router.add_get("/api/dashboard", api_dashboard)
    app.router.add_post("/api/chats/{chat_id}/summary", api_chat_summary)
    
    logger.info("Web application created")
    return app


async def start_web_server(app: web.Application, port: int) -> web.AppRunner:
    """Запускает веб-сервер."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")
    return runner
