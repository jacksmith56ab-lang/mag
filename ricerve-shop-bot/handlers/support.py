import re
import os

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

import database as db
import keyboards as kb
from utils import send_with_photo, edit_message

router = Router()

SUPPORT_PHOTO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "support.jpg")


class SupportState(StatesGroup):
    waiting_message = State()


def _support_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="support_new_ticket")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
    ])


SUPPORT_TEXT = (
    "🆘 <b>Поддержка</b>\n\n"
    "Возникли вопросы или проблемы?\n"
    "Нажмите кнопку ниже — создадим заявку и я отвечу вам лично."
)


# ─── /help — открывает меню поддержки ────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    if os.path.exists(SUPPORT_PHOTO):
        await message.answer_photo(
            photo=FSInputFile(SUPPORT_PHOTO),
            caption=SUPPORT_TEXT,
            reply_markup=_support_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(SUPPORT_TEXT, reply_markup=_support_kb(), parse_mode="HTML")


# ─── Кнопка поддержки (callback из меню) ─────────────────────────────────────

# NOTE: menu_support callback теперь обрабатывается в common.py через send_with_photo.
# Здесь оставляем только логику тикетов.


# ─── Создание тикета ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "support_new_ticket")
async def support_new_ticket(call: CallbackQuery, state: FSMContext):
    await state.set_state(SupportState.waiting_message)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_support")]
    ])
    text = (
        "✍️ <b>Напишите ваш вопрос</b>\n\n"
        "Опишите проблему подробно. Можно приложить фото или файл.\n"
        "Я отвечу вам как можно скорее!"
    )
    msg = call.message
    is_photo = bool(msg.photo) or getattr(msg, 'content_type', None) == 'photo'
    if is_photo:
        try:
            await msg.edit_caption(caption=text, reply_markup=cancel_kb, parse_mode="HTML")
        except Exception:
            try:
                await msg.delete()
            except Exception:
                pass
            await msg.answer(text, reply_markup=cancel_kb, parse_mode="HTML")
    else:
        await edit_message(call, text, reply_markup=cancel_kb)


# ─── Получение сообщения от пользователя → пересылаем каждому админу ─────────

@router.message(SupportState.waiting_message)
async def support_receive_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    user     = message.from_user
    username = f"@{user.username}" if user.username else f"#{user.id}"
    name     = user.first_name or "Пользователь"

    # Заголовок для админа с тегом #id_ для последующего ответа
    # ВАЖНО: #id_ должен быть в этом сообщении, чтобы reply на него работал
    header = (
        f"📩 <b>Новое обращение в поддержку</b>\n\n"
        f"👤 <b>{name}</b> ({username})\n"
        f"🆔 ID: <code>{user.id}</code>\n\n"
        f"Чтобы ответить — сделайте <b>Reply</b> на это сообщение.\n"
        f"#id_{user.id}"
    )

    sent_ok = False
    for admin_id in db.get_admin_ids():
        try:
            # Шлём заголовок
            await bot.send_message(
                chat_id=admin_id,
                text=header,
                parse_mode="HTML"
            )
            # Копируем само сообщение пользователя (надёжнее чем forward)
            await message.copy_to(chat_id=admin_id)
            sent_ok = True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Ошибка отправки тикета админу {admin_id}: {e}")

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
        [InlineKeyboardButton(text="✍️ Ещё вопрос",   callback_data="support_new_ticket")],
    ])

    if sent_ok:
        await message.answer(
            "✅ <b>Сообщение отправлено!</b>\n\n"
            "Ответ придёт сюда, в этот чат.\n"
            "Обычно отвечаем в течение нескольких часов.",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Не удалось отправить сообщение. Попробуйте позже или обратитесь напрямую.",
            reply_markup=back_kb,
            parse_mode="HTML"
        )


# ─── Ответ от админа (reply на пересланное сообщение) → пользователю ─────────

@router.message(F.reply_to_message)
async def admin_reply_to_user(message: Message, bot: Bot):
    """
    Когда АДМИН отвечает reply на сообщение-заголовок с #id_XXXXXXX —
    бот пересылает ответ этому пользователю.
    """
    if message.from_user.id not in db.get_admin_ids():
        return

    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    # Ищем #id_XXXXXXX в тексте заголовка
    match = re.search(r'#id_(\d+)', replied.text)
    if not match:
        return

    target_user_id = int(match.group(1))

    try:
        prefix = "💬 <b>Ответ поддержки:</b>\n\n"

        if message.photo:
            await bot.send_photo(
                chat_id=target_user_id,
                photo=message.photo[-1].file_id,
                caption=prefix + (message.caption or ""),
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                chat_id=target_user_id,
                document=message.document.file_id,
                caption=prefix + (message.caption or ""),
                parse_mode="HTML"
            )
        elif message.text:
            await bot.send_message(
                chat_id=target_user_id,
                text=prefix + message.text,
                parse_mode="HTML"
            )
        else:
            return

        # Подтверждаем админу
        await message.reply("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить: {e}")
