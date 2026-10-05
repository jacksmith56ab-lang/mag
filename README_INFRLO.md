# Ricerve — Infrlo deployment

This bundle runs the Telegram bot and the admin Mini App in ONE Infrlo service so both processes share the same SQLite database.

## Runtime requirements
- Node.js 24+
- Python 3.10+
- `pip`

The admin frontend/API build is already included in the archive, so Node dependencies are not needed at runtime.

## Build command
```sh
python3 -m pip install --user -r requirements.txt
```
If Infrlo does not allow `--user`, use:
```sh
python3 -m pip install -r requirements.txt
```

## Start command
```sh
./start.sh
```

## Required environment variables
```text
BOT_TOKEN=...
ADMIN_IDS=123456789
CRYPTO_BOT_TOKEN=...
XROCKET_TOKEN=...
SUPPORT_LINK=https://t.me/...
INFO_CHANNEL=https://t.me/...
ADMIN_WEBAPP_URL=https://YOUR-INFRLO-URL
SHOP_DB_PATH=/absolute/path/to/ricerve-shop-bot/shop.db
```

`SHOP_DB_PATH` is optional: `start.sh` defaults it to `ricerve-shop-bot/shop.db` inside this bundle.

`ADMIN_WEBAPP_URL` can be left empty for the first deployment. After Infrlo gives the app its public HTTPS URL, set `ADMIN_WEBAPP_URL` to that exact URL and restart the service.

## Important
The bot must initialize the database before the admin panel is used. `start.sh` starts the bot first and then the admin server.

The admin Mini App is protected by Telegram `initData` validation using `BOT_TOKEN` and `ADMIN_IDS`.

Do not commit or upload real secrets into source files.
