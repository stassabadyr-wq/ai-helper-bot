from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from database import get_stats, get_recent_leads, update_lead_status
from keyboards import admin_menu, back_to_admin

router = Router()


def is_admin(user_id: int) -> bool:
    return ADMIN_ID is not None and user_id == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для администратора.")
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "admin_menu")
async def cb_admin_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.edit_text(
        "🛠 <b>Админ-панель</b>\n\nВыбери раздел:",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    stats = await get_stats()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: <b>{stats['users']}</b>\n"
        f"📨 Всего заявок: <b>{stats['leads']}</b>\n"
        f"🆕 Новых заявок: <b>{stats['new_leads']}</b>\n"
        f"💬 Сообщений юзеров: <b>{stats['messages']}</b>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_admin())
    await call.answer()


@router.callback_query(F.data == "admin_leads")
async def cb_leads(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    leads = await get_recent_leads(limit=10)
    if not leads:
        await call.message.edit_text(
            "📭 Заявок пока нет.",
            reply_markup=back_to_admin(),
        )
        await call.answer()
        return

    lines = ["📨 <b>Последние 10 заявок:</b>\n"]
    for lid, name, contact, msg, status, dt in leads:
        short = msg[:60] + ("…" if len(msg) > 60 else "")
        status_emoji = "🆕" if status == "new" else "✅"
        lines.append(
            f"{status_emoji} <b>№{lid}</b> · {dt}\n"
            f"👤 {name} · {contact}\n"
            f"💬 {short}\n"
        )

    await call.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_to_admin(),
    )
    await call.answer()