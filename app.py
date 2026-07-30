from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai
import os
import json
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default-secret-key-change-me")

# ========== إعداد قاعدة البيانات ==========
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nbras.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ========== نماذج قاعدة البيانات ==========
class User(db.Model, object):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    chats = db.relationship('Chat', backref='user', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ========== نظام تسجيل الدخول ==========
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "يرجى تسجيل الدخول أولاً"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== قوالب HTML (مضمنة) ==========
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>تسجيل الدخول - نبراس</title>
<style>body{font-family:Arial;background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:white;padding:40px;border-radius:30px;box-shadow:0 10px 30px rgba(0,0,0,0.05);width:100%;max-width:350px;text-align:center}h2{color:#1a2b3c;margin-bottom:20px}input{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:30px;font-size:15px;outline:none}button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:30px;font-size:16px;cursor:pointer;margin-top:10px}button:hover{background:#3a5a7a}a{color:#4a6a8a;text-decoration:none}.flash{color:#c33;margin:10px 0}</style>
</head>
<body>
<div class="box">
<h2>🔐 تسجيل الدخول</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
{% endwith %}
<form method="post">
<input type="text" name="username" placeholder="اسم المستخدم" required>
<input type="password" name="password" placeholder="كلمة المرور" required>
<button type="submit">دخول</button>
</form>
<p>ليس لديك حساب؟ <a href="/register">سجل الآن</a></p>
</div>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>تسجيل جديد - نبراس</title>
<style>body{font-family:Arial;background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:white;padding:40px;border-radius:30px;box-shadow:0 10px 30px rgba(0,0,0,0.05);width:100%;max-width:350px;text-align:center}h2{color:#1a2b3c;margin-bottom:20px}input{width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:30px;font-size:15px;outline:none}button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:30px;font-size:16px;cursor:pointer;margin-top:10px}button:hover{background:#3a5a7a}a{color:#4a6a8a;text-decoration:none}</style>
</head>
<body>
<div class="box">
<h2>📝 إنشاء حساب</h2>
<form method="post">
<input type="text" name="username" placeholder="اسم المستخدم" required>
<input type="email" name="email" placeholder="البريد الإلكتروني" required>
<input type="password" name="password" placeholder="كلمة المرور" required>
<button type="submit">تسجيل</button>
</form>
<p>لديك حساب؟ <a href="/login">سجل دخول</a></p>
</div>
</body>
</html>
"""

# ========== مفتاح OpenAI ==========
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("المفتاح غير موجود")
client = openai.OpenAI(api_key=API_KEY)

# ========== تحميل ملف المعرفة ==========
knowledge_content = ""
possible_names = ["Knowledge.md", "knowledge.md", "معرفة.md", "README.md", "ملف_المعرفة.md"]
for filename in possible_names:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                knowledge_content = f.read()
                print(f"✅ تم تحميل ملف المعرفة: {filename}")
                break
        except:
            pass

# ========== تعليمات النظام ==========
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد شخصي طبيعي، تتحدث باللهجة العامية البيضاء.
**تعليماتك العامة:**
- خلك إنسان: تفاعل مع كلام المستخدم، اسأل، شارك، ناقش.
- إذا سألك "من طورك؟" قل: "أنا من تطوير وبرمجة أفضل المطورين في العالم."
- استخدم ملف المعرفة إذا وجدت المعلومة فيه.
- للأحداث الجديدة، استخدم البحث بالويب.
- إذا ما لقيت المعلومة، قل "ما عندي علم".
- إذا أرسل لك صورة، حللها وصفها بالعامية.

**ملف المعرفة:**
{knowledge_content}
"""

# ========== نظام الإعلانات ==========
ADS_FILE = "ads.json"
ads_config = {"enabled": False, "interval": 5, "ads": []}
if os.path.exists(ADS_FILE):
    try:
        with open(ADS_FILE, "r", encoding="utf-8") as f:
            ads_config = json.load(f)
    except:
        pass

# ========== واجهة نبراس الرئيسية ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background: #ffffff; height: 100dvh; display: flex; justify-content: center; align-items: center; margin: 0; padding: 0; }
        .app { width: 100%; max-width: 450px; height: 100dvh; background: #ffffff; display: flex; flex-direction: column; position: relative; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #eaeef2; flex-shrink: 0; background: #ffffff; }
        .header .user-info { font-size: 14px; color: #1a2b3c; display: flex; align-items: center; gap: 8px; }
        .header .user-info i { color: #4a6a8a; }
        .header .menu-btn { background: none; border: none; font-size: 22px; color: #5a6b7c; cursor: pointer; padding: 4px 8px; }
        .dropdown { position: absolute; top: 64px; left: 14px; right: 14px; background: white; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); display: none; flex-direction: column; z-index: 100; border: 1px solid #eaedf2; }
        .dropdown.show { display: flex; }
        .dropdown .item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; font-size: 15px; color: #1a2b3c; background: none; border: none; width: 100%; text-align: right; cursor: pointer; border-bottom: 1px solid #f0f2f5; }
        .dropdown .item:last-child { border-bottom: none; }
        .dropdown .item i { width: 22px; font-size: 18px; color: #5a6b7c; }
        .dropdown .item:hover { background: #f5f7fa; }
        #chat { flex: 1; overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; background: #ffffff; }
        .msg { max-width: 80%; padding: 10px 16px; border-radius: 20px; font-size: 17px; line-height: 1.6; word-wrap: break-word; white-space: pre-wrap; }
        .msg.user { align-self: flex-end; background: #eef2f7; color: #1a2b3c; border-bottom-left-radius: 6px; font-size: 17px; }
        .msg.bot { align-self: flex-start; background: #ffffff; color: #1a2b3c; border-bottom-right-radius: 6px; font-size: 17px; }
        .msg .time { font-size: 9px; opacity: 0.35; display: block; margin-top: 4px; }
        .msg.error { background: #fde8e8; color: #a33; align-self: center; max-width: 90%; }
        .msg .image-upload { max-width: 100%; max-height: 200px; border-radius: 12px; margin: 4px 0; border: 1px solid #ddd; display: block; }
        .msg .file-label { font-size: 12px; color: #6a7b8c; margin-top: 2px; display: block; }
        .input-area { display: flex; flex-direction: column; align-items: stretch; gap: 4px; padding: 6px 12px; margin: 8px 14px 16px 14px; background: #f5f7fa; border-radius: 40px; border: 1px solid #dce1e8; flex-shrink: 0; position: relative; }
        .input-area .input-row { display: flex; align-items: flex-end; gap: 6px; }
        .input-area textarea { flex: 1; border: none; background: transparent; padding: 12px 4px; font-size: 18px; outline: none; color: #1a2b3c; direction: rtl; resize: none; overflow: hidden; min-height: 40px; max-height: 120px; font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.5; }
        .input-area textarea::placeholder { color: #9aabbc; }
        .input-area .btn-icon { background: none; border: none; color: #6a7b8c; font-size: 20px; cursor: pointer; padding: 4px; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .input-area .btn-icon:hover { background: #e8ecf0; }
        .input-area .mic-btn { color: #4a6a8a; }
        .input-area .mic-btn.listening { color: #c33; background: #fde8e8; }
        .input-area .send { background: #4a6a8a; color: white; border: none; width: 44px; height: 44px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 8px rgba(74,106,138,0.2); }
        .input-area .send:hover { background: #3a5a7a; }
        .image-preview { display: none; position: relative; padding: 4px 0 0 0; margin: 0 4px; }
        .image-preview.show { display: block; }
        .image-preview img { max-height: 80px; max-width: 100%; border-radius: 12px; border: 1px solid #dce1e8; object-fit: cover; }
        .image-preview .file-info { display: flex; align-items: center; gap: 8px; background: #eef2f7; padding: 4px 12px; border-radius: 12px; font-size: 13px; color: #1a2b3c; max-width: 100%; }
        .image-preview .file-info i { font-size: 24px; color: #4a6a8a; }
        .image-preview .file-info span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px; }
        .image-preview .remove-preview { position: absolute; top: -6px; left: -6px; background: #c33; color: white; border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0; }
        .image-preview .remove-preview:hover { background: #a33; }
        .plus-btn { background: none; border: none; color: #4a6a8a; font-size: 24px; cursor: pointer; padding: 4px; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: 0.3s; }
        .plus-btn:hover { background: #e8ecf0; }
        .plus-btn.rotate { transform: rotate(45deg); }
        .plus-options { display: none; position: absolute; bottom: 70px; right: 0; background: #ffffff; border-radius: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); padding: 12px; gap: 8px; flex-direction: row; border: 1px solid #eaeef2; z-index: 50; }
        .plus-options.show { display: flex; }
        .plus-options .option-btn { background: #f5f7fa; border: none; border-radius: 50%; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #1a2b3c; cursor: pointer; transition: 0.2s; }
        .plus-options .option-btn:hover { background: #e8ecf0; transform: scale(1.05); }
        .plus-options .option-btn.camera { color: #e74c3c; }
        .plus-options .option-btn.gallery { color: #2ecc71; }
        .plus-options .option-btn.files { color: #3498db; }
        @media (max-width: 420px) {
            .header { padding: 12px 14px; }
            .dropdown { top: 58px; left: 10px; right: 10px; }
            .dropdown .item { padding: 12px 14px; font-size: 14px; }
            #chat { padding: 12px 14px; }
            .msg { font-size: 15px; padding: 8px 12px; }
            .input-area { margin: 6px 10px 12px 10px; padding: 4px 10px; }
            .input-area textarea { font-size: 16px; padding: 10px 2px; }
            .input-area .send { width: 40px; height: 40px; font-size: 16px; }
            .input-area .btn-icon { width: 34px; height: 34px; font-size: 18px; }
            .plus-btn { width: 34px; height: 34px; font-size: 20px; }
            .plus-options { bottom: 60px; padding: 8px; gap: 6px; }
            .plus-options .option-btn { width: 44px; height: 44px; font-size: 18px; }
            .msg .image-upload { max-height: 150px; }
            .image-preview img { max-height: 60px; }
        }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <div class="user-info">
            {% if current_user.is_authenticated %}
                <i class="fas fa-user-circle"></i> {{ current_user.username }}
                <a href="/logout" style="color:#c33; font-size:13px; margin-right:8px;">خروج</a>
            {% else %}
                <a href="/login" style="color:#4a6a8a; font-size:14px;">دخول</a>
            {% endif %}
        </div>
        <button class="menu-btn" id="menuToggle"><i class="fas fa-ellipsis-v"></i></button>
    </div>
    <div class="dropdown" id="dropdown">
        <button class="item" data-action="new"><i class="fas fa-plus-circle"></i> محادثة جديدة</button>
        <button class="item" data-action="library"><i class="fas fa-layer-group"></i> المكتبة</button>
        <button class="item" data-action="history"><i class="fas fa-history"></i> المحادثات السابقة</button>
    </div>
    <div id="chat"></div>
    <div class="input-area">
        <div class="image-preview" id="imagePreview">
            <div id="previewContent"></div>
            <button class="remove-preview" id="removePreviewBtn" title="إزالة">×</button>
        </div>
        <div class="input-row">
            <button class="btn-icon mic-btn" id="micBtn" title="تسجيل صوت"><i class="fas fa-microphone"></i></button>
            <button class="plus-btn" id="plusBtn" title="إضافة"><i class="fas fa-plus"></i></button>
            <div class="plus-options" id="plusOptions">
                <button class="option-btn camera" id="cameraBtn" title="كاميرا"><i class="fas fa-camera"></i></button>
                <button class="option-btn gallery" id="galleryBtn" title="معرض الصور"><i class="fas fa-images"></i></button>
                <button class="option-btn files" id="filesBtn" title="ملفات"><i class="fas fa-folder"></i></button>
            </div>
            <textarea id="userInput" placeholder="اكتب رسالة..." autofocus rows="1"></textarea>
            <button class="send" id="sendBtn"><i class="fas fa-arrow-left"></i></button>
        </div>
    </div>
    <input type="file" id="fileInput" accept="image/*" style="display: none;" />
    <input type="file" id="cameraInput" accept="image/*,video/*" capture="environment" style="display: none;" />
    <input type="file" id="fileInputGeneric" style="display: none;" />
</div>
<script>
    (function() {
        let conversationHistory = [];
        let pendingFileData = null;
        let messageCount = 0;
        const chatBox = document.getElementById('chat');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const micBtn = document.getElementById('micBtn');
        const fileInput = document.getElementById('fileInput');
        const cameraInput = document.getElementById('cameraInput');
        const fileInputGeneric = document.getElementById('fileInputGeneric');
        const menuToggle = document.getElementById('menuToggle');
        const dropdown = document.getElementById('dropdown');
        const plusBtn = document.getElementById('plusBtn');
        const plusOptions = document.getElementById('plusOptions');
        const cameraBtn = document.getElementById('cameraBtn');
        const galleryBtn = document.getElementById('galleryBtn');
        const filesBtn = document.getElementById('filesBtn');
        const imagePreview = document.getElementById('imagePreview');
        const previewContent = document.getElementById('previewContent');
        const removePreviewBtn = document.getElementById('removePreviewBtn');

        function clearPreview() {
            pendingFileData = null;
            imagePreview.classList.remove('show');
            previewContent.innerHTML = '';
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
        }
        removePreviewBtn.addEventListener('click', clearPreview);

        function showFilePreview(fileData, fileName, fileType) {
            pendingFileData = { data: fileData, name: fileName, type: fileType };
            let html = '';
            if (fileType && fileType.startsWith('image/')) {
                html = `<img src="${fileData}" style="max-height:80px;max-width:100%;border-radius:12px;border:1px solid #dce1e8;object-fit:cover;" />`;
            } else if (fileType && fileType.startsWith('video/')) {
                html = `<video src="${fileData}" style="max-height:80px;max-width:100%;border-radius:12px;border:1px solid #dce1e8;object-fit:cover;" controls></video>`;
            } else {
                let icon = 'fa-file';
                if (fileType && fileType.includes('pdf')) icon = 'fa-file-pdf';
                else if (fileType && (fileType.includes('word') || fileType.includes('document'))) icon = 'fa-file-word';
                else if (fileType && (fileType.includes('excel') || fileType.includes('spreadsheet'))) icon = 'fa-file-excel';
                else if (fileType && (fileType.includes('zip') || fileType.includes('rar'))) icon = 'fa-file-archive';
                else if (fileType && fileType.includes('text')) icon = 'fa-file-alt';
                html = `<div class="file-info"><i class="fas ${icon}"></i><span>${fileName || 'ملف'}</span></div>`;
            }
            previewContent.innerHTML = html;
            imagePreview.classList.add('show');
            setTimeout(() => {
                userInput.style.height = 'auto';
                userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
            }, 50);
        }

        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        let plusOpen = false;
        plusBtn.addEventListener('click', function() {
            plusOpen = !plusOpen;
            plusOptions.classList.toggle('show', plusOpen);
            this.classList.toggle('rotate', plusOpen);
        });
        document.addEventListener('click', function(e) {
            if (!plusBtn.contains(e.target) && !plusOptions.contains(e.target)) {
                plusOptions.classList.remove('show');
                plusOpen = false;
                plusBtn.classList.remove('rotate');
            }
        });

        cameraBtn.addEventListener('click', function() {
            cameraInput.value = '';
            cameraInput.click();
            plusOptions.classList.remove('show');
            plusOpen = false;
            plusBtn.classList.remove('rotate');
        });
        cameraInput.addEventListener('change', function(e) {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                if (file.type && (file.type.startsWith('image/') || file.type.startsWith('video/'))) {
                    const reader = new FileReader();
                    reader.onload = function(ev) {
                        showFilePreview(ev.target.result, file.name, file.type);
                        cameraInput.value = '';
                    };
                    reader.readAsDataURL(file);
                } else {
                    addMessage('الرجاء اختيار صورة أو فيديو من الكاميرا.', 'bot', true);
                    cameraInput.value = '';
                }
            }
        });

        galleryBtn.addEventListener('click', function() {
            fileInput.click();
            plusOptions.classList.remove('show');
            plusOpen = false;
            plusBtn.classList.remove('rotate');
        });
        fileInput.addEventListener('change', function(e) {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = function(ev) {
                    showFilePreview(ev.target.result, file.name, file.type);
                    fileInput.value = '';
                };
                reader.readAsDataURL(file);
            }
        });

        filesBtn.addEventListener('click', function() {
            fileInputGeneric.click();
            plusOptions.classList.remove('show');
            plusOpen = false;
            plusBtn.classList.remove('rotate');
        });
        fileInputGeneric.addEventListener('change', function(e) {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const reader = new FileReader();
                reader.onload = function(ev) {
                    showFilePreview(ev.target.result, file.name, file.type);
                    fileInputGeneric.value = '';
                };
                reader.readAsDataURL(file);
            }
        });

        function addMessage(text, sender = 'bot', isSystem = false, imageData = null, fileInfo = null) {
            const el = document.createElement('div');
            el.className = `msg ${sender}`;
            if (sender === 'error') el.classList.add('error');
            const now = new Date();
            const time = now.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
            if (imageData && sender === 'user') {
                let content = '';
                if (fileInfo && fileInfo.type && fileInfo.type.startsWith('video/')) {
                    content = `<video src="${imageData}" style="max-width:100%;max-height:200px;border-radius:12px;margin:4px 0;border:1px solid #ddd;" controls></video>`;
                } else if (fileInfo && fileInfo.type && fileInfo.type.startsWith('image/')) {
                    content = `<img src="${imageData}" class="image-upload" />`;
                } else {
                    let icon = 'fa-file';
                    if (fileInfo && fileInfo.type && fileInfo.type.includes('pdf')) icon = 'fa-file-pdf';
                    else if (fileInfo && fileInfo.type && fileInfo.type.includes('word')) icon = 'fa-file-word';
                    else if (fileInfo && fileInfo.type && fileInfo.type.includes('excel')) icon = 'fa-file-excel';
                    else if (fileInfo && fileInfo.type && fileInfo.type.includes('zip')) icon = 'fa-file-archive';
                    else icon = 'fa-file-alt';
                    content = `<i class="fas ${icon}" style="font-size:30px;display:block;text-align:center;margin:4px 0;"></i><span style="font-size:12px;color:#6a7b8c;display:block;text-align:center;">${fileInfo ? fileInfo.name : 'ملف'}</span>`;
                }
                el.innerHTML = `${content}<span class="time"> ${time}</span>`;
                chatBox.appendChild(el);
                chatBox.scrollTop = chatBox.scrollHeight;
                if (!isSystem && sender !== 'error') {
                    conversationHistory.push({ role: sender, content: '📎 ملف مرفق' });
                    if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);
                    saveHistory(sender, text || 'ملف');
                }
                return;
            }
            if (sender === 'bot' && !isSystem) {
                el.innerHTML = `<span class="typing-text"></span><span class="time"> ${time}</span>`;
                chatBox.appendChild(el);
                chatBox.scrollTop = chatBox.scrollHeight;
                const typingSpan = el.querySelector('.typing-text');
                let index = 0;
                function typeChar() {
                    if (index < text.length) {
                        typingSpan.textContent += text.charAt(index);
                        index++;
                        chatBox.scrollTop = chatBox.scrollHeight;
                        setTimeout(typeChar, 20);
                    }
                }
                typeChar();
                if (!isSystem && sender !== 'error') {
                    conversationHistory.push({ role: sender, content: text });
                    if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);
                    saveHistory(sender, text);
                }
                return;
            }
            el.innerHTML = `${text} <span class="time">${time}</span>`;
            chatBox.appendChild(el);
            chatBox.scrollTop = chatBox.scrollHeight;
            if (!isSystem && sender !== 'error') {
                conversationHistory.push({ role: sender, content: text });
                if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);
                saveHistory(sender, text);
            }
        }

        function saveHistory(sender, text) {
            let hist = JSON.parse(localStorage.getItem('niras_history') || '[]');
            hist.push({ sender, text, time: new Date().toISOString() });
            if (hist.length > 100) hist = hist.slice(-100);
            localStorage.setItem('niras_history', JSON.stringify(hist));
        }
        function getHistory() {
            return JSON.parse(localStorage.getItem('niras_history') || '[]');
        }

        function getImages() {
            return JSON.parse(localStorage.getItem('niras_images') || '[]');
        }
        function saveImages(imgs) {
            localStorage.setItem('niras_images', JSON.stringify(imgs));
        }
        function deleteImage(index) {
            let imgs = getImages();
            if (index >= 0 && index < imgs.length) {
                imgs.splice(index, 1);
                saveImages(imgs);
                addMessage('تم حذف الصورة.', 'bot', true);
                showLibrary();
            }
        }

        function showLibrary() {
            const imgs = getImages();
            if (imgs.length === 0) {
                addMessage('لا توجد صور.', 'bot', true);
                return;
            }
            let html = '<div class="gallery">';
            imgs.forEach((src, idx) => {
                html += `<div class="img-wrap">
                    <img src="${src}" />
                    <button class="del" data-idx="${idx}">×</button>
                </div>`;
            });
            html += '</div>';
            const container = document.createElement('div');
            container.className = 'msg bot';
            container.innerHTML = html + `<span class="time">${new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' })}</span>`;
            chatBox.appendChild(container);
            chatBox.scrollTop = chatBox.scrollHeight;
            container.querySelectorAll('.del').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const idx = parseInt(this.dataset.idx);
                    deleteImage(idx);
                });
            });
        }

        function showHistory() {
            const hist = getHistory();
            if (hist.length === 0) {
                addMessage('لا توجد محادثات.', 'bot', true);
                return;
            }
            let msg = '';
            hist.slice(-12).forEach((entry) => {
                const t = new Date(entry.time).toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
                const txt = entry.text.length > 40 ? entry.text.substring(0, 40) + '...' : entry.text;
                msg += `- ${txt} (${t})\n`;
            });
            addMessage(msg, 'bot', true);
            hist.slice(-5).forEach(entry => {
                const btn = document.createElement('button');
                btn.textContent = entry.text.length > 22 ? entry.text.substring(0, 22) + '…' : entry.text;
                btn.style.cssText = 'background:#f0f2f5;border:none;border-radius:30px;padding:4px 12px;margin:4px;cursor:pointer;font-size:13px;color:#1a2b3c;';
                btn.onclick = function() { userInput.value = entry.text; userInput.focus(); };
                chatBox.appendChild(btn);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function newChat() {
            chatBox.innerHTML = '';
            conversationHistory = [];
            clearPreview();
        }

        function handleAction(action) {
            dropdown.classList.remove('show');
            switch(action) {
                case 'new': newChat(); break;
                case 'library': showLibrary(); break;
                case 'history': showHistory(); break;
                default: break;
            }
        }

        document.querySelectorAll('.dropdown .item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                handleAction(item.dataset.action);
            });
        });

        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });
        document.addEventListener('click', () => {
            dropdown.classList.remove('show');
        });

        let recognition = null;
        micBtn.addEventListener('click', function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                addMessage('المتصفح لا يدعم التعرف على الصوت.', 'bot', true);
                return;
            }
            if (this.classList.contains('listening')) {
                this.classList.remove('listening');
                if (recognition) recognition.stop();
                return;
            }
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SR();
            recognition.lang = 'ar-SA';
            recognition.continuous = false;
            recognition.interimResults = false;
            this.classList.add('listening');
            addMessage('جاري الاستماع...', 'bot', true);
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                userInput.value = transcript;
                micBtn.classList.remove('listening');
                setTimeout(() => {
                    sendMessage();
                }, 300);
            };
            recognition.onerror = (event) => {
                micBtn.classList.remove('listening');
                if (event.error !== 'aborted') {
                    addMessage('لم يتعرف على الصوت، حاول مرة أخرى.', 'bot', true);
                }
            };
            recognition.onend = () => {
                micBtn.classList.remove('listening');
            };
            recognition.start();
        });

        async function sendMessage() {
            const text = userInput.value.trim();
            const fileData = pendingFileData;
            if (!text && !fileData) return;

            if (fileData) {
                addMessage(fileData.name || 'ملف', 'user', false, fileData.data, { name: fileData.name, type: fileData.type });
                if (fileData.type && fileData.type.startsWith('image/')) {
                    let imgs = getImages();
                    imgs.push(fileData.data);
                    saveImages(imgs);
                }
            }
            if (text) {
                addMessage(text, 'user');
                messageCount++;
            }

            const imageToSend = fileData && (fileData.type && fileData.type.startsWith('image/')) ? fileData.data : null;
            const fileToSend = fileData ? fileData.data : null;
            const fileName = fileData ? fileData.name : null;
            const fileType = fileData ? fileData.type : null;

            userInput.value = '';
            userInput.style.height = '40px';
            clearPreview();
            userInput.focus();

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        image: imageToSend,
                        file: fileToSend,
                        fileName: fileName,
                        fileType: fileType,
                        history: conversationHistory,
                        message_count: messageCount
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    addMessage(data.reply, 'bot');
                } else {
                    addMessage('خطأ: ' + (data.error || 'مشكلة في السيرفر'), 'error');
                }
            } catch (e) {
                addMessage('تعذر الاتصال بالسيرفر.', 'error');
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    })();
</script>
</body>
</html>
"""

# ========== مسارات المصادقة ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed = generate_password_hash(request.form['password'])
        new_user = User(
            username=request.form['username'],
            email=request.form['email'],
            password_hash=hashed
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ========== الصفحة الرئيسية ==========
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ========== نقطة الدردشة ==========
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        image_data = data.get("image", None)
        file_data = data.get("file", None)
        file_name = data.get("fileName", "")
        file_type = data.get("fileType", "")
        history = data.get("history", [])
        message_count = data.get("message_count", 0)

        # ===== التحقق من الإعلان =====
        ad_message = None
        if ads_config.get("enabled", False):
            interval = ads_config.get("interval", 5)
            if message_count > 0 and message_count % interval == 0:
                ads_list = ads_config.get("ads", [])
                if ads_list:
                    ad = random.choice(ads_list)
                    ad_message = ad.get("message", "")

        # ===== بناء السياق =====
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        if image_data:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message or "حلل هذه الصورة باللهجة العامية"},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            })
        elif file_data and file_type and not file_type.startswith('image/'):
            reply_text = f"استلمت ملفك '{file_name}' (نوعه: {file_type}). حالياً لا أستطيع تحليل هذا النوع من الملفات، لكن يمكنني مساعدتك في أي سؤال نصي."
            if ad_message:
                reply_text += f"\n\n---\n{ad_message}"
            return jsonify({"reply": reply_text})
        else:
            if user_message:
                messages.append({"role": "user", "content": user_message})

        if image_data:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0.8
            )
            reply = response.choices[0].message.content.strip()
            if not reply:
                reply = "ما قدرت أحلل الصورة، حاول مرة أخرى."
        else:
            full_context = ""
            for msg in messages:
                if msg["role"] == "system": continue
                if msg["role"] == "user":
                    if isinstance(msg["content"], list):
                        for part in msg["content"]:
                            if part["type"] == "text":
                                full_context += part["text"] + "\n"
                    else:
                        full_context += msg["content"] + "\n"
                elif msg["role"] == "assistant":
                    full_context += "نبراس: " + msg["content"] + "\n"

            try:
                response = client.responses.create(
                    model="gpt-4o-mini",
                    instructions=f"{SYSTEM_PROMPT}\n\nسياق المحادثة السابقة:\n{full_context}",
                    input=user_message,
                    tools=[{"type": "web_search"}],
                    temperature=0.8,
                    max_output_tokens=1000
                )
                reply = response.output_text.strip()
                if not reply:
                    reply = "ما قدرت أجيب لك معلومة."
            except Exception as e:
                print(f"⚠️ خطأ في البحث: {e}")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.8
                )
                reply = response.choices[0].message.content.strip()
                if not reply:
                    reply = "ما قدرت أجيب لك رد."

        # ===== إضافة الإعلان إذا كان موجوداً =====
        if ad_message:
            reply = f"{reply}\n\n---\n{ad_message}"

        # ===== حفظ المحادثة في قاعدة البيانات إذا كان المستخدم مسجلاً =====
        if current_user.is_authenticated:
            new_chat = Chat(
                user_id=current_user.id,
                user_message=user_message or "ملف مرفق",
                bot_response=reply
            )
            db.session.add(new_chat)
            db.session.commit()

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ خطأ: {e}")
        return jsonify({"error": str(e)}), 500

# ========== تشغيل التطبيق ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
