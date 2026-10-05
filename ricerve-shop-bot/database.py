import sqlite3
import os

DB_PATH = os.environ.get(
    "SHOP_DB_PATH",
    os.path.join(os.path.dirname(__file__), "shop.db"),
)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _run_migrations():
    """Применяет все миграции схемы. Безопасно при повторном запуске."""
    conn = get_conn()
    c = conn.cursor()

    # ALTER TABLE не поддерживает DEFAULT CURRENT_TIMESTAMP в SQLite < 3.23
    # поэтому добавляем столбец без дефолта и сразу заполняем NULL-значения
    migrations = [
        (
            "ALTER TABLE users ADD COLUMN registered_at DATETIME",
            "UPDATE users SET registered_at = datetime('now') WHERE registered_at IS NULL",
        ),
        (
            "ALTER TABLE users ADD COLUMN last_active DATETIME",
            "UPDATE users SET last_active = datetime('now') WHERE last_active IS NULL",
        ),
        (
            "ALTER TABLE products ADD COLUMN group_id INTEGER REFERENCES product_groups(id) ON DELETE SET NULL",
            None,
        ),
        (
            "ALTER TABLE products ADD COLUMN photo_id TEXT",
            None,
        ),
        (
            "ALTER TABLE product_groups ADD COLUMN parent_id INTEGER REFERENCES product_groups(id) ON DELETE CASCADE",
            None,
        ),
    ]
    for alter_sql, fill_sql in migrations:
        try:
            c.execute(alter_sql)
            conn.commit()
            if fill_sql:
                c.execute(fill_sql)
                conn.commit()
        except Exception:
            pass  # столбец уже существует — нормально
    conn.close()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY,
            username      TEXT,
            first_name    TEXT,
            balance       REAL DEFAULT 0,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_active   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Группы товаров
    c.execute("""
        CREATE TABLE IF NOT EXISTS product_groups (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL UNIQUE,
            parent_id INTEGER REFERENCES product_groups(id) ON DELETE CASCADE
        )
    """)

    # Товары
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            price        REAL NOT NULL,
            content      TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text',
            group_id     INTEGER REFERENCES product_groups(id) ON DELETE SET NULL,
            photo_id     TEXT
        )
    """)

    # История покупок
    c.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price       REAL NOT NULL,
            purchased_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Промокоды
    c.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code        TEXT PRIMARY KEY,
            amount      REAL NOT NULL,
            uses_left   INTEGER NOT NULL
        )
    """)

    # Использованные промокоды
    c.execute("""
        CREATE TABLE IF NOT EXISTS used_promos (
            user_id INTEGER,
            code    TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)

    # Платежи CryptoBot
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            invoice_id  INTEGER PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            amount      REAL NOT NULL,
            currency    TEXT NOT NULL,
            status      TEXT DEFAULT 'pending'
        )
    """)

    # Настройки (тех. режим и т.д.)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Дополнительные администраторы, выданные через админ-панель
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            granted_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Топики поддержки (user_id -> thread_id)
    c.execute("""
        CREATE TABLE IF NOT EXISTS support_topics (
            user_id   INTEGER PRIMARY KEY,
            thread_id INTEGER NOT NULL
        )
    """)

    # Отзывы после покупки
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            rating      INTEGER NOT NULL,
            comment     TEXT,
            reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Пользователи, оставившие хороший отзыв (4-5 звёзд) — им не показываем запрос повторно
    c.execute("""
        CREATE TABLE IF NOT EXISTS good_reviewers (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Web-admin balance changes keep a small audit trail without changing the
    # existing balance or purchase records.
    c.execute("""
        CREATE TABLE IF NOT EXISTS balance_adjustments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id   INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            direction       TEXT NOT NULL CHECK (direction IN ('credit', 'debit')),
            amount          REAL NOT NULL CHECK (amount > 0),
            note            TEXT NOT NULL DEFAULT '',
            previous_balance REAL NOT NULL,
            new_balance     REAL NOT NULL,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    # Применяем миграции ПОСЛЕ того как таблицы точно созданы
    _run_migrations()

    conn = get_conn()
    c = conn.cursor()

    # Создаём группу "Все товары" если нужно, и перемещаем товары без группы
    _migrate_ungrouped_products(c)

    # Дефолтное значение тех. режима
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', '0')")

    conn.commit()
    conn.close()


def _migrate_ungrouped_products(c):
    """Перемещает товары без группы в группу 'Все товары'."""
    ungrouped = c.execute(
        "SELECT COUNT(*) as cnt FROM products WHERE group_id IS NULL"
    ).fetchone()
    if ungrouped and ungrouped[0] > 0:
        # Создаём или находим группу "Все товары"
        existing = c.execute(
            "SELECT id FROM product_groups WHERE name='Все товары'"
        ).fetchone()
        if existing:
            group_id = existing[0]
        else:
            cur = c.execute("INSERT INTO product_groups (name) VALUES ('Все товары')")
            group_id = cur.lastrowid
        c.execute(
            "UPDATE products SET group_id=? WHERE group_id IS NULL", (group_id,)
        )


def get_all_users():
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, username, first_name, registered_at FROM users ORDER BY registered_at"
    ).fetchall()
    conn.close()
    return rows


