import math
import aiohttp

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import CRYPTO_BOT_TOKEN, RUB_TO_USDT, STARS_PER_RUB
from utils import edit_message

router = Router()

CRYPTO_API  = "https://pay.crypt.bot/api"
def price_to_stars(price_rub: float) -> int:
    """Сколько звёзд нужно заплатить за товар: 1₽ = STARS_PER_RUB звёзд.
    Курс берётся из config.py и округляется вверх до целого числа звёзд."""
    return max(1, math.ceil(price_rub * STARS_PER_RUB))


def price_to_usdt(price_rub: float) -> float:
    return round(price_rub * RUB_TO_USDT, 2)


async def create_product_invoice_usdt(product_id: int, price_rub: float, user_id: int) -> dict | None:
    usdt = price_to_usdt(price_rub)
    payload = {
        "asset": "USDT",
        "amount": str(usdt),
        "description": f"Оплата товара #{product_id}",
        "payload": f"product_usdt:{product_id}:{user_id}",
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


class ProductSearch(StatesGroup):
    waiting_query = State()


class ReviewState(StatesGroup):
    waiting_rating  = State()
    waiting_comment = State()


# ─── Каталог (список групп) ───────────────────────────────────────────────────

@router.callback_query(F.data == "all_products")
async def show_all_products(call: CallbackQuery):
    products = db.get_all_products()
    if not products:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_products")]
        ])
        await edit_message(call, "🛍 <b>Каталог товаров</b>\n\nПозиции пока не добавлены.", reply_markup=back_kb)
        return
    await edit_message(
        call,
        f"🛍 <b>Каталог товаров</b>\n\nВсего позиций: {len(products)}",
        reply_markup=kb.products_list(products, group_id=None, back_cb="menu_products")
    )


# ─── Товары внутри группы ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("group_"))
async def show_group(call: CallbackQuery):
    group_id = int(call.data.split("_")[1])
    group = db.get_group(group_id)
    if not group:
        await call.answer("❌ Группа не найдена.", show_alert=True)
        return

    parent_id = group["parent_id"]
    back_cb = f"group_{parent_id}" if parent_id else "menu_products"
    subgroups = db.get_subgroups(group_id)
    if subgroups:
        await edit_message(
            call,
            f"📂 <b>{group['name']}</b>\n\nВыберите подкатегорию:",
            reply_markup=kb.groups_list(subgroups, back_cb=back_cb)
        )
        return

    products = db.get_products_by_group(group_id)
    if not products:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)],
        ])
        await edit_message(
            call,
            f"📁 <b>{group['name']}</b>\n\nВ этой подкатегории пока нет товаров.",
            reply_markup=back_kb
        )
        return

    await edit_message(
        call,
        f"📁 <b>{group['name']}</b>\n\nВыберите товар:",
        reply_markup=kb.products_list(products, group_id, back_cb=back_cb)
    )


# ─── Карточка товара ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("product_"))
async def show_product(call: CallbackQuery):
    product_id = int(call.data.split("_")[1])
    product = db.get_product(product_id)
    if not product:
        await call.answer("❌ Товар не найден.", show_alert=True)
        return

    group_id = product["group_id"]
    stars    = price_to_stars(product["price"])
    usdt     = price_to_usdt(product["price"])
    sales    = db.get_product_sales(product_id)

    # Определяем название категории
    if group_id:
        group = db.get_group(group_id)
        category_name = group["name"] if group else "—"
    else:
        category_name = "Все товары"

    # Создаём USDT-счёт для прямой оплаты
    invoice = await create_product_invoice_usdt(product_id, product["price"], call.from_user.id)
    pay_url = invoice["pay_url"] if invoice else None

    text = (
        f"🔹 <b>{product['name']}</b>\n"
        f"📂 Категория: <b>{category_name}</b>\n\n"
        f"💰 Цена: <b>{product['price']}₽</b>  (~{stars} ⭐ / {usdt} USDT)\n"
        f"📊 Продаж: <b>{sales['today']}</b> сегодня / <b>{sales['total']}</b> всего\n\n"
        "Выберите способ оплаты:"
    )

    # Если у товара есть фото — отправляем с фото
    photo_id = product["photo_id"] if "photo_id" in product.keys() else None
    card_kb = kb.product_card(product_id, group_id, stars, usdt, pay_url)

    if photo_id:
        try:
            await call.message.edit_media(
                media=__import__('aiogram').types.InputMediaPhoto(media=photo_id, caption=text, parse_mode="HTML"),
                reply_markup=card_kb
            )
        except Exception:
            # Если текущее сообщение не фото — отправляем новое
            await call.message.answer_photo(photo=photo_id, caption=text, parse_mode="HTML", reply_markup=card_kb)
    else:
        await edit_message(call, text, reply_markup=card_kb)


