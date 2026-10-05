import os
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import CommandStart

import database as db
import keyboards as kb
from utils import send_with_photo, edit_message

router = Router()

# Папка с картинками
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

def img(name: str) -> str:
    path = os.path.join(IMAGES_DIR, name)
    if os.path.exists(path):
        return path
    if name.endswith(".jpg"):
        jpeg_path = os.path.join(IMAGES_DIR, f"{name[:-4]}.jpeg")
        if os.path.exists(jpeg_path):
            return jpeg_path
    return path


def get_display_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Пользователь"


def is_admin(user_id: int) -> bool:
    return user_id in db.get_admin_ids()


def reply_kb(user_id: int) -> ReplyKeyboardMarkup:
    """Reply-клавиатура с быстрыми кнопками."""
    rows = [
        [KeyboardButton(text="🛍 Каталог товаров"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="❓ FAQ"),              KeyboardButton(text="🆘 Поддержка")],
    ]
    if is_admin(user_id):
        rows.append([KeyboardButton(text="🛠 Админ")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    name = get_display_name(message.from_user)
    text = (
        f"👋 Привет, {name}!\n\n"
        "Добро пожаловать в наш магазин цифровых товаров.\n"
        "Выбери нужный раздел в меню ниже 👇"
    )
    welcome_photo = img("welcome.jpg")
    if os.path.exists(welcome_photo):
        await message.answer_photo(
            photo=FSInputFile(welcome_photo),
            caption=text,
            reply_markup=reply_kb(message.from_user.id),
            parse_mode="HTML"
        )
    else:
        await message.answer(text, reply_markup=reply_kb(message.from_user.id))


# ─── Reply-кнопки ────────────────────────────────────────────────────────────

@router.message(F.text.in_({"🛍 Каталог товаров", "📚 Каталог", "🛍 Товары"}))
async def rb_products(message: Message):
    groups   = db.get_root_groups()
    photo    = img("catalog.jpg")
    text     = "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:"
    back_kb  = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

    if not groups:
        text = "🛍 <b>Каталог товаров</b>\n\nКатегории ещё не добавлены. Загляните позже!"
        await message.answer(text, reply_markup=back_kb, parse_mode="HTML")
        return

    kb_groups = kb.groups_list(groups) if groups else back_kb

    if os.path.exists(photo):
        await message.answer_photo(
            photo=FSInputFile(photo),
            caption=text,
            reply_markup=kb_groups,
            parse_mode="HTML"
        )
    else:
        await message.answer(text, reply_markup=kb_groups, parse_mode="HTML")


@router.message(F.text == "👤 Профиль")
async def rb_profile(message: Message):
    user     = db.get_user(message.from_user.id)
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    balance  = user["balance"] if user else 0
    reg_date = user["registered_at"][:10] if user and user["registered_at"] else "—"
    text = (
        "👤 <b>Ваш Профиль</b>\n\n"
        f"🌟 Юзер: {username}\n"
        f"🔑 ID: <code>{message.from_user.id}</code>\n"
        f"💳 Баланс: <b>{balance}₽</b>\n"
        f"📅 Дата регистрации: <b>{reg_date}</b>"
    )
    photo = img("profile.jpg")
    if os.path.exists(photo):
        await message.answer_photo(FSInputFile(photo), caption=text, reply_markup=kb.profile_menu(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb.profile_menu(), parse_mode="HTML")


@router.message(F.text == "❓ FAQ")
async def rb_faq(message: Message):
    from handlers.faq import FAQ_TEXT
    photo = img("faq.jpg")
    if os.path.exists(photo):
        await message.answer_photo(
            FSInputFile(photo),
            caption=FAQ_TEXT,
            reply_markup=kb.faq_menu(db.get_info_channel()),
            parse_mode="HTML"
        )
    else:
        await message.answer(FAQ_TEXT, reply_markup=kb.faq_menu(db.get_info_channel()), parse_mode="HTML")


@router.message(F.text == "🆘 Поддержка")
async def rb_support(message: Message):
    kb_s = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="support_new_ticket")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
    ])
    photo = img("support.jpg")
    text = (
        "🆘 <b>Поддержка</b>\n\n"
        "Возникли вопросы или проблемы?\n"
        "Нажмите кнопку ниже — создадим заявку и я отвечу вам лично."
    )
    if os.path.exists(photo):
        await message.answer_photo(FSInputFile(photo), caption=text, reply_markup=kb_s, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb_s, parse_mode="HTML")


@router.message(F.text == "🛠 Админ")
async def rb_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    from handlers.admin import authorized_admins
    authorized_admins.add(message.from_user.id)
    photo = img("admin.jpg")
    if os.path.exists(photo):
        await message.answer_photo(
            FSInputFile(photo),
            caption="🛠 <b>Админ-панель</b>",
            reply_markup=kb.admin_menu(db.is_maintenance()),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🛠 <b>Админ-панель</b>",
            reply_markup=kb.admin_menu(db.is_maintenance()),
            parse_mode="HTML"
        )


# ─── Inline-кнопки главного меню (callbacks) ─────────────────────────────────

@router.callback_query(F.data == "menu_products")
async def cb_products(call: CallbackQuery):
    groups   = db.get_root_groups()
    back_kb  = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

    if not groups:
        await send_with_photo(
            call,
            "🛍 <b>Каталог товаров</b>\n\nКатегории ещё не добавлены. Загляните позже!",
            img("catalog.jpg"),
            reply_markup=back_kb
        )
        return

    await send_with_photo(
        call,
            "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:",
        img("catalog.jpg"),
            reply_markup=kb.groups_list(groups)
    )


@router.callback_query(F.data == "menu_support")
async def cb_support(call: CallbackQuery):
    kb_s = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="support_new_ticket")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")],
    ])
    text = (
        "🆘 <b>Поддержка</b>\n\n"
        "Возникли вопросы или проблемы?\n"
        "Нажмите кнопку ниже — создадим заявку и я отвечу вам лично."
    )
    await send_with_photo(call, text, img("support.jpg"), reply_markup=kb_s)


@router.callback_query(F.data == "menu_balance")
async def cb_balance(call: CallbackQuery):
    user    = db.get_user(call.from_user.id)
    balance = user["balance"] if user else 0
    text = f"💰 <b>Ваш баланс:</b> {balance}₽\n\nВыберите способ пополнения:"
    await send_with_photo(call, text, img("balance.jpg"), reply_markup=kb.balance_menu())


# ─── back_main callback ───────────────────────────────────────────────────────

@router.callback_query(F.data == "back_main")
async def back_to_main(call: CallbackQuery):
    text = "🏠 Главное меню\n\nВыбери нужный раздел 👇"
    msg = call.message
    # Возвращаем пользователя к нижней reply-клавиатуре,
    # не создавая отдельное inline-меню под сообщением.
    try:
        await msg.delete()
    except Exception:
        pass
    await msg.answer(text, reply_markup=reply_kb(call.from_user.id))
    await call.answer()