def get_buyer_ids():
    """Возвращает уникальные Telegram ID пользователей с покупками."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT u.user_id
        FROM users u
        INNER JOIN purchases p ON p.user_id = u.user_id
        ORDER BY u.user_id
        """
    ).fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def ensure_user(user_id: int, username: str, first_name: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )
    conn.execute(
        "UPDATE users SET username=?, first_name=?, last_active=CURRENT_TIMESTAMP WHERE user_id=?",
        (username, first_name, user_id)
    )
    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def update_balance(user_id: int, delta: float):
    conn = get_conn()
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))
    conn.commit()
    conn.close()


# ─── Группы товаров ──────────────────────────────────────────────────────────

def add_group(name: str, parent_id: int = None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO product_groups (name, parent_id) VALUES (?, ?)",
        (name, parent_id)
    )
    conn.commit()
    group_id = cur.lastrowid
    conn.close()
    return group_id


def get_all_groups():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM product_groups ORDER BY id").fetchall()
    conn.close()
    return rows


def get_root_groups():
    """Возвращает каталоги верхнего уровня."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM product_groups WHERE parent_id IS NULL ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def get_subgroups(parent_id: int):
    """Возвращает подкатегории выбранного каталога."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM product_groups WHERE parent_id=? ORDER BY id",
        (parent_id,)
    ).fetchall()
    conn.close()
    return rows


def get_group(group_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM product_groups WHERE id=?", (group_id,)).fetchone()
    conn.close()
    return row


def delete_group(group_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM product_groups WHERE id=?", (group_id,))
    conn.commit()
    conn.close()


def rename_group(group_id: int, new_name: str):
    conn = get_conn()
    conn.execute("UPDATE product_groups SET name=? WHERE id=?", (new_name, group_id))
    conn.commit()
    conn.close()


# ─── Товары ──────────────────────────────────────────────────────────────────

def add_product(name: str, price: float, content: str, content_type: str = "text", group_id: int = None, photo_id: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO products (name, price, content, content_type, group_id, photo_id) VALUES (?, ?, ?, ?, ?, ?)",
        (name, price, content, content_type, group_id, photo_id)
    )
    conn.commit()
    conn.close()


def get_all_products():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return rows


def get_products_by_group(group_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM products WHERE group_id=? ORDER BY id", (group_id,)
    ).fetchall()
    conn.close()
    return rows


def search_products(query: str):
    """Поиск товаров: хотя бы одно слово из запроса встречается в названии."""
    conn = get_conn()
    all_products = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    words = [w.lower() for w in query.strip().split() if w]
    if not words:
        return []
    result = []
    for p in all_products:
        name_lower = p["name"].lower()
        if any(word in name_lower for word in words):
            result.append(p)
    return result


def get_product(product_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return row


def delete_product(product_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def update_product_field(product_id: int, field: str, value):
    """Обновляет одно поле товара. field должен быть доверенным именем столбца."""
    allowed = {"name", "price", "content", "content_type", "group_id", "photo_id"}
    if field not in allowed:
        raise ValueError(f"Недопустимое поле: {field}")
    conn = get_conn()
    conn.execute(f"UPDATE products SET {field}=? WHERE id=?", (value, product_id))
    conn.commit()
    conn.close()


# ─── Покупки ─────────────────────────────────────────────────────────────────

def add_purchase(user_id: int, product_id: int, product_name: str, price: float):
    conn = get_conn()
    conn.execute(
        "INSERT INTO purchases (user_id, product_id, product_name, price) VALUES (?, ?, ?, ?)",
        (user_id, product_id, product_name, price)
    )
    conn.commit()
    conn.close()


def get_purchases(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM purchases WHERE user_id=? ORDER BY purchased_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_product_sales(product_id: int) -> dict:
    """Статистика продаж конкретного товара: за сегодня и всего."""
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM purchases WHERE product_id=?",
        (product_id,)
    ).fetchone()["cnt"]
    today = conn.execute(
        "SELECT COUNT(*) as cnt FROM purchases WHERE product_id=? "
        "AND purchased_at >= date('now')",
        (product_id,)
    ).fetchone()["cnt"]
    conn.close()
    return {"total": total, "today": today}


def get_user_stats(user_id: int):
    """Кол-во покупок и сумма трат конкретного пользователя."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(price), 0) as total FROM purchases WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return {"count": row["count"], "total": row["total"]}


def get_global_stats():
    """Общая статистика по всем покупкам."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(price), 0) as total FROM purchases"
    ).fetchone()
    conn.close()
    return {"count": row["count"], "total": row["total"]}


def get_admin_stats():
    """Расширенная статистика для админ-панели."""
    conn = get_conn()

    total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    active_24h = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE last_active >= datetime('now', '-24 hours')"
    ).fetchone()["cnt"]

    all_purchases = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total FROM purchases"
    ).fetchone()
    purchases_24h = conn.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as total FROM purchases "
        "WHERE purchased_at >= datetime('now', '-24 hours')"
    ).fetchone()

    conn.close()
    return {
        "total_users": total_users,
        "active_24h": active_24h,
        "total_purchases": all_purchases["cnt"],
        "total_revenue": all_purchases["total"],
        "purchases_24h": purchases_24h["cnt"],
        "revenue_24h": purchases_24h["total"],
    }