# ─── Покупка с баланса ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy_") & ~F.data.startswith("buy_stars_"))
async def buy_product(call: CallbackQuery):
    product_id = int(call.data.split("_")[1])
    product = db.get_product(product_id)
    if not product:
        await call.answer("❌ Товар не найден.", show_alert=True)
        return

    user    = db.get_user(call.from_user.id)
    balance = user["balance"] if user else 0

    if balance < product["price"]:
        await call.answer(
            f"❌ Недостаточно средств!\nНужно: {product['price']}₽\nВаш баланс: {balance}₽",
            show_alert=True
        )
        return

    db.update_balance(call.from_user.id, -product["price"])
    db.add_purchase(call.from_user.id, product_id, product["name"], product["price"])
    await _deliver_product(call.message, product, user_id=call.from_user.id)


# ─── Покупка за звёзды ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars(call: CallbackQuery):
    product_id = int(call.data.split("_")[2])
    product = db.get_product(product_id)
    if not product:
        await call.answer("❌ Товар не найден.", show_alert=True)
        return

    stars = price_to_stars(product["price"])

    await call.message.answer_invoice(
        title=product["name"],
        description=f"Цифровой товар · {product['price']}₽ · {stars} ⭐",
        payload=f"stars_buy:{product_id}",
        currency="XTR",
        prices=[LabeledPrice(label=product["name"], amount=stars)],
    )
    await call.answer()


# ─── Pre-checkout ─────────────────────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    payload = query.invoice_payload
    try:
        kind, value = payload.split(":", 1)
        if kind == "stars_buy":
            if db.get_product(int(value)):
                await query.answer(ok=True)
                return
        elif kind in ("topup", "topup_stars"):
            await query.answer(ok=True)
            return
    except Exception:
        pass
    await query.answer(ok=False, error_message="Товар больше недоступен.")


# ─── Успешная оплата звёздами ─────────────────────────────────────────────────

@router.message(F.successful_payment)
async def stars_payment_done(message: Message):
    payload    = message.successful_payment.invoice_payload
    stars_paid = message.successful_payment.total_amount

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])

    try:
        kind, value = payload.split(":", 1)
    except Exception:
        await message.answer("✅ Оплата получена, но не удалось обработать. Обратитесь в поддержку.")
        return

    if kind == "topup_stars":
        # value = количество звёзд
        from config import STARS_PER_RUB
        rub = round(stars_paid / STARS_PER_RUB, 2)
        db.update_balance(message.from_user.id, rub)
        await message.answer(
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"Оплачено: <b>{stars_paid} ⭐</b>\n"
            f"Зачислено: <b>{rub}₽</b>",
            reply_markup=back_kb,
            parse_mode="HTML"
        )

    elif kind == "topup":
        # legacy — на случай старых инвойсов
        rub = float(value)
        db.update_balance(message.from_user.id, rub)
        await message.answer(
            f"✅ <b>Баланс пополнен!</b>\n\n"
            f"Оплачено: <b>{stars_paid} ⭐</b>\n"
            f"Зачислено: <b>{rub}₽</b>",
            reply_markup=back_kb,
            parse_mode="HTML"
        )

    elif kind == "stars_buy":
        product = db.get_product(int(value))
        if not product:
            await message.answer("✅ Оплата получена, но товар не найден. Обратитесь в поддержку.")
            return
        db.add_purchase(message.from_user.id, product["id"], product["name"], product["price"])
        await _deliver_product(message, product, paid_stars=stars_paid, user_id=message.from_user.id)


