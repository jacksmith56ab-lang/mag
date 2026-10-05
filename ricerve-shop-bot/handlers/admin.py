import asyncio
import html
import os
from urllib.parse import urlparse
from aiogram import Router, F
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import ADMIN_IDS
router = Router()

ADMIN_PHOTO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "admin.jpeg")

authorized_admins: set[int] = set()


def is_user_authorized(user_id: int) -> bool:
    is_authorized = user_id in db.get_admin_ids()
    if is_authorized:
        authorized_admins.add(user_id)
    else:
        # Не оставляем удалённого администратора авторизованным в памяти.
        authorized_admins.discard(user_id)
    return is_authorized


async def _admin_edit(call_or_msg, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Универсальное редактирование — работает и с фото, и с текстом."""
    if isinstance(call_or_msg, CallbackQuery):
        msg = call_or_msg.message
    else:
        msg = call_or_msg
    is_photo = bool(msg.photo) or getattr(msg, 'content_type', None) == 'photo'
    if is_photo:
        try:
            await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            pass
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        try:
            await msg.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def _bot_edit(bot, chat_id: int, msg_id: int, text: str,
                    reply_markup=None, parse_mode: str = "HTML"):
    """
    Редактирует сообщение по ID через Bot API.
    Пробует edit_message_caption (фото), потом edit_message_text (текст).
    Если оба упали — ничего не делаем (исходное сообщение останется как есть).
    """
    try:
        await bot.edit_message_caption(
            chat_id=chat_id, message_id=msg_id,
            caption=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
        return
    except Exception:
        pass
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=text, reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception:
        pass


# ─── FSM States ───────────────────────────────────────────────────────────────

class AdminAddProduct(StatesGroup):
    waiting_group        = State()
    waiting_new_group    = State()
    waiting_name         = State()
    waiting_price        = State()
    waiting_content_type = State()
    waiting_content      = State()
    waiting_photo        = State()


class AdminAddGroup(StatesGroup):
    waiting_root_name = State()
    waiting_subcategory_name = State()


class AdminAddPromo(StatesGroup):
    waiting_code   = State()
    waiting_amount = State()
    waiting_uses   = State()


class AdminEditProduct(StatesGroup):
    choosing_field  = State()
    waiting_name    = State()
    waiting_price   = State()
    waiting_content = State()
    waiting_photo   = State()
    waiting_group   = State()


class AdminEditGroup(StatesGroup):
    waiting_name = State()


class AdminGrantBalance(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_confirmation = State()


class AdminGrantAdmin(StatesGroup):
    waiting_username = State()
    waiting_confirmation = State()


class AdminEditChannel(StatesGroup):
    waiting_url = State()


class AdminBroadcast(StatesGroup):
    waiting_message = State()
    waiting_confirmation = State()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def cancel_kb(back_cb: str = "admin_panel"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=back_cb)]
    ])


def product_edit_kb(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Название",  callback_data=f"pedit_name_{product_id}")],
        [InlineKeyboardButton(text="💰 Цена",       callback_data=f"pedit_price_{product_id}")],
        [InlineKeyboardButton(text="📄 Описание",   callback_data=f"pedit_content_{product_id}")],
        [InlineKeyboardButton(text="🖼 Картинка",   callback_data=f"pedit_photo_{product_id}")],
        [InlineKeyboardButton(text="📂 Группа",     callback_data=f"pedit_group_{product_id}")],
        [InlineKeyboardButton(text="🗑 Удалить",    callback_data=f"pedit_delete_{product_id}")],
        [InlineKeyboardButton(text="🔙 Назад",      callback_data="admin_list_products")],
    ])


def grant_balance_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])


def grant_balance_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="grant_balance_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"),
        ]
    ])


def grant_admin_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])


def grant_admin_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выдать админку", callback_data="grant_admin_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"),
        ]
    ])


def broadcast_confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"),
        ]
    ])


# ─── /admin команда ──────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_auth(message: Message, state: FSMContext):
    if message.from_user.id not in db.get_admin_ids():
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    try:
        await message.delete()
    except Exception:
        pass
    authorized_admins.add(message.from_user.id)
    if os.path.exists(ADMIN_PHOTO):
        await message.answer_photo(
            photo=FSInputFile(ADMIN_PHOTO),
            caption="🛠 <b>Админ-панель</b>",
            reply_markup=kb.admin_menu(db.is_maintenance()),
            parse_mode="HTML"
        )
    else:
        await message.answer("🛠 <b>Админ-панель</b>", reply_markup=kb.admin_menu(db.is_maintenance()), parse_mode="HTML")


# ─── admin_panel callback ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def admin_panel(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in db.get_admin_ids():
        await call.answer("⛔ У вас нет доступа к админ-панели.", show_alert=True)
        return
    authorized_admins.add(call.from_user.id)
    await state.clear()

    maintenance = db.is_maintenance()
    text = "🛠 <b>Админ-панель</b>"
    msg = call.message
    is_photo = bool(msg.photo) or getattr(msg, 'content_type', None) == 'photo'

    if os.path.exists(ADMIN_PHOTO):
        if is_photo:
            try:
                await msg.edit_media(
                    media=InputMediaPhoto(media=FSInputFile(ADMIN_PHOTO), caption=text, parse_mode="HTML"),
                    reply_markup=kb.admin_menu(maintenance)
                )
                return
            except Exception:
                pass
        try:
            await msg.delete()
        except Exception:
            pass
        await msg.answer_photo(
            photo=FSInputFile(ADMIN_PHOTO),
            caption=text,
            reply_markup=kb.admin_menu(maintenance),
            parse_mode="HTML"
        )
    else:
        await _admin_edit(call, text, kb.admin_menu(maintenance))


# ─── Ссылка на канал ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_channel_link")
async def admin_channel_link_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminEditChannel.waiting_url)
    await state.update_data(msg_id=call.message.message_id)
    await _admin_edit(
        call,
        "📢 <b>Ссылка на канал</b>\n\n"
        f"Текущая ссылка: <code>{html.escape(db.get_info_channel())}</code>\n\n"
        "Отправьте новую ссылку на канал (например, https://t.me/ricershop):",
        cancel_kb(),
    )


@router.message(AdminEditChannel.waiting_url)
async def admin_channel_link_save(message: Message, state: FSMContext):
    data = await state.get_data()
    raw_url = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    url = raw_url
    if url.startswith("t.me/"):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Некорректная ссылка. Пример: https://t.me/ricershop",
            cancel_kb(),
        )
        return

    db.set_setting("info_channel", url)
    await state.clear()
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        f"✅ Ссылка на канал обновлена:\n<code>{html.escape(url)}</code>",
        kb.admin_menu(db.is_maintenance()),
    )


# ─── Выдача админки по username ────────────────────────────────────────────────

@router.callback_query(F.data == "admin_grant_admin")
async def grant_admin_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminGrantAdmin.waiting_username)
    await state.update_data(msg_id=call.message.message_id)
    await _admin_edit(
        call,
        "👑 <b>Выдать админку</b>\n\n"
        "Введите username пользователя в формате <code>@username</code>.\n"
        "Пользователь должен хотя бы один раз отправить боту /start.",
        grant_admin_cancel_kb(),
    )


@router.message(AdminGrantAdmin.waiting_username)
async def grant_admin_username(message: Message, state: FSMContext):
    data = await state.get_data()
    username = (message.text or "").strip().lstrip("@")
    try:
        await message.delete()
    except Exception:
        pass

    user = db.find_user_by_username(username)
    if not user:
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Пользователь не найден в базе.\n"
            "Попросите его отправить боту /start, затем повторите ввод username:",
            grant_admin_cancel_kb(),
        )
        return

    if user["user_id"] in db.get_admin_ids():
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            f"ℹ️ Пользователь <code>@{html.escape(user['username'] or username)}</code> уже является администратором.",
            kb.admin_menu(db.is_maintenance()),
        )
        await state.clear()
        return

    await state.update_data(
        target_user_id=user["user_id"],
        target_username=user["username"] or username,
    )
    await state.set_state(AdminGrantAdmin.waiting_confirmation)
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        "🔎 <b>Подтвердите выдачу админки</b>\n\n"
        f"Пользователь: <code>@{html.escape(user['username'] or username)}</code>\n"
        f"Telegram ID: <code>{user['user_id']}</code>\n\n"
        "После подтверждения он сможет открывать админ-панель и управлять магазином.",
        grant_admin_confirm_kb(),
    )


@router.callback_query(F.data == "grant_admin_confirm", AdminGrantAdmin.waiting_confirmation)
async def grant_admin_confirm(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    data = await state.get_data()
    target_user_id = data["target_user_id"]
    target_username = data.get("target_username")
    db.add_admin(target_user_id, target_username)
    authorized_admins.add(target_user_id)
    await state.clear()
    await call.answer("Админка выдана.")
    await _admin_edit(
        call,
        "✅ <b>Админка выдана</b>\n\n"
        f"Пользователь: <code>@{html.escape(target_username or '—')}</code>\n"
        f"Telegram ID: <code>{target_user_id}</code>",
        kb.admin_menu(db.is_maintenance()),
    )


# ─── Список и удаление администраторов ─────────────────────────────────────────

def _admins_text():
    extra_admins = db.get_extra_admins()
    lines = [
        "👥 <b>Список администраторов</b>",
        "",
        "🔒 <b>Главные администраторы</b> — указаны в конфигурации:",
    ]
    lines.extend(f"• <code>{user_id}</code>" for user_id in sorted(ADMIN_IDS))

    if extra_admins:
        lines.extend(["", "🛡 <b>Дополнительные администраторы</b>:"])
        for admin in extra_admins:
            username = f"@{html.escape(admin['username'])}" if admin["username"] else "без username"
            lines.append(f"• {username} · <code>{admin['user_id']}</code>")
    else:
        lines.extend(["", "🛡 <b>Дополнительных администраторов нет.</b>"])

    lines.extend(["", "Нажмите на дополнительного администратора, чтобы открыть удаление."])
    return "\n".join(lines)


@router.callback_query(F.data == "admin_list_admins")
async def admin_list_admins(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.clear()
    await _admin_edit(
        call,
        _admins_text(),
        kb.admin_list_admins(db.get_extra_admins(), ADMIN_IDS),
    )


@router.callback_query(F.data == "admin_protected_admin")
async def admin_protected_admin(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await call.answer("Главного администратора удалить нельзя.", show_alert=True)


@router.callback_query(F.data.startswith("admin_manage_"))
async def admin_manage_extra(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    try:
        target_user_id = int(call.data.removeprefix("admin_manage_"))
    except ValueError:
        await call.answer("Некорректный ID администратора.", show_alert=True)
        return

    admin = db.get_extra_admin(target_user_id)
    if not admin:
        await call.answer("Этот администратор уже удалён.", show_alert=True)
        await _admin_edit(
            call,
            _admins_text(),
            kb.admin_list_admins(db.get_extra_admins(), ADMIN_IDS),
        )
        return

    username = f"@{html.escape(admin['username'])}" if admin["username"] else "без username"
    await _admin_edit(
        call,
        "🛡 <b>Управление администратором</b>\n\n"
        f"Пользователь: {username}\n"
        f"Telegram ID: <code>{target_user_id}</code>\n\n"
        "Удалить ему доступ к админ-панели?",
        kb.admin_remove_confirm_kb(target_user_id),
    )


@router.callback_query(F.data.startswith("admin_remove_confirm_"))
async def admin_remove_confirm(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    try:
        target_user_id = int(call.data.removeprefix("admin_remove_confirm_"))
    except ValueError:
        await call.answer("Некорректный ID администратора.", show_alert=True)
        return

    if target_user_id in ADMIN_IDS:
        await call.answer("Главного администратора удалить нельзя.", show_alert=True)
        return

    admin = db.get_extra_admin(target_user_id)
    if not admin:
        await call.answer("Этот администратор уже удалён.", show_alert=True)
    else:
        db.remove_admin(target_user_id)
        authorized_admins.discard(target_user_id)
        await call.answer("Администратор удалён.")

    await _admin_edit(
        call,
        _admins_text(),
        kb.admin_list_admins(db.get_extra_admins(), ADMIN_IDS),
    )


# ─── Выдача баланса администратором ───────────────────────────────────────────

@router.callback_query(F.data == "admin_grant_balance")
async def grant_balance_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminGrantBalance.waiting_user_id)
    await state.update_data(msg_id=call.message.message_id)
    await _admin_edit(
        call,
        "💸 <b>Выдать баланс</b>\n\n"
        "Введите Telegram ID пользователя, которому нужно зачислить баланс:",
        grant_balance_cancel_kb(),
    )


@router.message(AdminGrantBalance.waiting_user_id)
async def grant_balance_user_id(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        user_id = int((message.text or "").strip())
        if user_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Нужен корректный числовой Telegram ID:",
            grant_balance_cancel_kb(),
        )
        return

    user = db.get_user(user_id)
    if not user:
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Пользователь ещё не запускал бота. Сначала попросите его отправить /start.",
            grant_balance_cancel_kb(),
        )
        return

    await state.update_data(user_id=user_id)
    await state.set_state(AdminGrantBalance.waiting_amount)
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        f"👤 Пользователь: <code>{user_id}</code>\n\n"
        "Введите сумму зачисления в рублях:",
        grant_balance_cancel_kb(),
    )


@router.message(AdminGrantBalance.waiting_amount)
async def grant_balance_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        amount = float((message.text or "").strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Введите положительную сумму, например 500 или 99.90:",
            grant_balance_cancel_kb(),
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(AdminGrantBalance.waiting_confirmation)
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        (
            "🔎 <b>Проверьте начисление</b>\n\n"
            f"Пользователь: <code>{data['user_id']}</code>\n"
            f"Сумма: <b>+{amount:.2f}₽</b>\n\n"
            "После подтверждения сумма будет зачислена сразу."
        ),
        grant_balance_confirm_kb(),
    )


@router.callback_query(F.data == "grant_balance_confirm", AdminGrantBalance.waiting_confirmation)
async def grant_balance_confirm(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    data = await state.get_data()
    user_id = data["user_id"]
    amount = data["amount"]
    db.update_balance(user_id, amount)
    user = db.get_user(user_id)
    new_balance = user["balance"] if user else amount
    await state.clear()

    try:
        await call.bot.send_message(
            chat_id=user_id,
            text=(
                "💰 <b>Баланс пополнен администратором</b>\n\n"
                f"Зачислено: <b>+{amount:.2f}₽</b>\n"
                f"Текущий баланс: <b>{new_balance:.2f}₽</b>"
            ),
            parse_mode="HTML",
        )
        notification = "Уведомление пользователю отправлено."
    except Exception:
        notification = "Баланс зачислен, но уведомление отправить не удалось."

    await call.answer("Баланс зачислен.")
    await _admin_edit(
        call,
        (
            "✅ <b>Баланс выдан</b>\n\n"
            f"Пользователь: <code>{user_id}</code>\n"
            f"Зачислено: <b>+{amount:.2f}₽</b>\n"
            f"Новый баланс: <b>{new_balance:.2f}₽</b>\n\n"
            f"{notification}"
        ),
        kb.admin_menu(db.is_maintenance()),
    )


# ─── Рассылка покупателям ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    buyer_ids = db.get_buyer_ids()
    if not buyer_ids:
        await call.answer("Покупателей пока нет.", show_alert=True)
        await _admin_edit(
            call,
            "📣 <b>Рассылка покупателям</b>\n\n"
            "Пока нет пользователей с завершёнными покупками.",
            kb.admin_menu(db.is_maintenance()),
        )
        return

    await state.set_state(AdminBroadcast.waiting_message)
    await state.update_data(
        msg_id=call.message.message_id,
        buyer_count=len(buyer_ids),
    )
    await _admin_edit(
        call,
        "📣 <b>Рассылка покупателям</b>\n\n"
        f"Получателей сейчас: <b>{len(buyer_ids)}</b>\n\n"
        "Отправьте текст сообщения для рассылки.\n"
        "Максимальная длина — 4096 символов.",
        cancel_kb(),
    )


@router.message(AdminBroadcast.waiting_message)
async def broadcast_message(message: Message, state: FSMContext):
    data = await state.get_data()
    text = message.text or ""
    try:
        await message.delete()
    except Exception:
        pass

    if not text.strip():
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            "❌ Отправьте именно текстовое сообщение для рассылки:",
            cancel_kb(),
        )
        return
    if len(text) > 4096:
        await _bot_edit(
            message.bot,
            message.chat.id,
            data["msg_id"],
            f"❌ Сообщение слишком длинное: {len(text)} символов.\n"
            "Максимальная длина — 4096 символов.",
            cancel_kb(),
        )
        return

    await state.update_data(broadcast_text=text)
    await state.set_state(AdminBroadcast.waiting_confirmation)
    preview = html.escape(text)
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        (
            "🔎 <b>Проверьте рассылку</b>\n\n"
            f"Получателей: <b>{data['buyer_count']}</b>\n\n"
            f"<b>Текст сообщения:</b>\n{preview}\n\n"
            "Отправить сообщение всем покупателям?"
        ),
        broadcast_confirm_kb(),
    )


@router.callback_query(F.data == "broadcast_confirm", AdminBroadcast.waiting_confirmation)
async def broadcast_confirm(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    data = await state.get_data()
    text = data["broadcast_text"]
    buyer_ids = db.get_buyer_ids()
    await state.clear()
    await call.answer("Рассылка запущена.")
    await _admin_edit(
        call,
        "📣 <b>Рассылка выполняется…</b>\n\n"
        f"Получателей: <b>{len(buyer_ids)}</b>\n"
        "Пожалуйста, подождите.",
        None,
    )

    sent = 0
    failed = 0
    for user_id in buyer_ids:
        try:
            await call.bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
            try:
                await call.bot.send_message(chat_id=user_id, text=text)
                sent += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await _admin_edit(
        call,
        (
            "✅ <b>Рассылка завершена</b>\n\n"
            f"👥 Всего покупателей: <b>{len(buyer_ids)}</b>\n"
            f"✅ Доставлено: <b>{sent}</b>\n"
            f"❌ Не доставлено: <b>{failed}</b>"
        ),
        kb.admin_menu(db.is_maintenance()),
    )


# ─── Экспорт пользователей ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin_export_users")
async def export_users(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await call.answer("⏳ Формирую файл...")
    users = db.get_all_users()
    if not users:
        await call.message.answer("👥 Пользователей пока нет.")
        return
    lines = ["Имя | Username | ID | Дата регистрации", "-" * 55]
    for u in users:
        name     = u["first_name"] or "—"
        username = f"@{u['username']}" if u["username"] else "—"
        reg_date = u["registered_at"][:16] if u["registered_at"] else "—"
        lines.append(f"{name} | {username} | {u['user_id']} | {reg_date}")
    content = "\n".join(lines).encode("utf-8")
    await call.bot.send_document(
        chat_id=call.from_user.id,
        document=BufferedInputFile(content, filename="users.txt"),
        caption=f"👥 <b>Список пользователей</b>\nВсего: {len(users)}",
        parse_mode="HTML"
    )


# ─── Тех. режим ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_toggle_maintenance")
async def toggle_maintenance(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    new_state = db.toggle_maintenance()
    status = "🔴 ВКЛЮЧЁН" if new_state else "🟢 ВЫКЛЮЧЕН"
    await call.answer(f"Тех. режим {status}", show_alert=True)
    await _admin_edit(call, "🛠 <b>Админ-панель</b>", kb.admin_menu(new_state))


# ─── Статистика ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    s = db.get_admin_stats()
    maint_status = "🔴 Включён" if db.is_maintenance() else "🟢 Выключен"
    text = (
        "📊 <b>Статистика магазина</b>\n\n"
        f"👥 Всего пользователей: <b>{s['total_users']}</b>\n"
        f"🟢 Активных за 24ч: <b>{s['active_24h']}</b>\n\n"
        f"🛒 Всего продано товаров: <b>{s['total_purchases']}</b>\n"
        f"📦 Продано за 24ч: <b>{s['purchases_24h']}</b>\n\n"
        f"💰 Общая выручка: <b>{s['total_revenue']:.2f}₽</b>\n"
        f"📈 Выручка за 24ч: <b>{s['revenue_24h']:.2f}₽</b>\n\n"
        f"🔧 Тех. режим: {maint_status}"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])
    await _admin_edit(call, text, back_kb)


# ─── Позиции каталога ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_list_products")
async def admin_list_products(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    products = db.get_all_products()
    if not products:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ])
        await _admin_edit(call, "📚 Позиции каталога пока не добавлены.", back_kb)
        return
    await _admin_edit(
        call,
        "📚 <b>Позиции каталога</b>\n\nВыберите позицию для управления:",
        kb.admin_products_list(products)
    )


# ─── Карточка товара (редактирование) ────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_product_"))
async def admin_product_card(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    product = db.get_product(product_id)
    if not product:
        await call.answer("❌ Товар не найден.", show_alert=True)
        return
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    group_name = group["name"] if group else "—"
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group_name}</b>\n"
        f"📄 Тип: <b>{product['content_type']}</b>\n\n"
        f"🖼 Фото: <b>{'есть' if product['photo_id'] else 'нет'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    await _admin_edit(call, text, product_edit_kb(product_id))


# ─── Редактирование: название ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_name_"))
async def pedit_name_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    await state.set_state(AdminEditProduct.waiting_name)
    await state.update_data(product_id=product_id, msg_id=call.message.message_id)
    await _admin_edit(
        call, "📝 Введите <b>новое название</b> товара:",
        cancel_kb(f"admin_product_{product_id}")
    )


@router.message(AdminEditProduct.waiting_name)
async def pedit_name_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    new_name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not new_name:
        return
    db.update_product_field(product_id, "name", new_name)
    await state.clear()
    product = db.get_product(product_id)
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    text = (
        f"✅ Название обновлено!\n\n"
        f"📦 <b>{product['name']}</b>\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name'] if group else '—'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=text, reply_markup=product_edit_kb(product_id), parse_mode="HTML"
        )
    except Exception:
        await message.answer(text, reply_markup=product_edit_kb(product_id), parse_mode="HTML")


# ─── Редактирование: цена ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_price_"))
async def pedit_price_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    await state.set_state(AdminEditProduct.waiting_price)
    await state.update_data(product_id=product_id, msg_id=call.message.message_id)
    await _admin_edit(
        call, "💰 Введите <b>новую цену</b> в рублях:",
        cancel_kb(f"admin_product_{product_id}")
    )


@router.message(AdminEditProduct.waiting_price)
async def pedit_price_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    try:
        await message.delete()
    except Exception:
        pass
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Некорректная цена. Введите число больше 0:",
                reply_markup=cancel_kb(f"admin_product_{product_id}"), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    db.update_product_field(product_id, "price", price)
    await state.clear()
    product = db.get_product(product_id)
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    text = (
        f"✅ Цена обновлена!\n\n"
        f"📦 <b>{product['name']}</b>\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name'] if group else '—'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=text, reply_markup=product_edit_kb(product_id), parse_mode="HTML"
        )
    except Exception:
        await message.answer(text, reply_markup=product_edit_kb(product_id), parse_mode="HTML")


# ─── Редактирование: описание/контент ────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_content_"))
async def pedit_content_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    await state.set_state(AdminEditProduct.waiting_content)
    await state.update_data(product_id=product_id, msg_id=call.message.message_id)
    await _admin_edit(
        call, "📄 Введите <b>новое содержимое</b> товара (текст, ссылка или отправьте файл):",
        cancel_kb(f"admin_product_{product_id}")
    )


@router.message(AdminEditProduct.waiting_content)
async def pedit_content_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    try:
        await message.delete()
    except Exception:
        pass
    if message.document:
        new_content = message.document.file_id
        new_ctype = "file"
    elif message.text:
        new_content = message.text.strip()
        new_ctype = "text"
    else:
        return
    db.update_product_field(product_id, "content", new_content)
    db.update_product_field(product_id, "content_type", new_ctype)
    await state.clear()
    product = db.get_product(product_id)
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    text = (
        f"✅ Содержимое обновлено!\n\n"
        f"📦 <b>{product['name']}</b>\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name'] if group else '—'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=text, reply_markup=product_edit_kb(product_id), parse_mode="HTML"
        )
    except Exception:
        await message.answer(text, reply_markup=product_edit_kb(product_id), parse_mode="HTML")


# ─── Редактирование: картинка ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_photo_del_"))
async def pedit_photo_delete(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[3])
    await state.clear()
    db.update_product_field(product_id, "photo_id", None)
    await call.answer("🗑 Картинка удалена.", show_alert=True)
    product = db.get_product(product_id)
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name'] if group else '—'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    await _admin_edit(call, text, product_edit_kb(product_id))


@router.callback_query(F.data.startswith("pedit_photo_"))
async def pedit_photo_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    await state.set_state(AdminEditProduct.waiting_photo)
    await state.update_data(product_id=product_id, msg_id=call.message.message_id)
    rm = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить картинку", callback_data=f"pedit_photo_del_{product_id}")],
        [InlineKeyboardButton(text="❌ Отмена",           callback_data=f"admin_product_{product_id}")],
    ])
    await _admin_edit(call, "🖼 Отправьте <b>новую картинку</b> товара:", rm)


@router.message(AdminEditProduct.waiting_photo)
async def pedit_photo_done(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data["product_id"]
    try:
        await message.delete()
    except Exception:
        pass
    if not message.photo:
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Отправьте фотографию:",
                reply_markup=cancel_kb(f"admin_product_{product_id}"), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    photo_id = message.photo[-1].file_id
    db.update_product_field(product_id, "photo_id", photo_id)
    await state.clear()
    product = db.get_product(product_id)
    group = db.get_group(product["group_id"]) if product["group_id"] else None
    text = (
        f"✅ Картинка обновлена!\n\n"
        f"📦 <b>{product['name']}</b>\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name'] if group else '—'}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=text, reply_markup=product_edit_kb(product_id), parse_mode="HTML"
        )
    except Exception:
        await message.answer(text, reply_markup=product_edit_kb(product_id), parse_mode="HTML")


# ─── Редактирование: группа товара ──────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_group_pick_"))
async def pedit_group_pick(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    # format: pedit_group_pick_{product_id}_{group_id}
    parts = call.data.split("_")
    product_id = int(parts[3])
    group_id   = int(parts[4])
    await state.clear()
    db.update_product_field(product_id, "group_id", group_id)
    group   = db.get_group(group_id)
    product = db.get_product(product_id)
    await call.answer(f"✅ Группа изменена на «{group['name']}»", show_alert=True)
    text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>\n"
        f"📂 Группа: <b>{group['name']}</b>\n\n"
        "Выберите что хотите изменить:"
    )
    await _admin_edit(call, text, product_edit_kb(product_id))


@router.callback_query(F.data.startswith("pedit_group_"))
async def pedit_group_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    groups = db.get_all_groups()
    if not groups:
        await call.answer("❌ Нет каталогов для выбора. Сначала создайте каталог.", show_alert=True)
        return
    await state.set_state(AdminEditProduct.waiting_group)
    await state.update_data(product_id=product_id, msg_id=call.message.message_id)
    buttons = [
        [InlineKeyboardButton(text=f"📂 {g['name']}", callback_data=f"pedit_group_pick_{product_id}_{g['id']}")]
        for g in groups
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_product_{product_id}")])
    await _admin_edit(call, "📂 Выберите <b>новый каталог</b> для позиции:",
                      InlineKeyboardMarkup(inline_keyboard=buttons))


# ─── Удаление товара ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pedit_delete_"))
async def pedit_delete_product(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    product_id = int(call.data.split("_")[2])
    product = db.get_product(product_id)
    if product:
        db.delete_product(product_id)
        await call.answer(f"🗑 Товар «{product['name']}» удалён.", show_alert=True)
    await state.clear()
    products = db.get_all_products()
    if not products:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
        ])
        await _admin_edit(call, "📦 Товаров больше нет.", back_kb)
    else:
        await _admin_edit(
            call,
            "📦 <b>Товары</b>\n\nНажмите на товар для управления:",
            kb.admin_products_list(products)
        )


# ─── Каталоги и категории ────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_list_groups")
async def admin_list_groups(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    groups = db.get_all_groups()
    if not groups:
        kb_empty = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить каталог", callback_data="admin_add_group")],
            [InlineKeyboardButton(text="🔙 Назад",           callback_data="admin_panel")],
        ])
        await _admin_edit(call, "📚 <b>Каталоги</b>\n\nКаталогов пока нет.", kb_empty)
        return
    await _admin_edit(
        call,
        "📚 <b>Каталоги</b>\n\nВыберите каталог для управления:",
        kb.admin_groups_list(groups)
    )


@router.callback_query(F.data == "admin_add_group")
async def admin_add_group_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return

    root_groups = db.get_root_groups()
    await state.update_data(msg_id=call.message.message_id)
    if root_groups:
        await state.set_state(AdminAddGroup.waiting_root_name)
        await _admin_edit(
            call,
            "📚 <b>Каталог → подкатегория → товар</b>\n\n"
            "Выберите существующий каталог, чтобы добавить в него подкатегорию,\n"
            "или создайте новый каталог:",
            kb.admin_choose_root_for_subcategory(root_groups),
        )
    else:
        await state.set_state(AdminAddGroup.waiting_root_name)
        await _admin_edit(
            call,
            "📚 Введите <b>название нового каталога</b>:",
            cancel_kb("admin_panel"),
        )


@router.callback_query(F.data == "admin_create_root_catalog", AdminAddGroup.waiting_root_name)
async def admin_create_root_catalog(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminAddGroup.waiting_root_name)
    await _admin_edit(
        call,
        "📚 Введите <b>название нового каталога</b>:",
        cancel_kb("admin_panel"),
    )


@router.callback_query(F.data.startswith("admin_choose_catalog_"), AdminAddGroup.waiting_root_name)
async def admin_choose_catalog(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    try:
        parent_id = int(call.data.removeprefix("admin_choose_catalog_"))
    except ValueError:
        await call.answer("Некорректный ID каталога.", show_alert=True)
        return

    parent = db.get_group(parent_id)
    if not parent or parent["parent_id"] is not None:
        await call.answer("Каталог не найден.", show_alert=True)
        return

    subgroups = db.get_subgroups(parent_id)
    if subgroups:
        await state.update_data(parent_id=parent_id, parent_name=parent["name"])
        await _admin_edit(
            call,
            f"📂 <b>{html.escape(parent['name'])}</b>\n\n"
            "Выберите подкатегорию, чтобы добавить товар,\n"
            "или создайте новую:",
            kb.admin_choose_subcategory(subgroups, parent_id),
        )
    else:
        await state.update_data(parent_id=parent_id, parent_name=parent["name"])
        await state.set_state(AdminAddGroup.waiting_subcategory_name)
        await _admin_edit(
            call,
            f"📂 Каталог: <b>{html.escape(parent['name'])}</b>\n\n"
            "Введите название первой <b>подкатегории</b>:",
            cancel_kb("admin_add_group"),
        )


@router.callback_query(F.data.startswith("admin_create_subcategory_"), AdminAddGroup.waiting_root_name)
async def admin_create_subcategory_from_root(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    try:
        parent_id = int(call.data.removeprefix("admin_create_subcategory_"))
    except ValueError:
        await call.answer("Некорректный ID каталога.", show_alert=True)
        return
    parent = db.get_group(parent_id)
    if not parent:
        await call.answer("Каталог не найден.", show_alert=True)
        return
    await state.update_data(parent_id=parent_id, parent_name=parent["name"])
    await state.set_state(AdminAddGroup.waiting_subcategory_name)
    await _admin_edit(
        call,
        f"📂 Каталог: <b>{html.escape(parent['name'])}</b>\n\n"
        "Введите название новой <b>подкатегории</b>:",
        cancel_kb("admin_add_group"),
    )


@router.callback_query(F.data.startswith("admin_add_product_to_subcategory_"))
async def admin_add_product_to_subcategory(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    try:
        subcategory_id = int(call.data.removeprefix("admin_add_product_to_subcategory_"))
    except ValueError:
        await call.answer("Некорректный ID подкатегории.", show_alert=True)
        return

    subcategory = db.get_group(subcategory_id)
    if not subcategory or subcategory["parent_id"] is None:
        await call.answer("Подкатегория не найдена.", show_alert=True)
        return
    parent = db.get_group(subcategory["parent_id"])
    group_name = (
        f"{parent['name']} → {subcategory['name']}"
        if parent else subcategory["name"]
    )
    await state.update_data(
        msg_id=call.message.message_id,
        group_id=subcategory_id,
        group_name=group_name,
    )
    await state.set_state(AdminAddProduct.waiting_name)
    await _admin_edit(
        call,
        f"📂 Каталог: <b>{html.escape(group_name)}</b>\n\n"
        "📝 Введите <b>название товара</b>:",
        cancel_kb("admin_panel"),
    )


@router.message(AdminAddGroup.waiting_root_name)
async def admin_add_root_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not name:
        return
    try:
        parent_id = db.add_group(name)
    except Exception:
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Каталог с таким названием уже существует. Введите другое:",
                reply_markup=cancel_kb("admin_panel"), parse_mode="HTML"
            )
        except Exception:
            pass
        return

    await state.update_data(parent_id=parent_id, parent_name=name)
    await state.set_state(AdminAddGroup.waiting_subcategory_name)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Каталог <b>«{html.escape(name)}»</b> создан!\n\n"
                "📁 Теперь введите название <b>подкатегории</b>:"
            ),
            reply_markup=cancel_kb("admin_panel"), parse_mode="HTML"
        )
    except Exception:
        await message.answer(
            f"✅ Каталог <b>«{html.escape(name)}»</b> создан!\n\n"
            "📁 Введите название подкатегории:",
            reply_markup=cancel_kb("admin_panel"), parse_mode="HTML"
        )


@router.message(AdminAddGroup.waiting_subcategory_name)
async def admin_add_subcategory_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not name:
        return

    parent_id = data.get("parent_id")
    parent_name = data.get("parent_name", "—")
    try:
        subcategory_id = db.add_group(name, parent_id=parent_id)
    except Exception:
        try:
            await _bot_edit(
                message.bot,
                message.chat.id,
                data["msg_id"],
                text="❌ Подкатегория с таким названием уже существует. Введите другое:",
                reply_markup=cancel_kb("admin_panel"),
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    group_name = f"{parent_name} → {name}"
    await state.update_data(
        group_id=subcategory_id,
        group_name=group_name,
        msg_id=data["msg_id"],
    )
    await state.set_state(AdminAddProduct.waiting_name)
    await _bot_edit(
        message.bot,
        message.chat.id,
        data["msg_id"],
        text=(
            f"✅ Подкатегория <b>«{html.escape(name)}»</b> создана!\n\n"
            f"📂 Каталог: <b>{html.escape(group_name)}</b>\n\n"
            "📝 Введите <b>название товара</b>:"
        ),
        reply_markup=cancel_kb("admin_panel"),
        parse_mode="HTML",
    )


# ─── Переименование группы ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_group_rename_"))
async def admin_group_rename_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    group_id = int(call.data.split("_")[3])
    await state.set_state(AdminEditGroup.waiting_name)
    await state.update_data(group_id=group_id, msg_id=call.message.message_id)
    await _admin_edit(
        call, "✏️ Введите <b>новое название</b> группы:",
        cancel_kb(f"admin_group_{group_id}")
    )


@router.message(AdminEditGroup.waiting_name)
async def admin_group_rename_done(message: Message, state: FSMContext):
    data = await state.get_data()
    group_id = data["group_id"]
    new_name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not new_name:
        return
    try:
        db.rename_group(group_id, new_name)
    except Exception:
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Каталог с таким названием уже существует. Введите другое:",
                reply_markup=cancel_kb(f"admin_group_{group_id}"), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    await state.clear()
    groups = db.get_all_groups()
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=f"✅ Каталог переименован в <b>«{new_name}»</b>!\n\n📚 <b>Каталоги</b>\n\nВыберите каталог для управления:",
            reply_markup=kb.admin_groups_list(groups), parse_mode="HTML"
        )
    except Exception:
        await message.answer(
            f"✅ Каталог переименован в <b>«{new_name}»</b>!",
            reply_markup=kb.admin_groups_list(groups), parse_mode="HTML"
        )


# ─── Удаление группы ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_group_del_"))
async def admin_delete_group(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    group_id = int(call.data.split("_")[3])
    group = db.get_group(group_id)
    if group:
        db.delete_group(group_id)
        await call.answer(f"🗑 Группа «{group['name']}» удалена.", show_alert=True)
    groups = db.get_all_groups()
    if not groups:
        kb_empty = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить каталог", callback_data="admin_add_group")],
            [InlineKeyboardButton(text="🔙 Назад",           callback_data="admin_panel")],
        ])
        await _admin_edit(call, "📚 <b>Каталоги</b>\n\nКаталогов больше нет.", kb_empty)
    else:
        await _admin_edit(
            call,
            "📚 <b>Каталоги</b>\n\nВыберите каталог для управления:",
            kb.admin_groups_list(groups)
        )


# ─── Карточка группы ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("admin_group_"))
async def admin_group_card(call: CallbackQuery):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    group_id = int(call.data.split("_")[2])
    group = db.get_group(group_id)
    if not group:
        await call.answer("❌ Группа не найдена.", show_alert=True)
        return
    products_count = len(db.get_products_by_group(group_id))
    text = (
        f"📂 <b>{group['name']}</b>\n\n"
        f"📦 Товаров в группе: <b>{products_count}</b>\n\n"
        "Выберите действие:"
    )
    rm = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"admin_group_rename_{group_id}")],
        [InlineKeyboardButton(text="🔙 Назад",          callback_data="admin_list_groups")],
    ])
    await _admin_edit(call, text, rm)


# ─── Добавление товара ────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_product")
async def admin_add_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    groups = db.get_all_groups()
    await state.update_data(msg_id=call.message.message_id)
    if not groups:
        await state.set_state(AdminAddProduct.waiting_new_group)
        await _admin_edit(
            call,
            "📚 <b>Нет ни одного каталога.</b>\n\nСначала создайте каталог — введите его название:",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
            ])
        )
    else:
        await state.set_state(AdminAddProduct.waiting_group)
        await _admin_edit(
            call,
            "📚 <b>Выберите каталог для позиции</b>\nили создайте новый:",
            kb.admin_choose_group(groups)
        )


@router.message(AdminAddProduct.waiting_new_group)
async def admin_add_new_group_inline(message: Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not name:
        return
    try:
        group_id = db.add_group(name)
    except Exception:
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Каталог с таким названием уже существует. Введите другое:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
                ]), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    await state.update_data(group_id=group_id, group_name=name)
    await state.set_state(AdminAddProduct.waiting_name)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=f"✅ Каталог <b>«{name}»</b> создан!\n\n📝 Шаг 1/3 — Введите <b>название позиции</b>:",
            reply_markup=cancel_kb(), parse_mode="HTML"
        )
    except Exception:
        await message.answer(
            f"✅ Каталог <b>«{name}»</b> создан!\n\n📝 Введите <b>название позиции</b>:",
            reply_markup=cancel_kb(), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("pick_group_"), AdminAddProduct.waiting_group)
async def admin_pick_group(call: CallbackQuery, state: FSMContext):
    value = call.data.split("pick_group_")[1]
    if value == "new":
        await state.set_state(AdminAddProduct.waiting_new_group)
        await _admin_edit(call, "📚 Введите название <b>нового каталога</b>:", cancel_kb())
        return
    group_id = int(value)
    group = db.get_group(group_id)
    if not group:
        await call.answer("❌ Каталог не найден.", show_alert=True)
        return
    await state.update_data(group_id=group_id, group_name=group["name"])
    await state.set_state(AdminAddProduct.waiting_name)
    await _admin_edit(
        call,
        f"✅ Каталог: <b>{group['name']}</b>\n\n📝 Шаг 1/3 — Введите <b>название позиции</b>:",
        cancel_kb()
    )


@router.message(AdminAddProduct.waiting_name)
async def admin_add_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not name:
        return
    await state.update_data(name=name)
    await state.set_state(AdminAddProduct.waiting_price)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Группа: <b>{data.get('group_name', '—')}</b>\n"
                f"✅ Название: <b>{name}</b>\n\n"
                "💰 Шаг 2/3 — Введите <b>цену</b> в рублях (например: 199):"
            ),
            reply_markup=cancel_kb(), parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(AdminAddProduct.waiting_price)
async def admin_add_price(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text=(
                    f"✅ Группа: <b>{data.get('group_name', '—')}</b>\n"
                    f"✅ Название: <b>{data['name']}</b>\n\n"
                    "❌ Некорректная цена. Введите число больше 0:"
                ),
                reply_markup=cancel_kb(), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    await state.update_data(price=price)
    await state.set_state(AdminAddProduct.waiting_content_type)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Группа: <b>{data.get('group_name', '—')}</b>\n"
                f"✅ Название: <b>{data['name']}</b>\n"
                f"✅ Цена: <b>{price}₽</b>\n\n"
                "📦 Шаг 3/3 — Выберите <b>тип содержимого</b>:"
            ),
            reply_markup=kb.admin_content_type_menu(), parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("ctype_"))
async def admin_add_ctype(call: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    if current != AdminAddProduct.waiting_content_type:
        return
    ctype = call.data.split("_")[1]
    await state.update_data(content_type=ctype)
    await state.set_state(AdminAddProduct.waiting_content)
    data = await state.get_data()
    prompts = {
        "text":  "📝 Отправьте <b>текст</b> товара:",
        "link":  "🔗 Отправьте <b>ссылку</b> товара:",
        "file":  "📁 Отправьте <b>файл</b> товара:",
        "photo": "🖼 Отправьте <b>текст</b> товара (будет показан с фото):",
    }
    await _admin_edit(
        call,
        f"✅ Группа: <b>{data.get('group_name', '—')}</b>\n"
        f"✅ Название: <b>{data['name']}</b>\n"
        f"✅ Цена: <b>{data['price']}₽</b>\n\n"
        + prompts[ctype],
        cancel_kb()
    )


@router.message(AdminAddProduct.waiting_content)
async def admin_add_content(message: Message, state: FSMContext):
    data = await state.get_data()
    ctype = data.get("content_type", "text")
    try:
        await message.delete()
    except Exception:
        pass
    if ctype == "file":
        if not message.document:
            try:
                await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                    text="❌ Пожалуйста, отправьте файл.", reply_markup=cancel_kb()
                )
            except Exception:
                pass
            return
        content = message.document.file_id
    elif ctype == "photo":
        content = message.text.strip() if message.text else ""
        if not content:
            try:
                await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                    text="❌ Введите текст товара.", reply_markup=cancel_kb()
                )
            except Exception:
                pass
            return
    else:
        content = message.text.strip() if message.text else ""
        if not content:
            try:
                await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                    text="❌ Содержимое не может быть пустым.", reply_markup=cancel_kb()
                )
            except Exception:
                pass
            return
    await state.update_data(content=content)
    await state.set_state(AdminAddProduct.waiting_photo)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Содержимое сохранено.\n\n"
                f"📂 Группа: <b>{data.get('group_name', '—')}</b>\n"
                f"📦 Название: <b>{data['name']}</b>\n"
                f"💰 Цена: <b>{data['price']}₽</b>\n\n"
                "🖼 Отправьте фотографию для карточки товара "
                "или нажмите «Пропустить фото»:"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="skip_photo")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")],
            ]),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(AdminAddProduct.waiting_photo)
async def admin_add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    if not message.photo:
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text="❌ Отправьте фото или нажмите «Пропустить».",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⏭ Пропустить фото", callback_data="skip_photo")],
                    [InlineKeyboardButton(text="❌ Отмена",           callback_data="admin_panel")],
                ])
            )
        except Exception:
            pass
        return
    photo_id = message.photo[-1].file_id
    db.add_product(
        data["name"],
        data["price"],
        data["content"],
        data.get("content_type", "text"),
        data.get("group_id"),
        photo_id,
    )
    await state.clear()
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Товар с фото добавлен!\n\n"
                f"📂 Группа: <b>{data.get('group_name', '—')}</b>\n"
                f"📦 Название: <b>{data['name']}</b>\n"
                f"💰 Цена: <b>{data['price']}₽</b>"
            ),
            reply_markup=kb.admin_menu(db.is_maintenance()), parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data == "skip_photo")
async def skip_photo(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_product(
        data["name"],
        data["price"],
        data["content"],
        data.get("content_type", "text"),
        data.get("group_id"),
    )
    await state.clear()
    await _admin_edit(
        call,
        f"✅ Товар добавлен без фото!\n\n"
        f"📂 Группа: <b>{data.get('group_name', '—')}</b>\n"
        f"📦 Название: <b>{data['name']}</b>\n"
        f"💰 Цена: <b>{data['price']}₽</b>",
        kb.admin_menu(db.is_maintenance())
    )


# ─── Промокоды ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_promo")
async def admin_promo_start(call: CallbackQuery, state: FSMContext):
    if not is_user_authorized(call.from_user.id):
        await call.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.set_state(AdminAddPromo.waiting_code)
    await state.update_data(msg_id=call.message.message_id)
    await _admin_edit(call, "🎟 Шаг 1/3 — Введите <b>код</b> промокода:", cancel_kb())


@router.message(AdminAddPromo.waiting_code)
async def admin_promo_code(message: Message, state: FSMContext):
    data = await state.get_data()
    code = message.text.strip() if message.text else ""
    try:
        await message.delete()
    except Exception:
        pass
    if not code:
        return
    await state.update_data(code=code)
    await state.set_state(AdminAddPromo.waiting_amount)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=f"✅ Код: <b>{code}</b>\n\n💰 Шаг 2/3 — Введите <b>сумму</b> пополнения (в рублях):",
            reply_markup=cancel_kb(), parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(AdminAddPromo.waiting_amount)
async def admin_promo_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text=f"✅ Код: <b>{data['code']}</b>\n\n❌ Некорректная сумма. Введите число больше 0:",
                reply_markup=cancel_kb(), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    await state.update_data(amount=amount)
    await state.set_state(AdminAddPromo.waiting_uses)
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Код: <b>{data['code']}</b>\n"
                f"✅ Сумма: <b>{amount}₽</b>\n\n"
                "🔢 Шаг 3/3 — Введите <b>количество использований</b>:"
            ),
            reply_markup=cancel_kb(), parse_mode="HTML"
        )
    except Exception:
        pass


@router.message(AdminAddPromo.waiting_uses)
async def admin_promo_uses(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.delete()
    except Exception:
        pass
    try:
        uses = int(message.text.strip())
        if uses <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        try:
            await _bot_edit(message.bot, message.chat.id, data["msg_id"],
                text=(
                    f"✅ Код: <b>{data['code']}</b>\n"
                    f"✅ Сумма: <b>{data['amount']}₽</b>\n\n"
                    "❌ Введите целое число больше 0:"
                ),
                reply_markup=cancel_kb(), parse_mode="HTML"
            )
        except Exception:
            pass
        return
    db.add_promo(data["code"], data["amount"], uses)
    await state.clear()
    try:
        await _bot_edit(message.bot, message.chat.id, data["msg_id"],
            text=(
                f"✅ Промокод создан!\n\n"
                f"🎟 Код: <b>{data['code']}</b>\n"
                f"💰 Сумма: <b>{data['amount']}₽</b>\n"
                f"🔢 Использований: <b>{uses}</b>"
            ),
            reply_markup=kb.admin_menu(db.is_maintenance()), parse_mode="HTML"
        )
    except Exception:
        pass

