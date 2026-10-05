from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import ADMIN_WEBAPP_URL, STAR_RUB_RATE, SUPPORT_LINK, INFO_CHANNEL


# ─── Главное меню ─────────────────────────────────────────────────────────────

def main_menu(is_admin: bool = False, channel_url: str = INFO_CHANNEL):
    keyboard = [
        [
            InlineKeyboardButton(text="🛍 Каталог товаров", callback_data="menu_products"),
            InlineKeyboardButton(text="👤 Профиль",         callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton(text="❓ FAQ",       callback_data="menu_faq"),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu_support"),
        ],
    ]
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(text="📢 Канал", url=channel_url),
            InlineKeyboardButton(text="🛠 Админ", callback_data="admin_panel"),
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="📢 Канал", url=channel_url),
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ─── Профиль ──────────────────────────────────────────────────────────────────

def profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="menu_balance")],
        [InlineKeyboardButton(text="🎟 Промокод",        callback_data="profile_promo")],
        [InlineKeyboardButton(text="🧾 История покупок", callback_data="profile_history")],
        [InlineKeyboardButton(text="🔙 Назад",           callback_data="back_main")],
    ])


# ─── FAQ ──────────────────────────────────────────────────────────────────────

def faq_menu(channel_url: str = INFO_CHANNEL):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Инфо канал", url=channel_url)],
        [InlineKeyboardButton(text="🔙 Назад",      callback_data="back_main")],
    ])


# ─── Поддержка ────────────────────────────────────────────────────────────────

def support_menu():
    from database import get_support_link
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Тех. Поддержка", url=get_support_link())],
        [InlineKeyboardButton(text="🔙 Назад",          callback_data="back_main")],
    ])


# ─── Баланс ───────────────────────────────────────────────────────────────────

def balance_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Звёзды",    callback_data="balance_stars")],
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="balance_cryptobot")],
        [InlineKeyboardButton(text="🚀 xRocket",   callback_data="balance_xrocket")],
        [InlineKeyboardButton(text="🔙 Назад",      callback_data="back_main")],
    ])


# ─── Выбор валюты ─────────────────────────────────────────────────────────────

def currency_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 USDT", callback_data="currency_USDT"),
            InlineKeyboardButton(text="💎 TON",  callback_data="currency_TON"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_balance")],
    ])


# ─── Выбор суммы ──────────────────────────────────────────────────────────────

AMOUNTS = [10, 50, 100, 250, 500, 1000]

def amount_menu(currency: str):
    buttons = [
        InlineKeyboardButton(text=f"{a}₽", callback_data=f"amount_{currency}_{a}")
        for a in AMOUNTS
    ]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="balance_cryptobot")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
    

# ─── Окно оплаты ──────────────────────────────────────────────────────────────

def payment_menu(pay_url: str, invoice_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить счёт",   url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_pay_{invoice_id}")],
        [InlineKeyboardButton(text="❌ Отменить оплату",  callback_data="back_main")],
    ])


# ─── Каталог: список групп ────────────────────────────────────────────────────