# ─── Выдача товара ────────────────────────────────────────────────────────────

async def _deliver_product(msg, product, paid_stars: int = None, user_id: int = None):
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])

    if paid_stars is not None:
        summary = (
            f"✅ <b>Оплата звёздами успешна!</b>\n\n"
            f"Товар: <b>{product['name']}</b>\n"
            f"Оплачено: <b>{paid_stars} ⭐</b>\n\n"
            "Ваш товар 👇"
        )
    else:
        summary = (
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"Товар: <b>{product['name']}</b>\n"
            f"Списано: <b>{product['price']}₽</b>\n\n"
            "Ваш товар 👇"
        )

    await msg.answer(summary, parse_mode="HTML")

    ctype    = product["content_type"]
    content  = product["content"]
    photo_id = product["photo_id"] if "photo_id" in product.keys() else None

    if ctype == "text":
        await msg.answer(
            f"📦 <b>Ваш товар:</b>\n\n<code>{content}</code>",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
    elif ctype == "photo":
        # Текст + фото
        if photo_id:
            await msg.answer_photo(
                photo=photo_id,
                caption=f"📦 <b>Ваш товар:</b>\n\n<code>{content}</code>",
                reply_markup=back_kb,
                parse_mode="HTML"
            )
        else:
            await msg.answer(
                f"📦 <b>Ваш товар:</b>\n\n<code>{content}</code>",
                reply_markup=back_kb,
                parse_mode="HTML"
            )
    elif ctype == "link":
        await msg.answer(
            f"🔗 <b>Ваш товар (ссылка):</b>\n{content}",
            reply_markup=back_kb,
            parse_mode="HTML"
        )
    elif ctype == "file":
        await msg.answer_document(
            document=content,
            caption="📁 Ваш товар",
            reply_markup=back_kb
        )

    # Запрос отзыва (если пользователь ещё не оставлял хороший отзыв)
    if user_id and not db.is_good_reviewer(user_id):
        await msg.answer(
            "⭐ <b>Оцените ваш опыт покупки!</b>",
            reply_markup=kb.review_rating_kb(product["id"]),
            parse_mode="HTML"
        )


# ─── Система отзывов ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("review_skip_"))
async def review_skip(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.answer("Хорошо, может в следующий раз!")


@router.callback_query(F.data.startswith("review_rating_"))
async def review_rating(call: CallbackQuery, state: FSMContext):
    # format: review_rating_{rating}_{product_id}
    parts      = call.data.split("_")
    rating     = int(parts[2])
    product_id = int(parts[3])

    await state.update_data(rating=rating, product_id=product_id)
    await state.set_state(ReviewState.waiting_rating)

    if rating <= 3:
        text = (
            f"Вы поставили: {'⭐' * rating}\n\n"
            "😔 Жаль что не всё понравилось. Опишите что пошло не так — "
            "мы обязательно исправим ошибки в будущем!"
        )
    else:
        text = (
            f"Вы поставили: {'⭐' * rating}\n\n"
            "🙏 Рады что вам понравилось! Хотите оставить комментарий?"
        )

    await call.message.edit_text(
        text,
        reply_markup=kb.review_comment_kb(product_id, rating),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("review_change_"))
async def review_change(call: CallbackQuery, state: FSMContext):
    product_id = int(call.data.split("_")[2])
    await state.clear()
    await call.message.edit_text(
        "⭐ <b>Оцените ваш опыт покупки!</b>",
        reply_markup=kb.review_rating_kb(product_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("review_write_"))
async def review_write(call: CallbackQuery, state: FSMContext):
    # format: review_write_{product_id}_{rating}
    parts      = call.data.split("_")
    product_id = int(parts[2])
    rating     = int(parts[3])
    await state.set_state(ReviewState.waiting_comment)
    await state.update_data(product_id=product_id, rating=rating, review_msg_id=call.message.message_id)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"review_change_{product_id}")]
    ])
    await call.message.edit_text(
        "✍️ <b>Напишите ваш комментарий:</b>",
        reply_markup=cancel_kb,
        parse_mode="HTML"
    )


