import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
import database as db
from handlers import common, profile, faq, support, balance, products, admin
from middleware import MaintenanceMiddleware


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help",  description="🆘 Поддержка"),
    ]
    await bot.set_my_commands(commands)


async def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("root").setLevel(logging.INFO)

    db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Подключаем middleware тех. режима
    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())

    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(profile.router)
    dp.include_router(faq.router)
    dp.include_router(support.router)
    dp.include_router(balance.router)
    dp.include_router(products.router)
    dp.include_router(admin.router)

    await set_commands(bot)

    logging.info("Бот запущен.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
