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

        # Asosiy sahifa uchun chiroyli HTML status sahifasi (ping xizmatlari 200 qaytarishi uchun)
        async def handle_root(request):
            html_content = """
            <!DOCTYPE html>
            <html lang="uz">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Qabul Bot Status</title>
                <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
                <style>
                    body {
                        margin: 0;
                        padding: 0;
                        font-family: 'Outfit', sans-serif;
                        background: radial-gradient(circle at top right, #1a1c29, #0e1017);
                        color: #ffffff;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        overflow: hidden;
                    }
                    .card {
                        background: rgba(255, 255, 255, 0.03);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 24px;
                        padding: 40px;
                        text-align: center;
                        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
                        max-width: 400px;
                        width: 90%;
                        transform: translateY(0);
                        transition: all 0.3s ease;
                    }
                    .card:hover {
                        transform: translateY(-5px);
                        border-color: rgba(99, 102, 241, 0.3);
                        box-shadow: 0 30px 60px rgba(99, 102, 241, 0.1);
                    }
                    .logo-container {
                        position: relative;
                        width: 100px;
                        height: 100px;
                        margin: 0 auto 20px;
                    }
                    .logo {
                        width: 100px;
                        height: 100px;
                        border-radius: 50%;
                        background: linear-gradient(135deg, #6366f1, #a855f7);
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-size: 42px;
                        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
                    }
                    .pulse {
                        position: absolute;
                        top: -5px;
                        left: -5px;
                        right: -5px;
                        bottom: -5px;
                        border-radius: 50%;
                        border: 2px solid #6366f1;
                        animation: pulse-animation 2s infinite;
                        opacity: 0;
                    }
                    @keyframes pulse-animation {
                        0% {
                            transform: scale(0.95);
                            opacity: 0.8;
                        }
                        100% {
                            transform: scale(1.15);
                            opacity: 0;
                        }
                    }
                    h1 {
                        font-size: 28px;
                        font-weight: 800;
                        margin: 10px 0 5px;
                        background: linear-gradient(to right, #ffffff, #a5b4fc);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                    }
                    p {
                        color: #94a3b8;
                        font-size: 16px;
                        margin-bottom: 25px;
                    }
                    .status-badge {
                        display: inline-flex;
                        align-items: center;
                        gap: 8px;
                        background: rgba(16, 185, 129, 0.1);
                        border: 1px solid rgba(16, 185, 129, 0.2);
                        color: #34d399;
                        padding: 8px 16px;
                        border-radius: 100px;
                        font-size: 14px;
                        font-weight: 600;
                        letter-spacing: 0.5px;
                    }
                    .status-dot {
                        width: 8px;
                        height: 8px;
                        background-color: #10b981;
                        border-radius: 50%;
                        box-shadow: 0 0 10px #10b981;
                        animation: blink 1.5s infinite;
                    }
                    @keyframes blink {
                        0%, 100% { opacity: 0.5; }
                        50% { opacity: 1; }
                    }
                    .footer {
                        margin-top: 30px;
                        font-size: 12px;
                        color: #475569;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="logo-container">
                        <div class="pulse"></div>
                        <div class="logo">🤖</div>
                    </div>
                    <h1>Qabul Bot</h1>
                    <p>Litsey qabul komissiyasi chatbot tizimi</p>
                    <div class="status-badge">
                        <span class="status-dot"></span>
                        ONLINE • FAOL 24/7
                    </div>
                    <div class="footer">
                        Render.com Webhook status: OK
                    </div>
                </div>
            </body>
            </html>
            """
            return web.Response(text=html_content, content_type="text/html", charset="utf-8")

        app.router.add_get("/", handle_root)
        
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
