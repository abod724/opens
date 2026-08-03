import os
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for
from dotenv import load_dotenv
from openai import OpenAI

# ========== 1. تحميل المفتاح ==========
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    # ضع مفتاحك هنا مباشرة إن لم يكن لديك ملف .env
    api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # غير هذا بالمفتاح الحقيقي

client = OpenAI(api_key=api_key)

# ========== 2. قاعدة البيانات (SQLite) ==========
DB_PATH = "conversations.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')
init_db()

def create_conversation(title):
    now = datetime.now().isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
            (title, now, now)
        )
        return cur.lastrowid

def save_message(conv_id, role, content):
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, now)
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id)
        )

def get_all_conversations():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

def get_messages(conv_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conv_id,)
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

def delete_conversation(conv_id):
    with get_db() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))

# ========== 3. الذاكرة المؤقتة (لكل محادثة) ==========
active_memory = {}

class Memory:
    def __init__(self, max_history=50):
        self.messages = []
        self.max_history = max_history

    def add(self, role, content):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get(self):
        return self.messages

    def load(self, msgs):
        self.messages = msgs[-self.max_history:] if msgs else []

def get_memory(conv_id):
    if conv_id not in active_memory:
        mem = Memory()
        mem.load(get_messages(conv_id))
        active_memory[conv_id] = mem
    return active_memory[conv_id]

