from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamini yuborish uchun reply tugma."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamini yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_documents_done_keyboard() -> ReplyKeyboardMarkup:
    """Hujjatlar yuklashni yakunlash tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Hujjatlarni yuborib bo'ldim")]
        ],
        resize_keyboard=True
    )

def get_start_input_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """Arizani guruhga birinchi marta yuborganda chiqadigan inline tugma."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟡 Kiritishni boshlash",
                    callback_data=f"start_input:{student_id}"
                )
            ]
        ]
    )

def get_finish_input_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """Mas'ul xodim arizani kiritayotgan paytda chiqadigan inline tugma."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Platformaga kiritildi",
                    callback_data=f"finish_input:{student_id}"
                )
            ]
        ]
    )

def get_staff_list_keyboard(staff_members: list) -> InlineKeyboardMarkup:
    """Arizalarni kiritgan mas'ullar ro'yxati tugmalari."""
    keyboard = []
    for member in staff_members:
        name = member["assigned_staff_name"]
        staff_id = member["assigned_staff_id"]
        keyboard.append([
            InlineKeyboardButton(
                text=f"📁 {name}",
                callback_data=f"panel:staff:{staff_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_staff_apps_keyboard(applications: list) -> InlineKeyboardMarkup:
    """Mas'ul qabul qilgan arizalar ro'yxati."""
    keyboard = []
    for app in applications:
        name = app["student_name"]
        student_id = app["student_id"]
        status_icon = "✅" if app["status"] == "completed" else "🟡"
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {name} {status_icon}",
                callback_data=f"panel:app:{student_id}"
            )
        ])
    # Ortga tugmasi
    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Mas'ullar ro'yxatiga",
            callback_data="panel:main"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_app_details_keyboard(student_id: int, staff_id: int) -> InlineKeyboardMarkup:
    """Ariza tafsilotlari ko'rinishidagi boshqaruv tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Hujjatlarni yuklash (Download)",
                    callback_data=f"panel:files:{student_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Arizalar ro'yxatiga",
                    callback_data=f"panel:staff:{staff_id}"
                )
            ]
        ]
    )
