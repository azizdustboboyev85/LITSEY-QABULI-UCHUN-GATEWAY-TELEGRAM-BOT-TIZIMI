import sqlite3
from typing import Dict, Any, Optional

DB_PATH = "qabul_bot.db"

def get_connection():
    """Ma'lumotlar bazasiga ulanish yaratish va row_factory ni sqlite3.Row ga sozlash."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish."""
    with get_connection() as conn:
        # applications: O'quvchi arizalarini saqlash jadvali
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                student_id INTEGER PRIMARY KEY,
                student_name TEXT NOT NULL,
                student_phone TEXT NOT NULL,
                group_message_id INTEGER UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed
                assigned_staff_id INTEGER,
                assigned_staff_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # message_links: Guruh xabarlari bilan o'quvchi chatini bog'lash (reply logikasi uchun)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_links (
                group_message_id INTEGER PRIMARY KEY,
                student_chat_id INTEGER NOT NULL,
                student_message_id INTEGER
            )
        """)

        # application_files: O'quvchi yuborgan barcha hujjatlarni panelda arxiv ko'rish uchun saqlash
        conn.execute("""
            CREATE TABLE IF NOT EXISTS application_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL, -- photo, document
                caption TEXT
            )
        """)

        # staff_topics: Mas'ullar nomi bilan ochilgan guruh mavzulari (topics) bog'lanmasi
        conn.execute("""
            CREATE TABLE IF NOT EXISTS staff_topics (
                staff_id INTEGER PRIMARY KEY,
                message_thread_id INTEGER NOT NULL,
                staff_name TEXT NOT NULL
            )
        """)
        conn.commit()

def create_application(student_id: int, student_name: str, student_phone: str) -> None:
    """Yangi ariza yaratish (eski ariza va hujjatlarni tozalaydi)."""
    with get_connection() as conn:
        # O'quvchining eski hujjatlarini o'chirib tashlaymiz
        conn.execute("DELETE FROM application_files WHERE student_id = ?", (student_id,))
        
        # Arizani yaratamiz/yangilaymiz
        conn.execute(
            """
            INSERT OR REPLACE INTO applications 
            (student_id, student_name, student_phone, status, group_message_id, assigned_staff_id, assigned_staff_name)
            VALUES (?, ?, ?, 'pending', NULL, NULL, NULL)
            """,
            (student_id, student_name, student_phone)
        )
        conn.commit()

def update_application_message_id(student_id: int, group_message_id: int) -> None:
    """Arizaning guruhdagi summary xabar ID-sini saqlash."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE applications SET group_message_id = ? WHERE student_id = ?",
            (group_message_id, student_id)
        )
        conn.commit()

def get_application_by_student(student_id: int) -> Optional[Dict[str, Any]]:
    """O'quvchi ID-si orqali arizani olish."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM applications WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_application_by_message_id(group_message_id: int) -> Optional[Dict[str, Any]]:
    """Guruhdagi xabar ID-si orqali arizani olish."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM applications WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def start_processing_application(group_message_id: int, staff_id: int, staff_name: str) -> bool:
    """
    Arizani kiritishni boshlash. Agar ariza hali hech kim tomonidan olinmagan bo'lsa (status='pending'),
    uni o'sha mas'ul xodimga biriktiradi va True qaytaradi. Aks holda False qaytaradi.
    """
    with get_connection() as conn:
        # Oldin statusni tekshiramiz
        cursor = conn.execute(
            "SELECT status, assigned_staff_name FROM applications WHERE group_message_id = ?",
            (group_message_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False
            
        if row["status"] != "pending":
            return False
            
        # Biriktirish
        conn.execute(
            """
            UPDATE applications 
            SET status = 'processing', assigned_staff_id = ?, assigned_staff_name = ?
            WHERE group_message_id = ?
            """,
            (staff_id, staff_name, group_message_id)
        )
        conn.commit()
        return True

def finish_processing_application(group_message_id: int) -> bool:
    """Arizani kiritilgan deb belgilash."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT status FROM applications WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        if not row or row["status"] != "processing":
            return False
            
        conn.execute(
            "UPDATE applications SET status = 'completed' WHERE group_message_id = ?",
            (group_message_id,)
        )
        conn.commit()
        return True

def add_message_link(group_message_id: int, student_chat_id: int, student_message_id: Optional[int] = None) -> None:
    """Guruhdagi xabar ID-sini o'quvchining chat ID-si va xabar ID-siga bog'lash."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO message_links (group_message_id, student_chat_id, student_message_id)
            VALUES (?, ?, ?)
            """,
            (group_message_id, student_chat_id, student_message_id)
        )
        conn.commit()

def get_message_link(group_message_id: int) -> Optional[Dict[str, Any]]:
    """Guruhdagi xabar ID-si orqali bog'langan o'quvchi ma'lumotlarini olish."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM message_links WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

# --- Yangi Arxiv va Panel uchun zarur bo'lgan funksiyalar ---

def add_application_file(student_id: int, file_id: str, file_type: str, caption: Optional[str] = None) -> None:
    """O'quvchining hujjatlarini saqlash."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO application_files (student_id, file_id, file_type, caption)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, file_id, file_type, caption)
        )
        conn.commit()

def get_application_files(student_id: int) -> list:
    """O'quvchining barcha hujjatlarini olish."""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT file_id, file_type, caption FROM application_files WHERE student_id = ?",
            (student_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_processed_staff_members() -> list:
    """Arizalarni qabul qilgan yoki hozirda ishlayotgan barcha mas'ul xodimlarni olish."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT DISTINCT assigned_staff_id, assigned_staff_name 
            FROM applications 
            WHERE assigned_staff_id IS NOT NULL AND assigned_staff_name IS NOT NULL
            """
        )
        return [dict(row) for row in cursor.fetchall()]

def get_applications_by_staff(staff_id: int) -> list:
    """Ma'lum bir mas'ul xodim tomonidan qabul qilingan barcha arizalarni olish."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT student_id, student_name, student_phone, status 
            FROM applications 
            WHERE assigned_staff_id = ? 
            ORDER BY created_at DESC
            """,
            (staff_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_staff_topic(staff_id: int) -> Optional[int]:
    """Mas'ul xodimning guruhdagi mavzu ID-sini (message_thread_id) olish."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT message_thread_id FROM staff_topics WHERE staff_id = ?", (staff_id,))
        row = cursor.fetchone()
        return row["message_thread_id"] if row else None

def save_staff_topic(staff_id: int, message_thread_id: int, staff_name: str) -> None:
    """Mas'ul xodimning guruhdagi mavzu ID-sini saqlash."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO staff_topics (staff_id, message_thread_id, staff_name)
            VALUES (?, ?, ?)
            """,
            (staff_id, message_thread_id, staff_name)
        )
        conn.commit()
