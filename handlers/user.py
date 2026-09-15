import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID, COMPANY_NAME
from database import (
    save_user,
    save_lead,
    save_message,
    get_history,
    get_recent_leads,
)
from keyboards import main_menu, cancel_kb, lead_confirm_kb
from ai import ask_ai

log = logging.getLogger(__name__)
router = Router()


# --- FSM для заявки ---

class LeadForm(StatesGroup):
    name = State()
    contact = State()
    message = State()
    confirm = State()


# --- /start и /help ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        f"Я — AI-ассистент компании «{COMPANY_NAME}».\n"
        f"Могу ответить на вопросы о наших услугах или принять заявку.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🤖 <b>Что я умею</b>\n\n"
        "• <b>💬 Задать вопрос</b> — AI-консультант ответит на любой вопрос\n"
        "• <b>📝 Оставить заявку</b> — мы свяжемся с вами\n"
        "• <b>ℹ️ О компании</b> — информация о нас\n"
        "• <b>📞 Контакты</b> — как с нами связаться\n\n"
        "Команды: /start, /help, /cancel",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu())


@router.callback_query(F.data == "cancel_fsm")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Действие отменено.")
    await call.message.answer("Возвращаю в меню.", reply_markup=main_menu())
    await call.answer()


# --- Статические разделы ---

@router.message(F.text == "ℹ️ О компании")
async def about(message: Message):
    await message.answer(
        f"🏢 <b>{COMPANY_NAME}</b>\n\n"
        "Мы — команда, которая помогает бизнесу расти.\n\n"
        "• Более 5 лет на рынке\n"
        "• 200+ довольных клиентов\n"
        "• Работаем по всей России\n\n"
        "Чтобы узнать подробнее — задайте вопрос или оставьте заявку.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):
    await message.answer(
        "📞 <b>Наши контакты</b>\n\n"
        "Телефон: +7 (999) 123-45-67\n"
        "Email: hello@example.com\n"
        "Сайт: example.com\n"
        "Telegram: @your_manager",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# --- FSM: заявка ---

@router.message(F.text == "📝 Оставить заявку")
async def lead_start(message: Message, state: FSMContext):
    await state.set_state(LeadForm.name)
    await message.answer(
        "📝 <b>Оформление заявки</b>\n\n"
        "Шаг 1 из 3. Как вас зовут?",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(LeadForm.name, F.text)
async def lead_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer("Пожалуйста, введите корректное имя (2-100 символов).")
        return
    await state.update_data(name=name)
    await state.set_state(LeadForm.contact)
    await message.answer(
        "Шаг 2 из 3. Как с вами связаться?\n"
        "<i>Телефон, email или @username</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(LeadForm.contact, F.text)
async def lead_contact(message: Message, state: FSMContext):
    contact = message.text.strip()
    if len(contact) < 3 or len(contact) > 200:
        await message.answer("Пожалуйста, введите корректный контакт (3-200 символов).")
        return
    await state.update_data(contact=contact)
    await state.set_state(LeadForm.message)
    await message.answer(
        "Шаг 3 из 3. Опишите коротко, что вам нужно?",
        parse_mode="HTML",
        reply_markup=cancel_kb(),
    )


@router.message(LeadForm.message, F.text)
async def lead_message(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 5 or len(text) > 2000:
        await message.answer("Опишите, пожалуйста, подробнее (5-2000 символов).")
        return

    data = await state.get_data()
    await state.update_data(message=text)
    await state.set_state(LeadForm.confirm)

    # Создаём заявку сразу, чтобы получить ID для превью
    lead_id = await save_lead(
        message.from_user.id,
        data["name"],
        data["contact"],
        text,
    )

    preview = (
        "📋 <b>Проверьте заявку</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Контакт: {data['contact']}\n"
        f"💬 Сообщение: {text}\n\n"
        f"Номер заявки: <code>#{lead_id}</code>\n\n"
        "Всё верно?"
    )
    await message.answer(preview, parse_mode="HTML", reply_markup=lead_confirm_kb())


@router.callback_query(LeadForm.confirm, F.data == "lead_send")
async def lead_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    # Заявка уже сохранена — достаём ID последней записи
    leads = await get_recent_leads(limit=1)
    lead_id = leads[0][0] if leads else "?"

    await call.message.edit_text(
        f"✅ <b>Заявка №{lead_id} принята!</b>\n\n"
        "Мы свяжемся с вами в ближайшее время.",
        parse_mode="HTML",
    )
    await call.message.answer("Возвращаю в главное меню.", reply_markup=main_menu())
    await call.answer("Заявка отправлена")

    # Уведомляем админа
    if ADMIN_ID:
        admin_text = (
            f"🔔 <b>Новая заявка №{lead_id}</b>\n\n"
            f"👤 Имя: {data.get('name')}\n"
            f"📞 Контакт: {data.get('contact')}\n"
            f"💬 Сообщение: {data.get('message')}\n\n"
            f"👤 От: @{call.from_user.username or '—'} "
            f"(ID: <code>{call.from_user.id}</code>)"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            log.warning(f"Не удалось уведомить админа: {e}")


# --- AI диалог ---

@router.message(F.text == "💬 Задать вопрос")
async def ask_prompt(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "💬 Напишите свой вопрос — я постараюсь ответить.\n\n"
        "Можно спросить про услуги, цены, сроки и т.п.",
    )


@router.message(F.text & ~F.text.startswith("/"))
async def ai_reply(message: Message, state: FSMContext):
    # Если пользователь в середине FSM — не перебиваем
    current = await state.get_state()
    if current is not None:
        return

    # Игнорируем кнопки главного меню (они обрабатываются выше)
    if message.text in {
        "💬 Задать вопрос",
        "📝 Оставить заявку",
        "ℹ️ О компании",
        "📞 Контакты",
        "❌ Отмена",
    }:
        return

    await save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    # Показываем «печатает…», пока AI думает
    await message.chat.do("typing")

    history = await get_history(message.from_user.id, limit=8)
    answer = await ask_ai(history, message.text)

    await save_message(message.from_user.id, "user", message.text)
    await save_message(message.from_user.id, "assistant", answer)

    await message.answer(answer)