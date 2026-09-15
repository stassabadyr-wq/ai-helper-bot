import logging

from openai import AsyncOpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    SYSTEM_PROMPT,
)

log = logging.getLogger(__name__)

# Клиент создаётся один раз (lazy init) — переиспользуем соединение
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI | None:
    """Возвращает клиент OpenAI или None, если ключ не настроен."""
    global _client
    if not OPENAI_API_KEY:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=30.0,
            max_retries=2,
        )
        log.info(f"AI-клиент инициализирован: {OPENAI_BASE_URL} / {OPENAI_MODEL}")
    return _client


async def ask_ai(history: list[dict], user_text: str) -> str:
    """
    Отправляет запрос к AI.

    :param history: список сообщений [{'role': 'user'|'assistant', 'content': '...'}, ...]
    :param user_text: новое сообщение пользователя
    :return: текст ответа или сообщение об ошибке
    """
    client = get_client()
    if client is None:
        return (
            "⚠️ AI-функция пока не подключена.\n\n"
            "Администратор бота ещё не настроил API-ключ.\n"
            "Вы можете оставить заявку через меню — мы свяжемся с вами."
        )

    # Системный промпт + история + новый вопрос
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
        if not answer:
            return "⚠️ AI вернул пустой ответ. Попробуйте переформулировать вопрос."

        usage = response.usage
        if usage:
            log.info(
                f"AI: prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens}, "
                f"total={usage.total_tokens}"
            )
        return answer.strip()

    except Exception as e:
        log.error(f"Ошибка AI-запроса: {e}", exc_info=True)
        error_str = str(e).lower()

        if "rate limit" in error_str or "429" in error_str:
            return "⏳ Слишком много запросов. Подождите 10-15 секунд и попробуйте снова."
        if "insufficient_quota" in error_str or "quota" in error_str:
            return (
                "⚠️ Исчерпана квота AI-сервиса.\n"
                "Обратитесь к администратору бота."
            )
        if "timeout" in error_str:
            return "⏱ AI-сервис не ответил вовремя. Попробуйте ещё раз."
        if "connection" in error_str or "network" in error_str:
            return "🌐 Не удалось связаться с AI-сервисом. Проверьте подключение."

        return "⚠️ Не удалось получить ответ от AI. Попробуйте позже."


def is_ai_enabled() -> bool:
    """Проверяет, настроен ли AI (для индикации в админ-панели)."""
    return bool(OPENAI_API_KEY)