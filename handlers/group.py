from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message

import config
import database
import keyboards

router = Router()
# Faqat maxsus guruhdan kelgan xabarlarni ushbu routerda ko'ramiz
router.message.filter(F.chat.type.in_({"group", "supergroup"}), F.chat.id == config.GROUP_ID)

@router.callback_query(F.message.chat.id == config.GROUP_ID, F.data.startswith("start_input:"))
async def process_start_input(callback: CallbackQuery, bot: Bot):
    """
    Mas'ul xodim '🟡 Kiritishni boshlash' tugmasini bosganda:
    - Mas'ul xodim uchun alohida Forum Topic ochiladi (agar yo'q bo'lsa).
    - Hujjatlar va ariza tafsilotlari o'sha mavzuga yo'naltiriladi.
    - General chatdagi xabar yangilanadi va tugma olib tashlanadi.
    """
    student_id = int(callback.data.split(":")[1])
    staff_id = callback.from_user.id
    staff_name = callback.from_user.full_name
    
    # 1. Arizani kiritishni boshlashni bazada belgilash (status = 'processing')
    success = database.start_processing_application(
        group_message_id=callback.message.message_id,
        staff_id=staff_id,
        staff_name=staff_name
    )
    
    if not success:
        # Agar ariza allaqachon boshqa xodim tomonidan olingan bo'lsa
        app = database.get_application_by_message_id(callback.message.message_id)
        assigned_name = app["assigned_staff_name"] if app else "boshqa xodim"
        await callback.answer(
            text=f"Bu ariza ustida boshqa xodim ({assigned_name}) ishlamoqda! ❌",
            show_alert=True
        )
        return

    # Bazadan arizani va uning fayllarini o'qiymiz
    app = database.get_application_by_message_id(callback.message.message_id)
    if not app:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return

    # 2. Mas'ul xodim uchun guruhda Forum Topic (Mavzu) yaratish yoki olish
    topic_id = database.get_staff_topic(staff_id)
    
    if not topic_id:
        try:
            # Yangi mavzu yaratish
            topic = await bot.create_forum_topic(
                chat_id=config.GROUP_ID,
                name=f"📁 {staff_name}"
            )
            topic_id = topic.message_thread_id
            database.save_staff_topic(
                staff_id=staff_id,
                message_thread_id=topic_id,
                staff_name=staff_name
            )
        except Exception as e:
            # Agar mavzu yaratib bo'lmasa (Supergrupa emas yoki botga ruxsat yo'q), fallback rejimiga o'tadi
            print(f"Forum mavzusi yaratishda xato: {e}. Fallback rejimga o'tilmoqda.")
            topic_id = None

    # 3. Agar mavzu muvaffaqiyatli aniqlansa/yaratilsa:
    if topic_id is not None:
        try:
            files = database.get_application_files(student_id)
            
            # Hujjatlarni mas'ulning shaxsiy mavzusiga yo'naltiramiz
            for file_info in files:
                file_id = file_info["file_id"]
                file_type = file_info["file_type"]
                caption = file_info.get("caption") or ""
                caption_text = f"📁 <b>O'quvchi:</b> {app['student_name']}\n📎 <b>Izoh:</b> {caption}".strip()
                
                if file_type == "photo":
                    sent_file = await bot.send_photo(
                        chat_id=config.GROUP_ID,
                        photo=file_id,
                        caption=caption_text,
                        message_thread_id=topic_id
                    )
                else: # document
                    sent_file = await bot.send_document(
                        chat_id=config.GROUP_ID,
                        document=file_id,
                        caption=caption_text,
                        message_thread_id=topic_id
                    )
                
                # Yangi mavzudagi xabarlar reply-larini ham bog'laymiz
                database.add_message_link(
                    group_message_id=sent_file.message_id,
                    student_chat_id=student_id
                )
                
            # Yangi mavzuda asosiy ariza tafsilotlarini yangi tugma bilan yuboramiz
            summary_text = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📥 <b>ARIZA (KO'RIB CHIQILMOQDA)</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 <b>O'quvchi:</b> <code>{app['student_name']}</code>\n"
                f"📞 <b>Telefon:</b> <code>{app['student_phone']}</code>\n\n"
                f"📌 <b>Status:</b> 🟡 <code>Kiritish boshlandi</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            topic_summary_msg = await bot.send_message(
                chat_id=config.GROUP_ID,
                text=summary_text,
                message_thread_id=topic_id,
                reply_markup=keyboards.get_finish_input_keyboard(student_id)
            )
            
            # Arizaning asosiy message_id sini yangi mavzudagi message_id ga o'zgartiramiz
            database.update_application_message_id(student_id, topic_summary_msg.message_id)
            
            # Yangi summary xabarni ham reply uchun bog'laymiz
            database.add_message_link(
                group_message_id=topic_summary_msg.message_id,
                student_chat_id=student_id
            )
            
            # General chatdagi dastlabki xabarni tahrirlab, yopamiz
            general_edit_text = (
                f"👨‍💻 <b>Mas'ul:</b> <code>{staff_name}</code> (O'z bo'limiga o'tkazdi)\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📥 <b>ARIZA TAFSILOTLARI</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>O'quvchi:</b> <code>{app['student_name']}</code>\n"
                f"📞 <b>Telefon:</b> <code>{app['student_phone']}</code>\n\n"
                "📌 <b>Status:</b> ➡️ <code>Bo'limga o'tkazildi</code>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await callback.message.edit_text(
                text=general_edit_text,
                reply_markup=None
            )
            
            await callback.answer(f"Ariza maxsus '{staff_name}' bo'limiga ko'chirildi! 📁")
            
        except Exception as e:
            print(f"Mavzuga ko'chirishda xatolik: {e}. Fallback ishga tushmoqda...")
            topic_id = None # Fallback rejimida davom etish
            
    # 4. Fallback rejimi (Mavzular ishlamasa, oldingi oddiy holatda davom etadi):
    if topic_id is None:
        new_text = (
            f"👨‍💻 <b>Mas'ul:</b> <code>{staff_name}</code> (Hozir kiritmoqda...)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 <b>YANGI ARIZA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> <code>{app['student_name']}</code>\n"
            f"📞 <b>Telefon:</b> <code>{app['student_phone']}</code>\n\n"
            f"📌 <b>Status:</b> 🟡 <code>Kiritish boshlandi</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await callback.message.edit_text(
            text=new_text,
            reply_markup=keyboards.get_finish_input_keyboard(student_id)
        )
        await callback.answer("Siz mas'ul etib belgilandingiz! 👍")

    # O'quvchini ham xabardor qilish
    try:
        await bot.send_message(
            chat_id=student_id,
            text=f"Sizning arizangiz ustida ish boshlandi. 👨‍💻\nMas'ul xodim: {staff_name}"
        )
    except Exception as e:
        print(f"O'quvchiga xabar yuborishda xatolik: {e}")

