# database.py - إدارة اتصال قاعدة البيانات

import os
import psycopg2
from psycopg2.extras import Json

# ================= الحصول على رابط قاعدة البيانات =================
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL غير موجود في متغيرات البيئة")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """إنشاء جدول المحادثات إذا لم يكن موجوداً"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def execute_query(query, params=None):
    """تنفيذ استعلام (INSERT, UPDATE, DELETE)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def fetch_all(query, params=None):
    """استرجاع جميع الصفوف من استعلام SELECT"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_one(query, params=None):
    """استرجاع صف واحد من استعلام SELECT"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
