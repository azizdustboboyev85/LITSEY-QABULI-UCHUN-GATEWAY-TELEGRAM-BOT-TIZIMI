import re
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, ContentType

import config
import database
import keyboards
from states import Registration

router = Router()
# Faqat shaxsiy chatdagi xabarlarni ushbu routerda ko'ramiz
router.message.filter(F.chat.type == "private")

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    """/start komandasi: O'quvchini ro'yxatdan o'tkazishni boshlash yoki uning holatini ko'rsatish."""
    await state.clear()
    
    student_id = message.from_user.id
    app = database.get_application_by_student(student_id)
    
    if app:
        status = app["status"]
        if status == "pending":
            await message.answer(
                "⏳ <b>Arizangiz qabul qilingan va navbatda turibdi.</b>\n\n"
                "Tez orada mas'ul xodimlarimiz uni ko'rib chiqishni boshlashadi. "
                "Agar qo'shimcha ma'lumot yubormoqchi bo'lsangiz, uni matn yoki fayl ko'rinishida shu yerga yuborishingiz mumkin."
            )
            return
        elif status == "processing":
            staff_name = app["assigned_staff_name"] or "Mas'ul xodim"
            await message.answer(
                "👨‍💻 <b>Sizning arizangiz ko'rib chiqilmoqda.</b>\n\n"
                f"• <b>Mas'ul xodim:</b> <code>{staff_name}</code>\n\n"
                "Agar biror savolingiz bo'lsa yoki qo'shimcha ma'lumot yubormoqchi bo'lsangiz, shu yerga yozishingiz mumkin."
            )
            return
        elif status == "completed":
            await message.answer(
                "✅ <b>Arizangiz muvaffaqiyatli qabul qilindi va platformaga kiritildi!</b>\n\n"
                "E'tiboringiz uchun rahmat!"
            )
            return

    # Yangi ariza boshlash
    await state.set_state(Registration.name)
    await message.answer(
        "👋 <b>Assalomu alaykum! Litsey qabul botiga xush kelibsiz.</b>\n\n"
        "Ushbu bot orqali hujjatlaringizni tez va xavfsiz tarzda qabul komissiyasiga topshirishingiz mumkin.\n\n"
        "📝 <b>Boshlash uchun to'liq ism-familiyangizni kiriting (F.I.SH.):</b>\n"
        "<i>Masalan: Asrorov Asror</i>"
    )

@router.message(StateFilter(Registration.name))
async def process_name(message: Message, state: FSMContext):
    """Ism-familiyani qabul qilish."""
    name = message.text.strip() if message.text else ""
    if len(name) < 3:
        await message.answer("❌ <b>Iltimos, ism-familiyangizni to'liqroq yozing:</b>")
        return
        
    await state.update_data(name=name)
    await state.set_state(Registration.phone)
    await message.answer(
        f"🤝 <b>Rahmat, {name}.</b>\n\n"
        "📞 <b>Endi telefon raqamingizni yuboring:</b>\n"
        "• Pastdagi tugmani bosish orqali raqamingizni avtomatik yuborishingiz mumkin.\n"
        "• Yoki raqamingizni qo'lda kiriting (masalan: <code>+998901234567</code>):",
        reply_markup=keyboards.get_phone_keyboard()
    )

@router.message(StateFilter(Registration.phone))
async def process_phone(message: Message, state: FSMContext):
    """Telefon raqamini qabul qilish."""
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        # Oddiy telefon raqami tekshiruvi (faqat raqamlar va + belgisi)
        text = message.text.strip().replace(" ", "")
        if re.match(r"^\+?[0-9]{9,15}$", text):
            phone = text
        else:
            await message.answer(
                "⚠️ <b>Telefon raqami formati noto'g'ri.</b>\n\n"
                "Iltimos, raqamni quyidagi tugma orqali yuboring "
                "yoki to'g'ri formatda kiriting (masalan: <code>+998901234567</code>):",
                reply_markup=keyboards.get_phone_keyboard()
            )
            return
    else:
        await message.answer("⚠️ <b>Iltimos, telefon raqamingizni matn ko'rinishida yozing yoki pastdagi tugmani bosing:</b>")
        return

    # Raqamni normallashtirish (+ belgisi bo'lsa yaxshi)
    if not phone.startswith("+"):
        phone = "+" + phone

    await state.update_data(phone=phone)
    await state.update_data(files=[])
    await state.set_state(Registration.documents)
    await message.answer(
        "📎 <b>Hujjatlarni yuklash bosqichi:</b>\n\n"
        "Kerakli hujjatlarni (pasport nusxasi, rasm, PDF va h.k.) bitta-bitta yuboring.\n\n"
        "✨ <b>Qoidalar:</b>\n"
        "• Rasmlar va PDF fayllar tiniq va o'qiladigan bo'lishi kerak.\n"
        "• Barcha hujjatlarni yuborib bo'lgach, pastdagi <b>'✅ Hujjatlarni yuborib bo'ldim'</b> tugmasini bosing.",
        reply_markup=keyboards.get_documents_done_keyboard()
    )

