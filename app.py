from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ai_engine import process_message
from database import init_db
import os

app = Flask(__name__)
CORS(app)

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "لا يوجد رسالة"}), 400

        reply = process_message(user_message)
        return jsonify({"response": reply})
    
    except Exception as e:
        return jsonify({"error": f"خطأ في السيرفر: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
