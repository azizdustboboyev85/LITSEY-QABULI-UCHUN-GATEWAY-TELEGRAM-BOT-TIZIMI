import os
from dotenv import load_dotenv

# .env faylidan sozlamalarni yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID_STR = os.getenv("GROUP_ID")

# Sozlamalarni tekshirish va validatsiya qilish
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError(
        "Xatolik: .env faylida BOT_TOKEN topilmadi yoki xato o'rnatilgan! "
        "Iltimos, BotFather orqali olingan tokenni .env fayliga yozing."
    )

if not GROUP_ID_STR or GROUP_ID_STR == "-100XXXXXXXXXX":
    raise ValueError(
        "Xatolik: .env faylida GROUP_ID topilmadi yoki xato o'rnatilgan! "
        "Iltimos, mas'ullar guruhi ID-sini .env fayliga yozing."
    )

try:
    GROUP_ID = int(GROUP_ID_STR)
except ValueError:
    raise ValueError(
        f"Xatolik: GROUP_ID butun son (integer) bo'lishi kerak! Kiritilgan qiymat: '{GROUP_ID_STR}'"
    )