# ─── Настройки ────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "0") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()


def is_maintenance() -> bool:
    return get_setting("maintenance", "0") == "1"


def toggle_maintenance() -> bool:
    """Переключает тех. режим, возвращает новое состояние."""
    current = is_maintenance()
    set_setting("maintenance", "0" if current else "1")
    return not current


def get_info_channel() -> str:
    """Возвращает ссылку на канал из БД или значение из config.py."""
    from config import INFO_CHANNEL
    return get_setting("info_channel", INFO_CHANNEL)

def get_support_link() -> str:
    """Возвращает ссылку на поддержку из БД или значение из config.py."""
    from config import SUPPORT_LINK
    return get_setting("support_link", SUPPORT_LINK)

def find_user_by_username(username: str):
    """Ищет зарегистрированного пользователя по username без символа @."""
    normalized = (username or "").strip().lstrip("@").lower()
    if not normalized:
        return None
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE lower(username)=?",
        (normalized,)
    ).fetchone()
    conn.close()
    return row


def get_admin_ids() -> set[int]:
    """Возвращает владельцев из config.py и администраторов из БД."""
    from config import ADMIN_IDS
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM admins").fetchall()
    conn.close()
    return set(ADMIN_IDS) | {row["user_id"] for row in rows}


def get_extra_admins():
    """Возвращает администраторов, выданных через админ-панель."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, username, granted_at FROM admins ORDER BY granted_at, user_id"
    ).fetchall()
    conn.close()
    return rows


def get_extra_admin(user_id: int):
    """Возвращает запись дополнительного администратора или None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT user_id, username, granted_at FROM admins WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


def add_admin(user_id: int, username: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO admins (user_id, username) VALUES (?, ?)",
        (user_id, username.lstrip("@") if username else None)
    )
    conn.commit()
    conn.close()


def remove_admin(user_id: int) -> bool:
    """Удаляет только дополнительного администратора из БД."""
    conn = get_conn()
    cursor = conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    removed = cursor.rowcount > 0
    conn.close()
    return removed


# ─── Топики поддержки ─────────────────────────────────────────────────────────

def get_support_thread(user_id: int) -> int | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT thread_id FROM support_topics WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row["thread_id"] if row else None


def save_support_thread(user_id: int, thread_id: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO support_topics (user_id, thread_id) VALUES (?, ?)",
        (user_id, thread_id)
    )
    conn.commit()
    conn.close()


def get_user_by_thread(thread_id: int) -> int | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT user_id FROM support_topics WHERE thread_id=?", (thread_id,)
    ).fetchone()
    conn.close()
    return row["user_id"] if row else None


# ─── Промокоды ───────────────────────────────────────────────────────────────

def add_promo(code: str, amount: float, uses: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO promo_codes (code, amount, uses_left) VALUES (?, ?, ?)",
        (code, amount, uses)
    )
    conn.commit()
    conn.close()


def use_promo(user_id: int, code: str):
    """Возвращает сумму пополнения или None если промокод недействителен."""
    conn = get_conn()
    promo = conn.execute(
        "SELECT * FROM promo_codes WHERE code=? AND uses_left > 0", (code,)
    ).fetchone()
    if not promo:
        conn.close()
        return None
    used = conn.execute(
        "SELECT 1 FROM used_promos WHERE user_id=? AND code=?", (user_id, code)
    ).fetchone()
    if used:
        conn.close()
        return None
    conn.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code=?", (code,))
    conn.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, code))
    conn.commit()
    conn.close()
    return promo["amount"]


# ─── Платежи ─────────────────────────────────────────────────────────────────

def save_payment(invoice_id: int, user_id: int, amount: float, currency: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO payments (invoice_id, user_id, amount, currency) VALUES (?, ?, ?, ?)",
        (invoice_id, user_id, amount, currency)
    )
    conn.commit()
    conn.close()


def get_payment(invoice_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM payments WHERE invoice_id=?", (invoice_id,)).fetchone()
    conn.close()
    return row


def mark_payment_paid(invoice_id: int):
    conn = get_conn()
    conn.execute("UPDATE payments SET status='paid' WHERE invoice_id=?", (invoice_id,))
    conn.commit()
    conn.close()


# ─── Отзывы ──────────────────────────────────────────────────────────────────

def add_review(user_id: int, product_id: int, rating: int, comment: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO reviews (user_id, product_id, rating, comment) VALUES (?, ?, ?, ?)",
        (user_id, product_id, rating, comment)
    )
    conn.commit()
    conn.close()


def is_good_reviewer(user_id: int) -> bool:
    """Возвращает True если пользователь уже оставил отзыв 4-5 звёзд."""
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM good_reviewers WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row is not None


def mark_good_reviewer(user_id: int):
    """Отмечает пользователя как оставившего хороший отзыв."""
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO good_reviewers (user_id) VALUES (?)", (user_id,)
    )
    conn.commit()
    conn.close()
