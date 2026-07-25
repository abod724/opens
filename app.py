from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ai_engine import process_message
from database import init_db
import os

app = Flask(__name__)
CORS(app)

# شغّل قاعدة البيانات مباشرة بدون before_first_request
init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    response = process_message(user_message)
    return jsonify({"response": response})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
