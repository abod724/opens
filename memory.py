# ذاكرة مؤقتة لتخزين آخر 10 محادثات لكل جلسة (اختياري)
from collections import deque

# قاموس يحمل سجل المحادثات لكل مستخدم (حسب session)
session_memory = {}

def get_memory(session_id, limit=10):
    """استرجاع آخر limit محادثة من الذاكرة المؤقتة"""
    if session_id not in session_memory:
        session_memory[session_id] = deque(maxlen=limit)
    return list(session_memory[session_id])

def add_to_memory(session_id, user_msg, bot_msg):
    """إضافة محادثة جديدة إلى الذاكرة المؤقتة"""
    if session_id not in session_memory:
        session_memory[session_id] = deque(maxlen=10)
    session_memory[session_id].append({'user': user_msg, 'bot': bot_msg})