@router.message(ReviewState.waiting_comment)
async def review_save_comment(message: Message, state: FSMContext):
    data       = await state.get_data()
    product_id = data.get("product_id")
    rating     = data.get("rating")
    comment    = message.text.strip() if message.text else None
    msg_id     = data.get("review_msg_id")

    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass

    db.add_review(message.from_user.id, product_id, rating, comment)
    if rating >= 4:
        db.mark_good_reviewer(message.from_user.id)
        reply_text = "✅ Спасибо за отзыв!"
    else:
        reply_text = "✅ Спасибо! Мы учтём ваш отзыв и постараемся стать лучше."

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])

    # Редактируем исходное сообщение с запросом отзыва
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_id,
            text=reply_text,
            reply_markup=back_kb
        )
    except Exception:
        await message.answer(reply_text, reply_markup=back_kb)


@router.callback_query(F.data.startswith("review_nocomment_"))
async def review_nocomment(call: CallbackQuery, state: FSMContext):
    # format: review_nocomment_{product_id}_{rating}
    parts      = call.data.split("_")
    product_id = int(parts[2])
    rating     = int(parts[3])

    await state.clear()
    db.add_review(call.from_user.id, product_id, rating, None)

    if rating >= 4:
        db.mark_good_reviewer(call.from_user.id)
        reply_text = "✅ Спасибо за отзыв!"
    else:
        reply_text = "✅ Спасибо! Мы учтём ваш отзыв и постараемся стать лучше."

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
    ])
    await call.message.edit_text(reply_text, reply_markup=back_kb)


# ─── Поиск товаров ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "search_products")
async def search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(ProductSearch.waiting_query)
    await state.update_data(search_msg_id=call.message.message_id)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_cancel")]
    ])
    await edit_message(
        call,
        "🔍 <b>Поиск товаров</b>\n\nВведите название или часть названия:",
        reply_markup=cancel_kb
    )


@router.callback_query(F.data == "search_cancel")
async def search_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    groups = db.get_all_groups()
    if not groups:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
        ])
        await edit_message(call, "🛍 <b>Каталог товаров</b>\n\nТовары ещё не добавлены.", reply_markup=back_kb)
        return
    await edit_message(call, "🛍 <b>Каталог товаров</b>\n\nВыберите категорию:", reply_markup=kb.groups_list(groups))


@router.message(ProductSearch.waiting_query)
async def search_execute(message: Message, state: FSMContext):
    data  = await state.get_data()
    query = message.text.strip() if message.text else ""

    try:
        await message.delete()
    except Exception:
        pass

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="search_cancel")]
    ])

    if not query:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=data["search_msg_id"],
                text="🔍 <b>Поиск товаров</b>\n\n❌ Введите хотя бы одно слово:",
                reply_markup=cancel_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    results = db.search_products(query)
    await state.clear()

    if not results:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=data["search_msg_id"],
                text=f"🔍 <b>Поиск:</b> «{query}»\n\n😔 Ничего не найдено.",
                reply_markup=cancel_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    found_text = f"🔍 <b>Результаты поиска:</b> «{query}»\n\nНайдено: {len(results)}"
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data["search_msg_id"],
            text=found_text,
            reply_markup=kb.search_results_kb(results),
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(found_text, reply_markup=kb.search_results_kb(results), parse_mode="HTML")