@router.message(StateFilter(Registration.documents), F.text == "✅ Hujjatlarni yuborib bo'ldim")
async def process_documents_done(message: Message, state: FSMContext, bot: Bot):
    """O'quvchi hujjatlarni yuborib bo'lganligini tasdiqlaganida arizani guruhga yo'naltirish."""
    data = await state.get_data()
    files = data.get("files", [])
    
    if not files:
        await message.answer("❌ <b>Iltimos, ariza topshirish uchun kamida bitta hujjat (rasm yoki PDF) yuboring.</b>")
        return
        
    student_id = message.from_user.id
    student_name = data["name"]
    student_phone = data["phone"]
    
    # Bazada ariza yaratish
    database.create_application(
        student_id=student_id,
        student_name=student_name,
        student_phone=student_phone
    )
    
    await message.answer(
        "⏳ <b>Arizangiz guruhga yuborilmoqda. Iltimos, kuting...</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Hujjatlarni guruhga yo'naltirish
    sent_media_count = 0
    for file_info in files:
        try:
            file_id = file_info["file_id"]
            file_type = file_info["type"]
            caption = file_info.get("caption") or ""
            
            # Guruhga yuborilayotgan hujjatga o'quvchi ismini eslatma sifatida yozib qo'yamiz
            caption_text = f"📁 <b>O'quvchi:</b> {student_name}\n📎 <b>Izoh:</b> {caption}".strip()
            
            # Arxiv paneli uchun bazada saqlab qolamiz
            database.add_application_file(
                student_id=student_id,
                file_id=file_id,
                file_type=file_type,
                caption=caption
            )
            
            if file_type == "photo":
                sent_msg = await bot.send_photo(
                    chat_id=config.GROUP_ID,
                    photo=file_id,
                    caption=caption_text
                )
            else: # document
                sent_msg = await bot.send_document(
                    chat_id=config.GROUP_ID,
                    document=file_id,
                    caption=caption_text
                )
                
            # Reply uchun xabarlar bog'lanmasini saqlab qo'yamiz
            database.add_message_link(
                group_message_id=sent_msg.message_id,
                student_chat_id=student_id,
                student_message_id=file_info.get("original_msg_id")
            )
            sent_media_count += 1
        except Exception as e:
            print(f"Fayl yuborishda xatolik: {e}")
            
    # Guruhga asosiy ariza xulosasini va inline tugmani yuborish
    summary_text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 <b>YANGI ARIZA KELIB TUSHDI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>O'quvchi:</b> <code>{student_name}</code>\n"
        f"📞 <b>Telefon:</b> <code>{student_phone}</code>\n"
        f"📊 <b>Hujjatlar:</b> <code>{sent_media_count} ta fayl</code>\n\n"
        "📌 <b>Status:</b> 🟡 <code>Kiritish kutilmoqda</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        summary_msg = await bot.send_message(
            chat_id=config.GROUP_ID,
            text=summary_text,
            reply_markup=keyboards.get_start_input_keyboard(student_id)
        )
        
        # Arizani guruh xabari ID-si bilan bog'laymiz
        database.update_application_message_id(student_id, summary_msg.message_id)
        
        # Ushbu xabarni ham reply uchun bog'laymiz
        database.add_message_link(
            group_message_id=summary_msg.message_id,
            student_chat_id=student_id
        )
        
        await message.answer(
            "🎉 <b>Arizangiz muvaffaqiyatli topshirildi!</b>\n\n"
            "Tez orada mas'ul xodimlarimiz hujjatlarni ko'rib chiqishadi va natijasi haqida sizga shu bot orqali xabar berishadi."
        )
    except Exception as e:
        await message.answer(
            "❌ <b>Arizani guruhga yuborishda muammo yuz berdi.</b>\n\n"
            "Iltimos, guruh sozlamalarini va guruh ID-si to'g'ri kiritilganini tekshiring."
        )
        print(f"Summary xabar yuborishda xatolik: {e}")
        
    await state.clear()

