# Ricerve Telegram Shop Bot

The storefront stays in Telegram. This archive contains the bot source only; it does not include a token or SQLite database.

## Run

1. Install Python 3.11 or newer and run `python -m pip install -r requirements.txt`.
2. Set `BOT_TOKEN` in the environment (use Replit Secrets when running on Replit).
3. Set `ADMIN_IDS` to the owner's Telegram user ID; multiple IDs can be comma-separated.
4. Optionally set `SHOP_DB_PATH` to the SQLite file location. If omitted, the bot creates `shop.db` in this folder on first start.
5. Start with `python bot.py`.

The web admin shortcut is optional. After the admin app has an HTTPS URL, set `ADMIN_WEBAPP_URL` to that URL; it appears in the bot's admin panel. Configure the app domain with BotFather. If both services use `SHOP_DB_PATH`, they must point to the same SQLite file.

Optional payment-provider environment variables are not included or tested with live payments. Do not put tokens in `config.py` or commit them.
