import math
import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LabeledPrice
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import keyboards as kb
from config import (
    CRYPTO_BOT_TOKEN,
    RUB_TO_TON,
    RUB_TO_TON_XROCKET,
    RUB_TO_USDT,
    STAR_RUB_RATE,
    STARS_PER_RUB,
    TON_RUB_RATE,
    XROCKET_TOKEN,
)
from utils import edit_message

router = Router()

CRYPTO_API   = "https://pay.crypt.bot/api"
XROCKET_API  = "https://pay.xrocket.tg"

def stars_to_rub(stars: int) -> float:
    """Сколько рублей зачислить за N звёзд."""
    return round(stars / STARS_PER_RUB, 2)


class StarsCustomState(StatesGroup):
    waiting_amount = State()


# ─── CryptoBot invoice helpers ────────────────────────────────────────────────

async def create_invoice(amount_rub: float, currency: str, user_id: int) -> dict | None:
    if currency == "USDT":
        crypto_amount = round(amount_rub * RUB_TO_USDT, 4)
    else:
        crypto_amount = round(amount_rub * RUB_TO_TON, 4)

    payload = {
        "asset": currency,
        "amount": str(crypto_amount),
        "description": f"Пополнение баланса на {amount_rub}₽",
        "payload": f"{user_id}:{amount_rub}",
    }
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{CRYPTO_API}/createInvoice", json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data["result"]
    except Exception:
        pass
    return None


async def check_invoice(invoice_id: int) -> str | None:
    headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
    params  = {"invoice_ids": invoice_id}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CRYPTO_API}/getInvoices", params=params, headers=headers) as resp:
                data = await resp.json()
                if data.get("ok"):
                    items = data["result"].get("items", [])
                    if items:
                        return items[0]["status"]
    except Exception:
        pass
    return None


# ─── xRocket invoice helpers ─────────────────────────────────────────────────

async def create_xrocket_invoice(amount_rub: float, user_id: int) -> dict | None:
    ton_amount = round(amount_rub * RUB_TO_TON_XROCKET, 6)
    body = {
        "currency": "TONCOIN",
        "amount": ton_amount,
        "description": f"Пополнение баланса на {amount_rub}₽",
        "payload": f"xrocket:{user_id}:{amount_rub}",
    }
    headers = {
        "Rocket-Pay-Key": XROCKET_TOKEN,
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{XROCKET_API}/tg-invoices",
                json=body,
                headers=headers
            ) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"]
    except Exception:
        pass
    return None


async def check_xrocket_invoice(invoice_id: str) -> str | None:
    """Возвращает статус: 'paid', 'active', 'expired' и т.д."""
    headers = {"Rocket-Pay-Key": XROCKET_TOKEN}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{XROCKET_API}/tg-invoices/{invoice_id}",
                headers=headers
            ) as resp:
                data = await resp.json()
                if data.get("success"):
                    return data["data"].get("status")
    except Exception:
        pass
    return None


# ─── Баланс (главная) — обрабатывается в common.py ───────────────────────────


# ─── Пополнение через Telegram Stars ─────────────────────────────────────────

@router.callback_query(F.data == "balance_stars")
async def balance_stars_menu(call: CallbackQuery):
    rub_per_star = round(1 / STARS_PER_RUB, 2)
    await edit_message(
        call,
        f"⭐ <b>Пополнение через Telegram Stars</b>\n\n"
        f"1 звезда ≈ {STAR_RUB_RATE}₽\n"
        f"Курс TON для других способов: ≈ {TON_RUB_RATE}₽ за 1 TON\n\n"
        "Выберите количество звёзд или введите своё:",
        reply_markup=kb.stars_amount_menu()
    )


@router.callback_query(F.data.startswith("topup_stars_") & ~F.data.endswith("custom"))
async def topup_stars_invoice(call: CallbackQuery):
    stars = int(call.data.split("_")[2])
    rub   = stars_to_rub(stars)

    await call.message.answer_invoice(
        title=f"Пополнение баланса на {rub}₽",
        description=f"{stars} ⭐ = {rub}₽ на внутренний баланс магазина",
        payload=f"topup_stars:{stars}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Пополнение {stars} ⭐", amount=stars)],
    )
    await call.answer()


@router.callback_query(F.data == "topup_stars_custom")
async def topup_stars_custom_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(StarsCustomState.waiting_amount)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="balance_stars")]
    ])
    await edit_message(
        call,
        "✏️ <b>Введите количество звёзд</b>\n\n"
        "Минимум: <b>1</b> звезда\n"
        "Например: <code>250</code>",
        reply_markup=cancel_kb
    )


@router.message(StarsCustomState.waiting_amount)
async def topup_stars_custom_process(message: Message, state: FSMContext):
    await state.clear()
    text = message.text.strip() if message.text else ""
    try:
        stars = int(text)
        if stars < 1:
            raise ValueError
    except ValueError:
        cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="balance_stars")]
        ])
        await message.answer(
            "❌ Введите целое число больше 0:",
            reply_markup=cancel_kb,
            parse_mode="HTML"
        )
        await state.set_state(StarsCustomState.waiting_amount)
        return

    rub = stars_to_rub(stars)
    await message.answer_invoice(
        title=f"Пополнение баланса на {rub}₽",
        description=f"{stars} ⭐ = {rub}₽ на внутренний баланс магазина",
        payload=f"topup_stars:{stars}",
        currency="XTR",
        prices=[LabeledPrice(label=f"Пополнение {stars} ⭐", amount=stars)],
    )


# ─── Пополнение через CryptoBot ───────────────────────────────────────────────

@router.callback_query(F.data == "balance_cryptobot")
async def choose_currency(call: CallbackQuery):
    await edit_message(
        call,
        "🤖 <b>Пополнение через CryptoBot</b>\n\nВыберите валюту:",
        reply_markup=kb.currency_menu()
    )


