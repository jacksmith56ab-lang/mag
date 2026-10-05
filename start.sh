#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

DB_PATH="${SHOP_DB_PATH:-$APP_DIR/ricerve-shop-bot/shop.db}"
export SHOP_DB_PATH="$DB_PATH"

mkdir -p "$(dirname "$DB_PATH")"

NODE_VERSION="24.18.0"
NODE_DIR="/tmp/ricerve-node"
NODE_BIN="$NODE_DIR/bin/node"

if [ ! -x "$NODE_BIN" ]; then
    rm -rf "$NODE_DIR"
    mkdir -p "$NODE_DIR"

    python3 - "$NODE_VERSION" "$NODE_DIR" <<'PY'
import sys
import urllib.request
import tarfile
import io

version = sys.argv[1]
target = sys.argv[2]

url = f"https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.gz"

data = urllib.request.urlopen(url, timeout=120).read()

with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
    prefix = f"node-v{version}-linux-x64/"

    for member in tar.getmembers():
        if not member.name.startswith(prefix):
            continue

        member.name = member.name[len(prefix):]

        if member.name:
            tar.extract(member, target)
PY
fi

export PATH="$NODE_DIR/bin:$PATH"

API_DIST="$APP_DIR/ricerve-admin-app/artifacts/api-server/dist"
API_INDEX="$API_DIST/index.mjs"

# Fix paths embedded in the prebuilt API bundle.
if [ -f "$API_INDEX" ]; then
    sed -i "s#/home/runner/workspace/artifacts/api-server/dist#$API_DIST#g" "$API_INDEX"
fi

python3 "$APP_DIR/ricerve-shop-bot/bot.py" &
BOT_PID=$!

cleanup() {
    kill "$BOT_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

export PORT="${PORT:-3000}"
export HOST="${HOST:-0.0.0.0}"

exec "$NODE_BIN" \
    "$APP_DIR/ricerve-admin-app/artifacts/ricerve-admin/standalone-server.mjs"

exec "$NODE_BIN" \
    "$APP_DIR/ricerve-admin-app/artifacts/ricerve-admin/standalone-server.mjs"