# ========== 4. تطبيق Flask ==========
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== 5. واجهات HTML (مدمجة) ==========
INDEX_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>محادثاتي</title>
    <style>
        body { font-family: 'Segoe UI', Arial; padding: 20px; background: #f0f2f5; margin:0; }
        .container { max-width: 800px; margin: auto; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { color: #1a1a2e; }
        .conv-list { margin-top: 20px; }
        .conv-item { padding: 15px; border-bottom: 1px solid #eee; cursor: pointer; transition: 0.2s; border-radius: 8px; }
        .conv-item:hover { background: #f8f9fa; transform: translateX(5px); }
        .conv-title { font-weight: bold; font-size: 18px; color: #16213e; }
        .conv-date { font-size: 13px; color: #6c757d; }
        .new { display: flex; gap: 10px; margin-bottom: 25px; }
        .new input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; }
        .new button { padding: 10px 24px; background: #0d6efd; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }
        .new button:hover { background: #0b5ed7; }
        .no-conv { color: #6c757d; text-align: center; padding: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📂 محادثاتي</h1>
        <div class="new">
            <form method="POST" action="/new" style="display: flex; width: 100%; gap: 10px;">
                <input type="text" name="title" placeholder="عنوان المحادثة الجديدة" required>
                <button type="submit">➕ جديد</button>
            </form>
        </div>
        <div class="conv-list">
            {% if conversations %}
                {% for conv in conversations %}
                <div class="conv-item" onclick="window.location='/chat/{{ conv.id }}'">
                    <div class="conv-title">{{ conv.title }}</div>
                    <div class="conv-date">{{ conv.updated_at[:16] }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-conv">لا توجد محادثات سابقة، ابدأ محادثة جديدة!</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

CHAT_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>المحادثة</title>
    <style>
        body { font-family: 'Segoe UI', Arial; padding: 20px; background: #f0f2f5; margin:0; }
        .container { max-width: 1100px; margin: auto; display: flex; gap: 25px; align-items: flex-start; }
        .sidebar { width: 280px; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .sidebar h3 { margin-top: 0; color: #1a1a2e; }
        .sidebar a { display: block; padding: 12px; margin: 6px 0; background: #f8f9fa; border-radius: 8px; text-decoration: none; color: #16213e; transition: 0.2s; }
        .sidebar a:hover { background: #e9ecef; }
        .sidebar .active { background: #d4edda; font-weight: bold; }
        .sidebar .new-form { display: flex; flex-direction: column; gap: 8px; margin: 15px 0; }
        .sidebar .new-form input { padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
        .sidebar .new-form button { padding: 10px; background: #0d6efd; color: white; border: none; border-radius: 8px; cursor: pointer; }
        .sidebar .new-form button:hover { background: #0b5ed7; }
        .delete-btn { background: #dc3545; color: white; border: none; padding: 10px; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 10px; }
        .delete-btn:hover { background: #c82333; }
        .chat-area { flex: 1; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .messages { height: 450px; overflow-y: auto; border: 1px solid #e9ecef; padding: 15px; border-radius: 12px; background: #fafafa; margin-bottom: 20px; }
        .msg { margin: 10px 0; padding: 12px 18px; border-radius: 18px; max-width: 80%; word-wrap: break-word; }
        .user { background: #0d6efd; color: white; align-self: flex-end; margin-right: auto; }
        .assistant { background: #e9ecef; color: #212529; align-self: flex-start; }
        .form { display: flex; gap: 12px; }
        .form input { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 30px; font-size: 16px; }
        .form button { padding: 12px 28px; background: #28a745; color: white; border: none; border-radius: 30px; cursor: pointer; font-size: 16px; }
        .form button:hover { background: #218838; }
        h2 { color: #1a1a2e; margin-top: 0; }
        .back-link { display: inline-block; margin-bottom: 15px; color: #0d6efd; text-decoration: none; }
        .back-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h3>📂 المحادثات</h3>
            <a href="/">🏠 الرئيسية</a>
            <form method="POST" action="/new" class="new-form">
                <input type="text" name="title" placeholder="عنوان جديد" required>
                <button type="submit">➕ إضافة</button>
            </form>
            {% for conv in conversations %}
                <a href="/chat/{{ conv.id }}" class="{% if conv.id == current_conv %}active{% endif %}">
                    {{ conv.title }}
                </a>
            {% endfor %}
            <form method="POST" action="/delete/{{ current_conv }}" onsubmit="return confirm('حذف المحادثة؟')">
                <button type="submit" class="delete-btn">🗑️ حذف هذه المحادثة</button>
            </form>
        </div>
        <div class="chat-area">
            <h2>💬 المحادثة</h2>
            <div class="messages">
                {% for msg in messages %}
                    <div class="msg {{ msg.role }}">{{ msg.content }}</div>
                {% endfor %}
            </div>
            <form method="POST" action="/send" class="form">
                <input type="hidden" name="conv_id" value="{{ current_conv }}">
                <input type="text" name="message" placeholder="اكتب رسالتك..." required autofocus>
                <button type="submit">إرسال</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# ========== 6. مسارات Flask ==========
@app.route("/")
def index():
    return render_template_string(INDEX_HTML, conversations=get_all_conversations())

@app.route("/chat/<int:conv_id>")
def chat(conv_id):
    return render_template_string(CHAT_HTML,
        conversations=get_all_conversations(),
        current_conv=conv_id,
        messages=get_messages(conv_id)
    )

@app.route("/new", methods=["POST"])
def new_conversation():
    title = request.form.get("title", "محادثة جديدة")
    conv_id = create_conversation(title)
    return redirect(url_for("chat", conv_id=conv_id))

@app.route("/send", methods=["POST"])
def send():
    conv_id = int(request.form["conv_id"])
    user_msg = request.form["message"].strip()
    if not user_msg:
        return redirect(url_for("chat", conv_id=conv_id))

    # حفظ رسالة المستخدم
    save_message(conv_id, "user", user_msg)
    memory = get_memory(conv_id)
    memory.add("user", user_msg)

    # تجهيز السياق للنموذج
    system = {"role": "system", "content": "أنت مساعد ذكي ومفيد. أجب بالعربية."}
    messages = [system] + memory.get()

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        bot_reply = response.choices[0].message.content
    except Exception as e:
        bot_reply = f"⚠️ حدث خطأ: {e}"

    # حفظ رد البوت
    save_message(conv_id, "assistant", bot_reply)
    memory.add("assistant", bot_reply)

    return redirect(url_for("chat", conv_id=conv_id))

@app.route("/delete/<int:conv_id>", methods=["POST"])
def delete(conv_id):
    delete_conversation(conv_id)
    if conv_id in active_memory:
        del active_memory[conv_id]
    return redirect(url_for("index"))

# ========== 7. تشغيل الخادم ==========
if __name__ == "__main__":
    app.run(debug=True)
