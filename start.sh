#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DB_PATH="${SHOP_DB_PATH:-$APP_DIR/ricerve-shop-bot/shop.db}"
export SHOP_DB_PATH="$DB_PATH"

mkdir -p "$(dirname "$DB_PATH")"

# The bot and admin panel deliberately use the same SQLite file.
python3 "$APP_DIR/ricerve-shop-bot/bot.py" &
BOT_PID=$!

cleanup() {
  kill "$BOT_PID" 2>/dev/null || true
  wait "$BOT_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Infrlo supplies PORT. The standalone server starts the internal API itself.
export RICERVE_API_PORT="${RICERVE_API_PORT:-3001}"
exec node "$APP_DIR/ricerve-admin-app/artifacts/ricerve-admin/standalone-server.mjs"
