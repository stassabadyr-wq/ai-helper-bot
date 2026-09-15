from aiogram.types import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню внизу экрана — постоянные кнопки."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💬 Задать вопрос"),
                KeyboardButton(text="📝 Оставить заявку"),
            ],
            [
                KeyboardButton(text="ℹ️ О компании"),
                KeyboardButton(text="📞 Контакты"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню или напишите вопрос…",
    )
    return kb


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка «Отмена» для FSM-шагов (inline под сообщением)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_fsm")
    return builder.as_markup()


def lead_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение заявки перед отправкой."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="lead_send")
    builder.button(text="❌ Отмена", callback_data="cancel_fsm")
    builder.adjust(2)  # две кнопки в один ряд
    return builder.as_markup()


def admin_menu() -> InlineKeyboardMarkup:
    """Меню админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📨 Последние заявки", callback_data="admin_leads")
    builder.adjust(1)  # каждая кнопка — отдельная строка
    return builder.as_markup()


def back_to_admin() -> InlineKeyboardMarkup:
    """Кнопка «Назад» для возврата в админ-меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_menu")
    return builder.as_markup()