@router.callback_query(F.data.startswith("currency_"))
async def choose_amount(call: CallbackQuery):
    currency = call.data.split("_")[1]
    await edit_message(
        call,
        f"💱 Валюта: <b>{currency}</b>\n\nВыберите сумму пополнения:",
        reply_markup=kb.amount_menu(currency)
    )


@router.callback_query(F.data.startswith("amount_"))
async def create_payment(call: CallbackQuery):
    _, currency, amount_str = call.data.split("_")
    amount_rub = float(amount_str)

    await call.answer("⏳ Создаём счёт...")

    invoice = await create_invoice(amount_rub, currency, call.from_user.id)
    if not invoice:
        await edit_message(call, "❌ Не удалось создать счёт. Попробуйте позже.", reply_markup=kb.balance_menu())
        return

    invoice_id = invoice["invoice_id"]
    pay_url     = invoice["pay_url"]

    db.save_payment(invoice_id, call.from_user.id, amount_rub, currency)

    if currency == "USDT":
        crypto_amount = round(amount_rub * RUB_TO_USDT, 4)
    else:
        crypto_amount = round(amount_rub * RUB_TO_TON, 4)

    text = (
        "🧾 <b>Счёт на оплату</b>\n\n"
        f"🆔 ID платежа: <code>{invoice_id}</code>\n"
        f"💰 Сумма: {amount_rub}₽ ({crypto_amount} {currency})\n\n"
        "Нажмите кнопку ниже для оплаты, затем проверьте статус."
    )
    await edit_message(call, text, reply_markup=kb.payment_menu(pay_url, invoice_id))


@router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(call: CallbackQuery):
    invoice_id = int(call.data.split("_")[2])
    payment = db.get_payment(invoice_id)

    if not payment:
        await call.answer("❌ Платёж не найден.", show_alert=True)
        return

    if payment["status"] == "paid":
        await call.answer("✅ Платёж уже зачислен!", show_alert=True)
        return

    status = await check_invoice(invoice_id)

    if status == "paid":
        db.mark_payment_paid(invoice_id)
        db.update_balance(call.from_user.id, payment["amount"])
        await edit_message(
            call,
            f"✅ Оплата подтверждена!\n\nНа ваш баланс зачислено <b>{payment['amount']}₽</b>."
        )
    else:
        await call.answer("⏳ Оплата ещё не поступила. Попробуйте чуть позже.", show_alert=True)


# ─── Пополнение через xRocket ────────────────────────────────────────────────

@router.callback_query(F.data == "balance_xrocket")
async def balance_xrocket_menu(call: CallbackQuery):
    await edit_message(
        call,
        "🚀 <b>Пополнение через xRocket</b>\n\n"
        f"Оплата в TONCOIN (курс ~{TON_RUB_RATE}₽ за 1 TON)\n\n"
        "Выберите сумму пополнения:",
        reply_markup=kb.xrocket_amount_menu()
    )


@router.callback_query(F.data.startswith("xrocket_amount_"))
async def xrocket_create_payment(call: CallbackQuery):
    amount_rub = float(call.data.split("_")[2])
    ton_amount = round(amount_rub * RUB_TO_TON_XROCKET, 6)

    await call.answer("⏳ Создаём счёт...")

    invoice = await create_xrocket_invoice(amount_rub, call.from_user.id)
    if not invoice:
        await edit_message(
            call,
            "❌ Не удалось создать счёт xRocket. Попробуйте позже.",
            reply_markup=kb.balance_menu()
        )
        return

    invoice_id = str(invoice["id"])
    pay_url    = invoice["link"]

    # Сохраняем в таблицу payments (используем строковый id как invoice_id через хэш)
    # Т.к. payments.invoice_id INTEGER — используем hash для совместимости
    # Храним оригинальный xrocket_id в payload через save_payment с currency=TONCOIN
    # Для проверки xrocket используем отдельный callback с полным id
    db.save_payment(hash(invoice_id) & 0x7FFFFFFF, call.from_user.id, amount_rub, "TONCOIN")

    text = (
        "🧾 <b>Счёт xRocket</b>\n\n"
        f"💎 Сумма: {amount_rub}₽ ({ton_amount} TON)\n\n"
        "Нажмите кнопку ниже для оплаты через xRocket, затем проверьте статус."
    )
    await edit_message(call, text, reply_markup=kb.xrocket_payment_menu(pay_url, invoice_id))


@router.callback_query(F.data.startswith("xrocket_check_"))
async def xrocket_check_payment(call: CallbackQuery):
    # invoice_id — строка из xrocket
    invoice_id = call.data[len("xrocket_check_"):]

    await call.answer("⏳ Проверяем...")

    status = await check_xrocket_invoice(invoice_id)

    if status == "paid":
        # Находим сумму из payload в тексте сообщения (резервный метод)
        # Пытаемся найти платёж по хэшу
        int_id = hash(invoice_id) & 0x7FFFFFFF
        payment = db.get_payment(int_id)
        amount  = payment["amount"] if payment else 0

        if payment and payment["status"] == "paid":
            await call.answer("✅ Платёж уже зачислен!", show_alert=True)
            return

        if payment:
            db.mark_payment_paid(int_id)
        db.update_balance(call.from_user.id, amount)

        await edit_message(
            call,
            f"✅ Оплата xRocket подтверждена!\n\nНа ваш баланс зачислено <b>{amount}₽</b>."
        )
    elif status is None:
        await call.answer("❌ Не удалось проверить статус. Попробуйте позже.", show_alert=True)
    else:
        await call.answer("⏳ Оплата ещё не поступила. Попробуйте чуть позже.", show_alert=True)
