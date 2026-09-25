"""
Конфигурация проекта ai-content-studio.

Читает переменные окружения из:
  1. os.environ (приоритет — Render, Docker, CI)
  2. .env файл (локально — если существует)

На Render .env отсутствует — переменные приходят из Environment Variables.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Ищем .env рядом с config.py
env_path = Path(__file__).parent / ".env"

# Загружаем .env ТОЛЬКО если файл существует (локально).
# override=False — НЕ затираем уже заданные переменные os.environ
# (на Render BOT_TOKEN приходит из Environment, .env его не должен перекрывать).
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)


def _required(key: str) -> str:
    """Возвращает обязательную переменную окружения или падает с понятной ошибкой."""
    value = os.getenv(key)
    if not value or value.startswith("123456:"):
        raise SystemExit(
            f"❌ Не задана переменная окружения: {key}\n"
            f"\n"
            f"  Локально: добавь в файл {env_path}\n"
            f"           Формат: {key}=значение (без кавычек и пробелов)\n"
            f"\n"
            f"  На Render: Dashboard → Environment → Add Environment Variable\n"
            f"            Key:   {key}\n"
            f"            Value: <значение>"
        )
    return value.strip()


# --- ОБЯЗАТЕЛЬНЫЕ ---
BOT_TOKEN = _required("BOT_TOKEN")

# --- ОПЦИОНАЛЬНЫЕ ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

_admin_raw = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID = int(_admin_raw) if _admin_raw.isdigit() else None

COMPANY_NAME = os.getenv("COMPANY_NAME", "Наша компания").strip()

# --- ПУТИ ---
DB_PATH = Path(__file__).parent / "bot.db"

# --- AI SYSTEM PROMPT ---
SYSTEM_PROMPT = (
    f"Ты — вежливый консультант компании «{COMPANY_NAME}». "
    "Отвечай кратко (до 3 абзацев), по делу, на русском языке. "
    "Если вопрос не по теме услуг компании — мягко верни разговор к услугам. "
    "Если пользователь хочет оставить заявку или связаться с менеджером — "
    "предложи выбрать пункт «📝 Оставить заявку» в меню."
)