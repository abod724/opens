from flask import Flask, render_template, request, jsonify
from config import Config
from database import init_db
from ai_engine import chat_with_myais
from memory import save_message, get_last_messages

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY

# تشغيل قاعدة البيانات أول ما يبدأ السيرفر
@app.before_first_request
def setup():
    init_db()

# الصفحة الرئيسية
@app.route("/")
def index():
    return render_template("index.html")

# واجهة API للمحادثة
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_message = data.get("message", "")

    # جلب آخر 5 رسائل من الذاكرة
    history = get_last_messages(limit=5)
    messages = history + [{"role": "user", "content": user_message}]

    # رد المساعد
    reply = chat_with_myais(messages)

    # حفظ الرسائل في قاعدة البيانات
    save_message("user", user_message)
    save_message("assistant", reply)

    return jsonify({"reply": reply})

# تشغيل التطبيق
if __name__ == "__main__":
    app.run(debug=True)