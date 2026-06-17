import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import config
import database
import handlers

# Loggingni sozlash (Konsolga chiroyli loglar chiqarish)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    # Chiroyli konsol bannerini chiqarish
    banner = r"""
  ======================================================
     ____        _           _   ____        _   
    / ___| __ _ | |__  _   _| | | __ )  ___ | |_ 
   | |  _ / _` || '_ \| | | | | |  _ \ / _ \| __|
   | |_| | (_| || |_) | |_| | | | |_) | (_) | |_ 
    \____|\__,_||_.__/ \__,_|_| |____/ \___/ \__|
                                                  
     QABUL BOT TIZIMI -- PRODUCTION READY ACTIVE
  ======================================================
    """
    print(banner)
    
    logger.info("Qabul bot tizimi ishga tushmoqda...")
    
    # 1. Ma'lumotlar bazasini tekshirish va yaratish
    logger.info("SQLite ma'lumotlar bazasi tekshirilmoqda...")
    database.init_db()
    
    # 2. Bot va Dispatcher obyektlarini yaratish
    logger.info("Telegram Bot API ulanishi yaratilmoqda...")
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    
    dp = Dispatcher()
    
    # 3. Routerlarni ro'yxatdan o'tkazish
    logger.info("Routerlar dispatcherga ulanmoqda...")
    dp.include_router(handlers.get_router())
    
    # 4. Oldingi kelib tushgan xabarlarni o'chirib yuborish (webhook tozalash)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 5. Pollingni boshlash
    logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni tinglamoqda. 🚀")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot faoliyati to'xtatildi. 🛑")
