import urllib.request
import json
import sys

# Windows konsoli uchun UTF-8 ni yoqish
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BOT_TOKEN = "8963866357:AAGW4LZI1HRPPPqblPCUd07fZhPxDeGZHmU"
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

try:
    print("Telegramdan ma'lumotlar olinmoqda...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
    results = data.get("result", [])
    if not results:
        print("\nHech qanday yangi xabar topilmadi! (No updates found)")
        print("Iltimos, quyidagilarni bajaring:")
        print("1. Botni guruhga qo'shing.")
        print("2. Guruhga biror xabar yuboring (masalan: 'Salom' yoki '/test').")
        print("3. Keyin ushbu skriptni qaytadan ishga tushiring.")
    else:
        found_chats = {}
        for item in results:
            chat = None
            if "message" in item:
                chat = item["message"]["chat"]
            elif "my_chat_member" in item:
                chat = item["my_chat_member"]["chat"]
            elif "callback_query" in item:
                chat = item["callback_query"]["message"]["chat"]
                
            if chat:
                chat_id = chat["id"]
                chat_title = chat.get("title", chat.get("username", chat.get("first_name", "Nomalum")))
                chat_type = chat["type"]
                found_chats[chat_id] = (chat_title, chat_type)
                
        print("\nTopilgan chatlar va guruhlar:")
        print("-" * 60)
        for cid, (title, ctype) in found_chats.items():
            print(f"Nomi: {title} | Turi: {ctype} | ID-si: {cid}")
        print("-" * 60)
        print("\nAgar o'z guruhingizni ko'rgan bo'lsangiz, uning ID-sini nusxalab .env faylidagi GROUP_ID o'rniga qo'ying.")
except Exception as e:
    print(f"Xatolik yuz berdi: {e}")
