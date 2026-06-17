import os
import sqlite3
from typing import Dict, Any, Optional

# PostgreSQL uchun drayverni yuklash (agar kerak bo'lsa)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DB_PATH = "qabul_bot.db"
DATABASE_URL = os.getenv("DATABASE_URL")

# Agar DATABASE_URL mavjud bo'lsa va drayver yuklangan bo'lsa, Postgres ishlatiladi
IS_POSTGRES = DATABASE_URL is not None and HAS_POSTGRES

def get_connection():
    """Ma'lumotlar bazasi turiga qarab ulanish hosil qilish."""
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Ma'lumotlar bazasi jadvallarini yaratish (PostgreSQL yoki SQLite)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            # PostgreSQL sxemasi (Telegram ID-lari uchun BIGINT ishlatiladi)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    student_id BIGINT PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    student_phone TEXT NOT NULL,
                    group_message_id BIGINT UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    assigned_staff_id BIGINT,
                    assigned_staff_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_links (
                    group_message_id BIGINT PRIMARY KEY,
                    student_chat_id BIGINT NOT NULL,
                    student_message_id BIGINT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_files (
                    id SERIAL PRIMARY KEY,
                    student_id BIGINT NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    caption TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff_topics (
                    staff_id BIGINT PRIMARY KEY,
                    message_thread_id BIGINT NOT NULL,
                    staff_name TEXT NOT NULL
                )
            """)
        else:
            # SQLite sxemasi
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    student_id INTEGER PRIMARY KEY,
                    student_name TEXT NOT NULL,
                    student_phone TEXT NOT NULL,
                    group_message_id INTEGER UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    assigned_staff_id INTEGER,
                    assigned_staff_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_links (
                    group_message_id INTEGER PRIMARY KEY,
                    student_chat_id INTEGER NOT NULL,
                    student_message_id INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS application_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    caption TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staff_topics (
                    staff_id INTEGER PRIMARY KEY,
                    message_thread_id INTEGER NOT NULL,
                    staff_name TEXT NOT NULL
                )
            """)
        conn.commit()
        cursor.close()

def create_application(student_id: int, student_name: str, student_phone: str) -> None:
    """Yangi ariza yaratish (eski ariza va hujjatlarni tozalaydi)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute("DELETE FROM application_files WHERE student_id = %s", (student_id,))
            cursor.execute(
                """
                INSERT INTO applications (student_id, student_name, student_phone, status, group_message_id, assigned_staff_id, assigned_staff_name)
                VALUES (%s, %s, %s, 'pending', NULL, NULL, NULL)
                ON CONFLICT (student_id) DO UPDATE SET
                    student_name = EXCLUDED.student_name,
                    student_phone = EXCLUDED.student_phone,
                    status = 'pending',
                    group_message_id = NULL,
                    assigned_staff_id = NULL,
                    assigned_staff_name = NULL
                """,
                (student_id, student_name, student_phone)
            )
        else:
            cursor.execute("DELETE FROM application_files WHERE student_id = ?", (student_id,))
            cursor.execute(
                """
                INSERT OR REPLACE INTO applications 
                (student_id, student_name, student_phone, status, group_message_id, assigned_staff_id, assigned_staff_name)
                VALUES (?, ?, ?, 'pending', NULL, NULL, NULL)
                """,
                (student_id, student_name, student_phone)
            )
        conn.commit()
        cursor.close()

def update_application_message_id(student_id: int, group_message_id: int) -> None:
    """Arizaning guruhdagi summary xabar ID-sini saqlash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute(
                "UPDATE applications SET group_message_id = %s WHERE student_id = %s",
                (group_message_id, student_id)
            )
        else:
            cursor.execute(
                "UPDATE applications SET group_message_id = ? WHERE student_id = ?",
                (group_message_id, student_id)
            )
        conn.commit()
        cursor.close()

def get_application_by_student(student_id: int) -> Optional[Dict[str, Any]]:
    """O'quvchi ID-si orqali arizani olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM applications WHERE student_id = %s", (student_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

def get_application_by_message_id(group_message_id: int) -> Optional[Dict[str, Any]]:
    """Guruhdagi xabar ID-si orqali arizani olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM applications WHERE group_message_id = %s", (group_message_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

def start_processing_application(group_message_id: int, staff_id: int, staff_name: str) -> bool:
    """
    Arizani kiritishni boshlash. Agar ariza hali hech kim tomonidan olinmagan bo'lsa (status='pending'),
    uni o'sha mas'ul xodimga biriktiradi va True qaytaradi. Aks holda False qaytaradi.
    """
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT status, assigned_staff_name FROM applications WHERE group_message_id = %s",
                (group_message_id,)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT status, assigned_staff_name FROM applications WHERE group_message_id = ?",
                (group_message_id,)
            )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return False
            
        if row["status"] != "pending":
            cursor.close()
            return False
            
        # Biriktirish
        if IS_POSTGRES:
            cursor.execute(
                """
                UPDATE applications 
                SET status = 'processing', assigned_staff_id = %s, assigned_staff_name = %s
                WHERE group_message_id = %s
                """,
                (staff_id, staff_name, group_message_id)
            )
        else:
            cursor.execute(
                """
                UPDATE applications 
                SET status = 'processing', assigned_staff_id = ?, assigned_staff_name = ?
                WHERE group_message_id = ?
                """,
                (staff_id, staff_name, group_message_id)
            )
        conn.commit()
        cursor.close()
        return True