def groups_list(groups, back_cb: str = "back_main"):
    """Список всех доступных категорий каталога."""
    buttons = [
        [InlineKeyboardButton(
            text=f"📂 {g['name']}",
            callback_data=f"group_{g['id']}"
        )]
        for g in groups
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Список товаров ───────────────────────────────────────────────────────────

def products_list(products, group_id: int = None, back_cb: str = None):
    """Товары + кнопка поиска + назад."""
    if back_cb is None:
        back_cb = f"group_{group_id}" if group_id else "menu_products"
    buttons = [
        [InlineKeyboardButton(
            text=f"🔹 {p['name']} — {p['price']}₽",
            callback_data=f"product_{p['id']}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Результаты поиска ────────────────────────────────────────────────────────

def search_results_kb(products, back_cb: str = "menu_products"):
    """Список найденных товаров + кнопка назад."""
    buttons = [
        [InlineKeyboardButton(
            text=f"🔹 {p['name']} — {p['price']}₽",
            callback_data=f"product_{p['id']}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Карточка товара ──────────────────────────────────────────────────────────

def product_card(product_id: int, group_id: int = None, stars: int = 0,
                 usdt_price: float = 0, pay_url: str = None,
                 sales_day: int = 0, sales_total: int = 0):
    # Если group_id есть — кнопка назад ведёт в группу, иначе в каталог
    back_cb = f"group_{group_id}" if group_id else "menu_products"
    buttons = [
        [InlineKeyboardButton(text="💳 Купить с баланса",           callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text=f"⭐ Купить за {stars} звёзд",   callback_data=f"buy_stars_{product_id}")],
    ]
    if pay_url and usdt_price:
        buttons.append([InlineKeyboardButton(text=f"💵 Купить за {usdt_price} USDT", url=pay_url)])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Админ-панель ─────────────────────────────────────────────────────────────

def admin_menu(maintenance: bool = False):
    maint_icon = "🔴" if maintenance else "🟢"
    rows = [
        [InlineKeyboardButton(text="➕ Добавить каталог",             callback_data="admin_add_group")],
        [InlineKeyboardButton(text="🎟 Создать промокод",             callback_data="admin_add_promo")],
        [InlineKeyboardButton(text="💸 Выдать баланс",                callback_data="admin_grant_balance")],
        [InlineKeyboardButton(text="👑 Выдать админку",               callback_data="admin_grant_admin")],
        [InlineKeyboardButton(text="👥 Список админов",               callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="📢 Изменить ссылку канала",        callback_data="admin_channel_link")],
        [InlineKeyboardButton(text="📣 Рассылка покупателям",         callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Выгрузить юзеров",             callback_data="admin_export_users")],
        [InlineKeyboardButton(text="📊 Статистика",                   callback_data="admin_stats")],
        [InlineKeyboardButton(text=f"{maint_icon} Тех. режим",        callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton(text="🔙 Выйти",                        callback_data="back_main")],
    ]
    if ADMIN_WEBAPP_URL.startswith("https://"):
        rows.insert(
            0,
            [InlineKeyboardButton(
                text="🌐 Веб-админка",
                web_app=WebAppInfo(url=ADMIN_WEBAPP_URL),
            )],
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_products_list(products):
    buttons = [
        [InlineKeyboardButton(
            text=f"📦 [{p['id']}] {p['name']} — {p['price']}₽",
            callback_data=f"admin_product_{p['id']}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_groups_list(groups):
    buttons = [
        [InlineKeyboardButton(
            text=f"📂 {g['name']}",
            callback_data=f"admin_group_{g['id']}"
        )]
        for g in groups
    ]
    buttons.append([InlineKeyboardButton(text="➕ Добавить каталог", callback_data="admin_add_group")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_choose_root_for_subcategory(groups):
    """Выбор существующего каталога или создание нового."""
    buttons = [
        [InlineKeyboardButton(
            text=f"📂 {group['name']}",
            callback_data=f"admin_choose_catalog_{group['id']}"
        )]
        for group in groups
    ]
    buttons.append([
        InlineKeyboardButton(
            text="➕ Создать новый каталог",
            callback_data="admin_create_root_catalog"
        )
    ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_choose_subcategory(subgroups, parent_id: int):
    """Выбор существующей подкатегории или создание новой."""
    buttons = [
        [InlineKeyboardButton(
            text=f"📁 {group['name']} — добавить товар",
            callback_data=f"admin_add_product_to_subcategory_{group['id']}"
        )]
        for group in subgroups
    ]
    buttons.append([
        InlineKeyboardButton(
            text="➕ Создать подкатегорию",
            callback_data=f"admin_create_subcategory_{parent_id}"
        )
    ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_list_admins(extra_admins, primary_admin_ids):
    """Список главных и дополнительных администраторов."""
    buttons = []
    for user_id in sorted(primary_admin_ids):
        buttons.append([
            InlineKeyboardButton(
                text=f"🔒 Главный админ · ID {user_id}",
                callback_data="admin_protected_admin"
            )
        ])

    for admin in extra_admins:
        username = f"@{admin['username']}" if admin["username"] else f"ID {admin['user_id']}"
        buttons.append([
            InlineKeyboardButton(
                text=f"🛡 {username}",
                callback_data=f"admin_manage_{admin['user_id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_remove_confirm_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🗑 Удалить администратора",
                callback_data=f"admin_remove_confirm_{user_id}"
            )
        ],
        [InlineKeyboardButton(text="🔙 К списку админов", callback_data="admin_list_admins")],
    ])


def admin_content_type_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текст",    callback_data="ctype_text")],
        [InlineKeyboardButton(text="🔗 Ссылка",   callback_data="ctype_link")],
        [InlineKeyboardButton(text="📁 Файл",     callback_data="ctype_file")],
        [InlineKeyboardButton(text="🖼 Текст + фото", callback_data="ctype_photo")],
    ])


def admin_choose_group(groups):
    buttons = [
        [InlineKeyboardButton(
            text=f"📂 {g['name']}",
            callback_data=f"pick_group_{g['id']}"
        )]
        for g in groups
    ]
    buttons.append([InlineKeyboardButton(text="➕ Создать новый каталог", callback_data="pick_group_new")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Пополнение через звёзды ──────────────────────────────────────────────────

# Суммы в звёздах (не в рублях — напрямую звёзды)
STAR_AMOUNTS = [50, 100, 150, 300, 1000]

def stars_amount_menu():
    buttons = []
    for stars in STAR_AMOUNTS:
        buttons.append([InlineKeyboardButton(
            text=f"⭐ {stars} звёзд (~{round(stars * STAR_RUB_RATE)}₽)",
            callback_data=f"topup_stars_{stars}"
        )])
    buttons.append([InlineKeyboardButton(text="✏️ Ввести своё количество", callback_data="topup_stars_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_balance")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── xRocket: выбор суммы ─────────────────────────────────────────────────────

def xrocket_amount_menu():
    buttons = [
        InlineKeyboardButton(text=f"{a}₽", callback_data=f"xrocket_amount_{a}")
        for a in AMOUNTS
    ]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_balance")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def xrocket_payment_menu(pay_url: str, invoice_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через xRocket", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"xrocket_check_{invoice_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="back_main")],
    ])


# ─── Отзывы ───────────────────────────────────────────────────────────────────

def review_rating_kb(product_id: int):
    """Клавиатура выбора оценки 1-5."""
    stars_row = [
        InlineKeyboardButton(text=f"⭐{i}", callback_data=f"review_rating_{i}_{product_id}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        stars_row,
        [InlineKeyboardButton(text="❌ Пропустить", callback_data=f"review_skip_{product_id}")],
    ])


def review_comment_kb(product_id: int, rating: int):
    """Клавиатура после выбора оценки — написать комментарий или пропустить."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Написать комментарий", callback_data=f"review_write_{product_id}_{rating}")],
        [InlineKeyboardButton(text="⬅️ Изменить оценку",      callback_data=f"review_change_{product_id}")],
        [InlineKeyboardButton(text="⏭ Без комментария",       callback_data=f"review_nocomment_{product_id}_{rating}")],
    ])
