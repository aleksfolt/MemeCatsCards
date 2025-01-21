import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from admin.add_cards import admin_router
from database.cards import init_db
from database.clans import initialize_database
from database.cooldown import init_cd_db
from database.mailing import create_table
from handlers.cards import cards_router
from handlers.clans import clans_router
from handlers.handlers import router
from handlers.profile import profile_router
from middlewares.throttling_middlewares import ThrottlingMiddleware


async def main():
    await create_table()
    await init_db()
    await init_cd_db()
    await initialize_database()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware())
    dp.include_routers(router, cards_router, admin_router,
                       profile_router, clans_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())