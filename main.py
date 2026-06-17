import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

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
    logger.info("Ma'lumotlar bazasi tekshirilmoqda...")
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
    
    # 4. Render.com webhook yoki mahalliy polling rejimini aniqlash
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    
    if render_url:
        logger.info("Render.com muhiti aniqlandi. Webhook rejimi ishga tushmoqda...")
        
        # Webhook sozlamalari
        webhook_path = "/webhook"
        webhook_url = f"{render_url}{webhook_path}"
        
        # Webhookni o'rnatish
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        
        # aiohttp ilovasini yaratish
        app = web.Application()
        
        # handler yaratish va uni aiohttp ga ulash
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_handler.register(app, path=webhook_path)
        
        # setup_application clean startup/shutdown uchun
        setup_application(app, dp, bot=bot)
        
        # Portni olish (Render PORT muhit o'zgaruvchisini beradi)
        port = int(os.getenv("PORT", 10000))
        
        # Server runnerini sozlash
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        logger.info(f"Server {port}-portda ishlamoqda. Webhook manzili: {webhook_url}")
        await site.start()
        
        # Server o'chib ketmasligi uchun eventni kutib turamiz
        await asyncio.Event().wait()
    else:
        logger.info("Mahalliy (Local) muhit aniqlandi. Polling rejimi ishga tushmoqda...")
        
        # Oldingi webhookni o'chirib yuborish
        await bot.delete_webhook(drop_pending_updates=True)
        
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
