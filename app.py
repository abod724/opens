from flask import Flask, render_template, request, jsonify
from config import Config
from database import db, ChatHistory
from memory import get_memory, add_to_memory
from ai_engine import get_ai_response
import os
import traceback  # عشان نطبع تفاصيل الخطأ

app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# محاولة تهيئة قاعدة البيانات، لو فشلت يكمل تشغيل عادي (بدون حفظ)
try:
    db.init_app(app)
    with app.app_context():
        db.create_all()
    print("✅ Database connected successfully.")
except Exception as e:
    print(f"⚠️ Database warning (will run without DB): {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'error': 'الرسالة فارغة'}), 400

        # تحديد معرف الجلسة
        session_id = request.remote_addr
        history = get_memory(session_id, limit=5)

        # استدعاء الذكاء الاصطناعي (مع التقاط أي خطأ فيه)
        bot_reply = get_ai_response(user_message, history)

        # حفظ في الذاكرة المؤقتة
        add_to_memory(session_id, user_message, bot_reply)

        # محاولة حفظ في قاعدة البيانات (لو فشلت، نتجاوزها عشان ما توقف الخدمة)
        try:
            record = ChatHistory(user_message=user_message, bot_response=bot_reply)
            db.session.add(record)
            db.session.commit()
        except Exception as db_err:
            print(f"⚠️ DB save skipped: {db_err}")
            db.session.rollback()

        return jsonify({'response': bot_reply})

    except Exception as e:
        # هذا يمسك أي خطأ مفاجئ ويرجعه للواجهة بدل ما يخلي السيرفر يطيح
        error_detail = traceback.format_exc()
        print(f"❌ Chat Error: {error_detail}")
        return jsonify({'error': f'خطأ في السيرفر: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
