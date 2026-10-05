# Ricerve Shop Admin Mini App

This is the separate Telegram-only admin panel. The customer storefront remains the Telegram bot. The archive contains the admin frontend, API source/build, and a small standalone Node server; it contains no bot token or shop database.

## Shared data and access

- Set `BOT_TOKEN` as a secret, never in source code.
- Set `ADMIN_IDS` to the Telegram owner ID(s), comma-separated.
- Set `SHOP_DB_PATH` to the exact same SQLite file used by the bot. If the bot archive is extracted as `shop-bot/` beside this project, the API's default path resolves to `shop-bot/shop.db`.
- Start the bot once so it creates/updates its SQLite tables before using the admin panel.
- Use Node.js 24+ (the API uses Node's built-in SQLite module) and pnpm.

## Standalone run

From this archive's project root:

```sh
pnpm install
pnpm --filter @workspace/api-server run build
PORT=5173 BASE_PATH=/ pnpm --filter @workspace/ricerve-admin run build
PORT=3000 RICERVE_API_PORT=3001 SHOP_DB_PATH=/absolute/path/to/shop-bot/shop.db ADMIN_IDS=YOUR_TELEGRAM_ID node artifacts/ricerve-admin/standalone-server.mjs
```

Provide `BOT_TOKEN` through your host's secret/environment-variable manager before starting the server. The standalone server serves the built frontend and proxies `/api` to the bundled API process.

## Replit preview and Telegram launch

The archive retains the Replit artifact definitions. In a Replit workspace, run the managed `artifacts/api-server: API Server` and `artifacts/ricerve-admin: web` workflows. Once the admin app has been published at an HTTPS URL, set `ADMIN_WEBAPP_URL` for the bot to that URL and configure the domain with BotFather. The bot adds the shortcut to its admin panel only when this HTTPS URL is set.

Opening the URL in an ordinary browser shows the Telegram access gate by design. The panel requires Telegram Mini App `initData`, verified server-side with the bot token.