@router.callback_query(F.message.chat.id == config.GROUP_ID, F.data.startswith("finish_input:"))
async def process_finish_input(callback: CallbackQuery, bot: Bot):
    """Mas'ul xodim '🟢 Platformaga kiritildi' tugmasini bosganda."""
    student_id = int(callback.data.split(":")[1])
    staff_id = callback.from_user.id
    
    app = database.get_application_by_message_id(callback.message.message_id)
    if not app:
        await callback.answer("Ariza topilmadi!", show_alert=True)
        return
        
    # Tugmani faqat arizani kiritishni boshlagan mas'ul xodim bosa oladi
    if app["assigned_staff_id"] != staff_id:
        await callback.answer(
            text=f"Bu arizani faqat biriktirilgan mas'ul ({app['assigned_staff_name']}) yakunlay oladi! ❌",
            show_alert=True
        )
        return
        
    # Bazada arizani yakunlash
    success = database.finish_processing_application(callback.message.message_id)
    
    if success:
        # Guruhdagi xabarni yangilash (tugmalarni olib tashlash va muvaffaqiyatli deb belgilash)
        new_text = (
            f"✅ <b>Platformaga muvaffaqiyatli kiritildi!</b> (Mas'ul: <code>{app['assigned_staff_name']}</code>)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 <b>ARIZA YAKUNLANDI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> <code>{app['student_name']}</code>\n"
            f"📞 <b>Telefon:</b> <code>{app['student_phone']}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await callback.message.edit_text(
            text=new_text,
            reply_markup=None
        )
        await callback.answer("Ariza muvaffaqiyatli yopildi! ✅")
        
        # O'quvchini xabardor qilish
        try:
            await bot.send_message(
                chat_id=student_id,
                text="Xushxabar! 🎉\nSizning arizangiz ko'rib chiqildi va muvaffaqiyatli kiritildi! ✅"
            )
        except Exception as e:
            print(f"O'quvchiga yakuniy xabar yuborishda xatolik: {e}")
    else:
        await callback.answer("Xatolik yuz berdi. Arizani yakunlab bo'lmadi.", show_alert=True)

@router.message(F.reply_to_message)
async def process_group_reply(message: Message, bot: Bot):
    """
    Guruhda arizaga oid xabarlarga reply yozilganda, 
    ushbu xabarni o'quvchining shaxsiy botiga yetkazish.
    Mas'ulning shaxsiy akkaunti yashirin qoladi.
    """
    replied_msg = message.reply_to_message
    
    # Bazadan reply qilingan xabar kimga tegishli ekanligini izlaymiz
    link = database.get_message_link(replied_msg.message_id)
    if not link:
        # Agar reply qilingan xabar bizning arizalarimizga bog'lanmagan bo'lsa
        return
        
    student_chat_id = link["student_chat_id"]
    student_message_id = link["student_message_id"]
    
    try:
        sent_msg = None
        header_text = "💬 <b>Qabul komissiyasidan javob:</b>\n"
        
        # Matnli xabarni yuborish
        if message.text:
            sent_msg = await bot.send_message(
                chat_id=student_chat_id,
                text=f"{header_text}<blockquote>{message.text}</blockquote>",
                reply_to_message_id=student_message_id
            )
        # Rasmni yuborish
        elif message.photo:
            caption = message.caption or ""
            sent_msg = await bot.send_photo(
                chat_id=student_chat_id,
                photo=message.photo[-1].file_id,
                caption=f"{header_text}<blockquote>{caption}</blockquote>",
                reply_to_message_id=student_message_id
            )
        # Hujjatni yuborish
        elif message.document:
            caption = message.caption or ""
            sent_msg = await bot.send_document(
                chat_id=student_chat_id,
                document=message.document.file_id,
                caption=f"{header_text}<blockquote>{caption}</blockquote>",
                reply_to_message_id=student_message_id
            )
        else:
            # Boshqa turdagi xabarlar (audio, video) yo'naltirilmaydi
            return

        # Reply xabarlar zanjirining davomiyligini ta'minlash uchun
        if sent_msg:
            database.add_message_link(
                group_message_id=message.message_id,
                student_chat_id=student_chat_id,
                student_message_id=sent_msg.message_id
            )
            
    except Exception as e:
        print(f"Javobni o'quvchiga yuborishda xatolik: {e}")
        # Mas'ul xodimga xato haqida guruhda javob beramiz
        await message.reply(
            "❌ <b>Ushbu xabarni o'quvchiga yuborib bo'lmadi.</b>\n"
            "Sababi: O'quvchi botni bloklagan yoki o'chirib yuborgan bo'lishi mumkin."
        )
