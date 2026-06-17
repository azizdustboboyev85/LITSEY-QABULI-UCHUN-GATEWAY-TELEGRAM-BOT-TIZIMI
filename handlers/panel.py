from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import config
import database
import keyboards

router = Router()
# Faqat shaxsiy chatdagi xabarlarni ushbu routerda ko'ramiz
router.message.filter(F.chat.type == "private")

async def is_staff(user_id: int, bot: Bot) -> bool:
    """Foydalanuvchining guruhga a'zo yoki mas'ulligini tekshirish."""
    try:
        member = await bot.get_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
        # creator, administrator va member statusiga ega bo'lganlar ruxsat etiladi
        return member.status in ("creator", "administrator", "member")
    except Exception as e:
        print(f"Mas'ul a'zoligini tekshirishda xatolik: {e}")
        return False

@router.message(Command("panel"))
async def open_panel(message: Message, bot: Bot):
    """Mas'ullar uchun shaxsiy papkalar panelini ochish."""
    if not await is_staff(message.from_user.id, bot):
        await message.answer("❌ <b>Kechirasiz, ushbu panelga faqat qabul komissiyasi a'zolari kira oladi!</b>")
        return

    staff_members = database.get_processed_staff_members()
    
    if not staff_members:
        await message.answer(
            "📂 <b>Mas'ullar Hujjatlar Arxiv Paneli</b>\n\n"
            "Hozircha tizimda kiritilgan arizalar va mas'ul biriktirilgan hujjatlar mavjud emas. 📭"
        )
        return

    text = (
        "📂 <b>Mas'ullar Hujjatlar Arxiv Paneli</b>\n\n"
        "Quyida har bir mas'ul xodim tomonidan qabul qilingan va platformaga kiritilgan arizalar jamlangan.\n\n"
        "Kerakli mas'ulning shaxsiy papkasini tanlang:"
    )
    
    await message.answer(
        text=text,
        reply_markup=keyboards.get_staff_list_keyboard(staff_members)
    )

@router.callback_query(F.data == "panel:main")
async def process_panel_main(callback: CallbackQuery, bot: Bot):
    """Bosh panel sahifasiga qaytish."""
    if not await is_staff(callback.from_user.id, bot):
        await callback.answer("❌ Ruxsat berilmadi!", show_alert=True)
        return

    staff_members = database.get_processed_staff_members()
    
    if not staff_members:
        await callback.message.edit_text(
            text="Hozircha tizimda hech qanday arizalar mavjud emas. 📭",
            reply_markup=None
        )
        return

    text = (
        "📂 <b>Mas'ullar Hujjatlar Arxiv Paneli</b>\n\n"
        "Quyida har bir mas'ul xodim tomonidan qabul qilingan va platformaga kiritilgan arizalar jamlangan.\n\n"
        "Kerakli mas'ulning shaxsiy papkasini tanlang:"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboards.get_staff_list_keyboard(staff_members)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("panel:staff:"))
async def process_panel_staff(callback: CallbackQuery, bot: Bot):
    """Ma'lum bir mas'ulning arizalar ro'yxatini ko'rish."""
    if not await is_staff(callback.from_user.id, bot):
        await callback.answer("❌ Ruxsat berilmadi!", show_alert=True)
        return

    staff_id = int(callback.data.split(":")[2])
    
    apps = database.get_applications_by_staff(staff_id)
    
    # Mas'ul ismini olish (tizimdagi birinchi arizadan yoki bazadan)
    staff_name = "Noma'lum"
    if apps:
        app_details = database.get_application_by_student(apps[0]["student_id"])
        if app_details:
            staff_name = app_details["assigned_staff_name"]

    if not apps:
        await callback.message.edit_text(
            text="📁 Ushbu mas'ul xodimda hali kiritilgan arizalar mavjud emas.",
            reply_markup=keyboards.get_staff_apps_keyboard([])
        )
        return

    text = (
        f"📁 <b>Mas'ul xodim:</b> <code>{staff_name}</code>\n"
        f"📊 <b>Kiritilgan arizalar:</b> <code>{len(apps)} ta</code>\n\n"
        "Quyida ushbu xodim tomonidan kiritilgan o'quvchilar ro'yxati keltirilgan. "
        "Batafsil ma'lumot va hujjatlar bilan tanishish uchun o'quvchini tanlang:"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboards.get_staff_apps_keyboard(apps)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("panel:app:"))
async def process_panel_app(callback: CallbackQuery, bot: Bot):
    """Ariza tafsilotlarini ko'rish."""
    if not await is_staff(callback.from_user.id, bot):
        await callback.answer("❌ Ruxsat berilmadi!", show_alert=True)
        return

    student_id = int(callback.data.split(":")[2])
    app = database.get_application_by_student(student_id)
    
    if not app:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return

    status_str = "Platformaga kiritildi ✅" if app["status"] == "completed" else "Kiritilmoqda (Jarayonda) 🟡"
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>O'quvchi:</b> <code>{app['student_name']}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📞 <b>Telefon:</b> <code>{app['student_phone']}</code>\n"
        f"📊 <b>Holati:</b> <code>{status_str}</code>\n"
        f"👨‍💻 <b>Mas'ul:</b> <code>{app['assigned_staff_name']}</code>\n"
        f"📅 <b>Qabul qilingan vaqt:</b> <i>{app['created_at']}</i>\n\n"
        "O'quvchining hujjatlarini shaxsiy chatingizga yuklab olish uchun pastdagi tugmani bosing."
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboards.get_app_details_keyboard(student_id, app["assigned_staff_id"])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("panel:files:"))
async def process_panel_files(callback: CallbackQuery, bot: Bot):
    """O'quvchining barcha fayllarini mas'ulning shaxsiy chatiga jo'natish."""
    if not await is_staff(callback.from_user.id, bot):
        await callback.answer("❌ Ruxsat berilmadi!", show_alert=True)
        return

    student_id = int(callback.data.split(":")[2])
    app = database.get_application_by_student(student_id)
    files = database.get_application_files(student_id)
    
    if not app:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return

    if not files:
        await callback.answer("Ushbu o'quvchiga tegishli hujjatlar topilmadi!", show_alert=True)
        return

    await callback.answer("Hujjatlar yuborilmoqda... 📥")
    
    # Avval mas'ulga kimning hujjatlarini yuborayotganimizni bildiramiz
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=f"📂 <b>{app['student_name']}</b>ga tegishli barcha hujjatlar yuklanmoqda:"
    )

    sent_count = 0
    for file_info in files:
        try:
            file_id = file_info["file_id"]
            file_type = file_info["file_type"]
            caption = file_info.get("caption") or ""
            
            caption_text = f"📄 {app['student_name']} hujjati\n{caption}".strip()
            
            if file_type == "photo":
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=file_id,
                    caption=caption_text
                )
            else: # document
                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file_id,
                    caption=caption_text
                )
            sent_count += 1
        except Exception as e:
            print(f"Faylni shaxsiy chatga yuborishda xato: {e}")
            
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=f"✅ Jami <code>{sent_count} ta</code> hujjat muvaffaqiyatli yuborildi."
    )
