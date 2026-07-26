from flask import Flask, render_template, request, jsonify, session
from config import Config
from database import db, ChatHistory
from memory import get_memory, add_to_memory
from ai_engine import get_ai_response
import os

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# إنشاء الجداول عند أول تشغيل
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')  # يجب أن يكون لديك ملف index.html في مجلد templates

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'الرسالة فارغة'}), 400

    # تحديد معرف الجلسة (أو استخدام عنوان IP مؤقت)
    session_id = request.remote_addr
    # استرجاع آخر 5 محادثات من الذاكرة المؤقتة للسياق
    history = get_memory(session_id, limit=5)

    # استدعاء الذكاء الاصطناعي مع السياق
    bot_reply = get_ai_response(user_message, history)

    # حفظ المحادثة في الذاكرة المؤقتة
    add_to_memory(session_id, user_message, bot_reply)

    # حفظ في قاعدة البيانات (للأرشفة)
    try:
        record = ChatHistory(user_message=user_message, bot_response=bot_reply)
        db.session.add(record)
        db.session.commit()
    except Exception as e:
        print(f"Database error: {e}")
        db.session.rollback()

    return jsonify({'response': bot_reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
