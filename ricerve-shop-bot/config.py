import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "")
XROCKET_TOKEN = os.getenv("XROCKET_TOKEN", "")
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "8630192662").split(",")
    if value.strip().isdigit()
}
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/seoload")
INFO_CHANNEL = os.getenv("INFO_CHANNEL", "https://t.me/ricershop")
ADMIN_WEBAPP_URL = os.getenv("ADMIN_WEBAPP_URL", "").strip()

# Курс зафиксирован 07.09.2026 после сравнения нескольких источников:
# USD/RUB: CBR 86.5857, Wise 86.9528, CurrencyRate 86.6154.
# Берём медиану: 86.6154 → 86.62 ₽ за $1.
USD_RUB_RATE = 86.62

# TON/USD: Kraken $1.38, Coinbase $1.39. Берём середину: $1.385.
TON_USD_RATE = 1.385
TON_RUB_RATE = round(TON_USD_RATE * USD_RUB_RATE, 2)

# Telegram Stars: payout около $0.013, web-покупка около $0.0141,
# мобильная покупка около $0.020. Медианное значение — $0.0141 за ⭐.
# 1 ⭐ ≈ 1.22 ₽, поэтому 1 ₽ ≈ 0.82 ⭐.
STAR_USD_RATE = 0.0141
STAR_RUB_RATE = round(STAR_USD_RATE * USD_RUB_RATE, 2)
STARS_PER_RUB = round(1 / STAR_RUB_RATE, 2)

# Денежные эквиваленты для платёжных провайдеров.
RUB_TO_USDT = round(1 / USD_RUB_RATE, 6)
RUB_TO_TON = round(1 / TON_RUB_RATE, 6)
RUB_TO_TON_XROCKET = RUB_TO_TON

# ID группы с топиками для поддержки (форум-группа)
# Создай группу, включи "Темы" в настройках, добавь бота как админа, вставь сюда ID
SUPPORT_GROUP_ID = -1002000000000  # замени на реальный ID своей группы