def finish_processing_application(group_message_id: int) -> bool:
    """Arizani kiritilgan deb belgilash."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT status FROM applications WHERE group_message_id = %s", (group_message_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM applications WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        if not row or row["status"] != "processing":
            cursor.close()
            return False
            
        if IS_POSTGRES:
            cursor.execute(
                "UPDATE applications SET status = 'completed' WHERE group_message_id = %s",
                (group_message_id,)
            )
        else:
            cursor.execute(
                "UPDATE applications SET status = 'completed' WHERE group_message_id = ?",
                (group_message_id,)
            )
        conn.commit()
        cursor.close()
        return True

def add_message_link(group_message_id: int, student_chat_id: int, student_message_id: Optional[int] = None) -> None:
    """Guruhdagi xabar ID-sini o'quvchining chat ID-si va xabar ID-siga bog'lash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute(
                """
                INSERT INTO message_links (group_message_id, student_chat_id, student_message_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (group_message_id) DO UPDATE SET
                    student_chat_id = EXCLUDED.student_chat_id,
                    student_message_id = EXCLUDED.student_message_id
                """,
                (group_message_id, student_chat_id, student_message_id)
            )
        else:
            cursor.execute(
                """
                INSERT OR REPLACE INTO message_links (group_message_id, student_chat_id, student_message_id)
                VALUES (?, ?, ?)
                """,
                (group_message_id, student_chat_id, student_message_id)
            )
        conn.commit()
        cursor.close()

def get_message_link(group_message_id: int) -> Optional[Dict[str, Any]]:
    """Guruhdagi xabar ID-si orqali bog'langan o'quvchi ma'lumotlarini olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM message_links WHERE group_message_id = %s", (group_message_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM message_links WHERE group_message_id = ?", (group_message_id,))
        row = cursor.fetchone()
        cursor.close()
        return dict(row) if row else None

# --- Yangi Arxiv va Panel uchun zarur bo'lgan funksiyalar ---

def add_application_file(student_id: int, file_id: str, file_type: str, caption: Optional[str] = None) -> None:
    """O'quvchining hujjatlarini saqlash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute(
                """
                INSERT INTO application_files (student_id, file_id, file_type, caption)
                VALUES (%s, %s, %s, %s)
                """,
                (student_id, file_id, file_type, caption)
            )
        else:
            cursor.execute(
                """
                INSERT INTO application_files (student_id, file_id, file_type, caption)
                VALUES (?, ?, ?, ?)
                """,
                (student_id, file_id, file_type, caption)
            )
        conn.commit()
        cursor.close()

def get_application_files(student_id: int) -> list:
    """O'quvchining barcha hujjatlarini olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT file_id, file_type, caption FROM application_files WHERE student_id = %s",
                (student_id,)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_id, file_type, caption FROM application_files WHERE student_id = ?",
                (student_id,)
            )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

def get_processed_staff_members() -> list:
    """Arizalarni qabul qilgan yoki hozirda ishlayotgan barcha mas'ul xodimlarni olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT assigned_staff_id, assigned_staff_name 
            FROM applications 
            WHERE assigned_staff_id IS NOT NULL AND assigned_staff_name IS NOT NULL
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

def get_applications_by_staff(staff_id: int) -> list:
    """Ma'lum bir mas'ul xodim tomonidan qabul qilingan barcha arizalarni olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT student_id, student_name, student_phone, status 
                FROM applications 
                WHERE assigned_staff_id = %s 
                ORDER BY created_at DESC
                """,
                (staff_id,)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT student_id, student_name, student_phone, status 
                FROM applications 
                WHERE assigned_staff_id = ? 
                ORDER BY created_at DESC
                """,
                (staff_id,)
            )
        rows = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in rows]

def get_staff_topic(staff_id: int) -> Optional[int]:
    """Mas'ul xodimning guruhdagi mavzu ID-sini (message_thread_id) olish."""
    with get_connection() as conn:
        if IS_POSTGRES:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT message_thread_id FROM staff_topics WHERE staff_id = %s", (staff_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT message_thread_id FROM staff_topics WHERE staff_id = ?", (staff_id,))
        row = cursor.fetchone()
        cursor.close()
        return row["message_thread_id"] if row else None

def save_staff_topic(staff_id: int, message_thread_id: int, staff_name: str) -> None:
    """Mas'ul xodimning guruhdagi mavzu ID-sini saqlash."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute(
                """
                INSERT INTO staff_topics (staff_id, message_thread_id, staff_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (staff_id) DO UPDATE SET
                    message_thread_id = EXCLUDED.message_thread_id,
                    staff_name = EXCLUDED.staff_name
                """,
                (staff_id, message_thread_id, staff_name)
            )
        else:
            cursor.execute(
                """
                INSERT OR REPLACE INTO staff_topics (staff_id, message_thread_id, staff_name)
                VALUES (?, ?, ?)
                """,
                (staff_id, message_thread_id, staff_name)
            )
        conn.commit()
        cursor.close()
