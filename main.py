"""
AI Content Studio Bot — точка входа.

Архитектура:
    - Логирование: только stdout (на Render FileHandler падает)
    - Flask (health check для Render) — в daemon-потоке
    - Telegram-бот — в главном потоке
"""

import asyncio
import logging
import os
import sys
import threading

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==========================================================
#  ЛОГИРОВАНИЕ — настраиваем ДО импорта config,
#  чтобы видеть ошибки даже если config упадёт
# ==========================================================
handlers = [logging.StreamHandler(sys.stdout)]

# FileHandler только локально (на Render файловая система read-only)
if not os.getenv("RENDER"):
    try:
        handlers.append(logging.FileHandler("bot.log", encoding="utf-8"))
    except OSError as e:
        # Если не удалось создать файл — просто предупреждаем
        print(f"[WARN] Не удалось открыть bot.log: {e}", file=sys.stderr)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
    handlers=handlers,
)
log = logging.getLogger(__name__)

# ==========================================================
#  ИМПОРТЫ ПОСЛЕ ЛОГИРОВАНИЯ
# ==========================================================
from config import BOT_TOKEN
from database import init_db
from handlers import setup_routers


# ==========================================================
#  FLASK — health check для Render
# ==========================================================
web = Flask(__name__)


@web.route("/")
def home():
    return "AI Content Studio Bot is running"


@web.route("/health")
def health():
    return "OK"


def run_flask() -> None:
    """Запускает Flask в daemon-потоке."""
    port = int(os.environ.get("PORT", 5000))
    log.info("Flask слушает на 0.0.0.0:%d", port)
    web.run(host="0.0.0.0", port=port, use_reloader=False)


# ==========================================================
#  TELEGRAM BOT
# ==========================================================
async def main() -> None:
    # 1. Инициализируем БД
    await init_db()
    log.info("✅ База данных готова")

    # 2. Создаём бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Подключаем роутеры
    dp.include_router(setup_routers())

    # 4. Проверяем, что токен валидный
    me = await bot.get_me()
    log.info(f"✅ Бот @{me.username} запущен и готов к работе")

    # 5. Запускаем polling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        log.info("Бот остановлен")


# ==========================================================
#  ТОЧКА ВХОДА
# ==========================================================
if __name__ == "__main__":
    # Flask — в фоне (daemon), чтобы не блокировать бота
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Остановка по сигналу")
    except Exception as e:
        log.exception("Критическая ошибка: %s", e)
        sys.exit(1)