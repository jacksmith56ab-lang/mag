import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from utils import edit_message, send_with_photo

router = Router()

IMG_PROFILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "profile.jpeg")


class PromoState(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "menu_profile")
async def show_profile(call: CallbackQuery):
    user     = db.get_user(call.from_user.id)
    username = f"@{call.from_user.username}" if call.from_user.username else call.from_user.first_name
    balance  = user["balance"] if user else 0
    reg_date = user["registered_at"][:10] if user and user["registered_at"] else "—"

    text = (
        "👤 <b>Ваш Профиль</b>\n\n"
        f"🌟 Юзер: {username}\n"
        f"🔑 ID: <code>{call.from_user.id}</code>\n"
        f"💳 Баланс: <b>{balance}₽</b>\n"
        f"📅 Дата регистрации: <b>{reg_date}</b>"
    )
    await send_with_photo(call, text, IMG_PROFILE, reply_markup=kb.profile_menu())


@router.callback_query(F.data == "profile_history")
async def show_history(call: CallbackQuery):
    purchases = db.get_purchases(call.from_user.id)
    if not purchases:
        text = "🧾 <b>История покупок</b>\n\nУ вас пока нет покупок."
    else:
        lines = ["🧾 <b>История покупок</b>\n"]
        for p in purchases:
            lines.append(f"• {p['product_name']} — {p['price']}₽  <i>({p['purchased_at'][:10]})</i>")
        text = "\n".join(lines)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_profile")]
    ])
    await edit_message(call, text, reply_markup=back_kb)


@router.callback_query(F.data == "profile_promo")
async def ask_promo(call: CallbackQuery, state: FSMContext):
    await state.set_state(PromoState.waiting_code)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_profile")]
    ])
    await edit_message(call, "🎟 Введите промокод:", reply_markup=cancel_kb)


@router.message(PromoState.waiting_code)
async def process_promo(message: Message, state: FSMContext):
    await state.clear()
    code = message.text.strip()
    amount = db.use_promo(message.from_user.id, code)
    if amount is None:
        await message.answer(
            "❌ Промокод недействителен или уже был использован.",
            reply_markup=kb.profile_menu()
        )
    else:
        db.update_balance(message.from_user.id, amount)
        await message.answer(
            f"✅ Промокод активирован! На ваш баланс зачислено <b>{amount}₽</b>.",
            reply_markup=kb.profile_menu(),
            parse_mode="HTML"
        )