@router.message(StateFilter(Registration.documents))
async def process_documents(message: Message, state: FSMContext):
    """Hujjatlar yuklanishini nazorat qilish."""
    data = await state.get_data()
    files = data.get("files", [])
    
    file_id = None
    file_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        await message.answer(
            "⚠️ <b>Iltimos, faqat rasm yoki PDF/hujjat ko'rinishida yuboring.</b>\n"
            "Agar tugatgan bo'lsangiz, pastdagi tugmani bosing."
        )
        return
        
    files.append({
        "file_id": file_id,
        "type": file_type,
        "caption": message.caption,
        "original_msg_id": message.message_id
    })
    
    await state.update_data(files=files)
    await message.answer(
        f"✅ <b>Hujjat qabul qilindi.</b> (Jami: <code>{len(files)} ta</code>)\n"
        "Yana yuborishingiz mumkin. Tugatsangiz, pastdagi tugmani bosing."
    )

@router.message()
async def process_student_reply(message: Message, bot: Bot):
    """
    O'quvchi ro'yxatdan o'tib bo'lgach, botga yozgan qo'shimcha xabarlarini 
    guruhdagi o'sha o'quvchining arizasiga reply qilib yo'naltirish.
    """
    student_id = message.from_user.id
    app = database.get_application_by_student(student_id)
    
    if not app or not app["group_message_id"]:
        # Agar o'quvchi hali ro'yxatdan o'tmagan bo'lsa
        await message.answer("⚠️ <b>Iltimos, ariza topshirish uchun avval /start buyrug'ini bosing.</b>")
        return
        
    # Ariza guruhdagi qaysi xabarga biriktirilganini aniqlaymiz
    reply_to_id = app["group_message_id"]
    
    # Mas'ul xodim va uning Forum mavzusi (topic) ID-sini aniqlaymiz
    topic_id = None
    if app["assigned_staff_id"]:
        topic_id = database.get_staff_topic(app["assigned_staff_id"])
    
    try:
        # Matnli xabarni yo'naltirish
        if message.text:
            sent_msg = await bot.send_message(
                chat_id=config.GROUP_ID,
                text=f"💬 <b>O'quvchidan yangi xabar:</b>\n<blockquote>{message.text}</blockquote>",
                reply_to_message_id=reply_to_id,
                message_thread_id=topic_id
            )
        # Rasmni yo'naltirish
        elif message.photo:
            caption_text = f"💬 <b>O'quvchidan rasm/hujjat:</b>\n<blockquote>{message.caption or ''}</blockquote>"
            sent_msg = await bot.send_photo(
                chat_id=config.GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=caption_text,
                reply_to_message_id=reply_to_id,
                message_thread_id=topic_id
            )
        # Hujjatni yo'naltirish
        elif message.document:
            caption_text = f"💬 <b>O'quvchidan hujjat:</b>\n<blockquote>{message.caption or ''}</blockquote>"
            sent_msg = await bot.send_document(
                chat_id=config.GROUP_ID,
                document=message.document.file_id,
                caption=caption_text,
                reply_to_message_id=reply_to_id,
                message_thread_id=topic_id
            )
        else:
            await message.answer("❌ <b>Ushbu formatdagi xabar qo'llab-quvvatlanmaydi.</b>")
            return

        # Reply xabarlar zanjiri ishlashi uchun bazaga qo'shamiz
        database.add_message_link(
            group_message_id=sent_msg.message_id,
            student_chat_id=student_id,
            student_message_id=message.message_id
        )
        
        await message.answer("📨 <b>Xabaringiz qabul komissiyasiga yetkazildi.</b>")
        
    except Exception as e:
        print(f"Xabarni guruhga yuborishda xatolik: {e}")
        await message.answer("❌ <b>Xabaringizni yuborishda muammo yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.</b>")
