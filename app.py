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
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "لا يوجد رسالة"}), 400

        reply = process_message(messages)
        return jsonify({"reply": reply})
    
    except Exception as e:
        return jsonify({"error": f"خطأ: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
