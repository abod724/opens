from datetime import datetime
import os
import base64  # تأكد من وجود هذا الاستيراد
from flask import Flask, jsonify, render_template_string, request
from google import genai
from google.genai import types

app = Flask(__name__)

# استخدام مفتاح Gemini
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise Exception("مفتاح Gemini غير موجود في متغيرات البيئة")

client = genai.Client(api_key=API_KEY)

# ========== نظام الذاكرة ==========
session_memory = {}

# ========== تحميل ملف المعرفة ==========
knowledge_content = ""
possible_names = ["Knowledge.md", "knowledge.md", "معرفة.md", "README.md", "ملف_المعرفة.md"]
for filename in possible_names:
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                knowledge_content = f.read()
                break
        except:
            pass

if not knowledge_content:
    knowledge_content = "أنت نبراس، مساعد ذكي."

# ========== تعليمات النظام ==========
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد شخصي ذكي تتحدث باللهجة العامية البيضاء.

**مصادر معرفتك:**
1. **ملف المعرفة** (أدناه) هو مرجعك الأساسي.
2. **معرفتك العامة**.
3. **البحث بالويب** (مفعل تلقائياً عبر الأداة).

**ملف المعرفة الخاص بك:**
{knowledge_content}

**تعليمات مهمة:**
- إذا سألك المستخدم عن أي شيء، حاول أولاً الإجابة من ملف المعرفة.
- إذا كان السؤال يتطلب معلومات حديثة أو غير موجودة، استخدم البحث بالويب.
- دائماً حافظ على لهجتك العامية البيضاء.
- إذا لم تجد المعلومة في أي من المصادر، قل بصراحة "ما عندي علم".
"""

# ========== الواجهة (نفس واجهتك تماماً) ==========
HTML_TEMPLATE = """<!DOCTYPE html>
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
        .header { display: flex; justify-content: flex-end; align-items: center; padding: 14px 18px; border-bottom: 1px solid #eaeef2; flex-shrink: 0; background: #ffffff; }
        .header .menu-btn { background: none; border: none; font-size: 22px; color: #5a6b7c; cursor: pointer; padding: 4px 8px; }
        .dropdown { position: absolute; top: 64px; left: 14px; right: 14px; background: white; border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); display: none; flex-direction: column; z-index: 100; border: 1px solid #eaedf2; }
        .dropdown.show { display: flex; }
        .dropdown .item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; font-size: 15px; color: #1a2b3c; background: none; border: none; width: 100%; text-align: right; cursor: pointer; border-bottom: 1px solid #f0f2f5; }
        .dropdown .item:last-child { border-bottom: none; }
        .dropdown .item i { width: 22px; font-size: 18px; color: #5a6b7c; }
        .dropdown .item:hover { background: #f5f7fa; }
        #chat { flex: 1; overflow-y: auto; padding: 16px 18px; display: flex; flex-direction: column; gap: 10px; background: #ffffff; }
        .msg { max-width: 80%; padding: 10px 16px; border-radius: 20px; font-size: 18px; line-height: 1.6; word-wrap: break-word; white-space: pre-wrap; }
        .msg.user { align-self: flex-end; background: #eef2f7; color: #1a2b3c; border-bottom-left-radius: 6px; }
        .msg.bot { align-self: flex-start; background: #ffffff; color: #1a2b3c; border-bottom-right-radius: 6px; }
        .msg .time { font-size: 9px; opacity: 0.35; display: block; margin-top: 4px; }
        .msg.error { background: #fde8e8; color: #a33; align-self: center; max-width: 90%; }
        .msg .image-upload { max-width: 100%; max-height: 200px; border-radius: 12px; margin: 4px 0; border: 1px solid #ddd; display: block; }
        .msg .file-label { font-size: 12px; color: #6a7b8c; margin-top: 2px; display: block; }
        .input-area { display: flex; align-items: flex-end; gap: 6px; padding: 6px 12px; margin: 8px 14px 16px 14px; background: #f5f7fa; border-radius: 40px; border: 1px solid #dce1e8; flex-shrink: 0; position: relative; }
        .input-area textarea { flex: 1; border: none; background: transparent; padding: 12px 4px; font-size: 17px; outline: none; color: #1a2b3c; direction: rtl; resize: none; overflow: hidden; min-height: 40px; max-height: 120px; line-height: 1.5; }
        .input-area .btn-icon { background: none; border: none; color: #6a7b8c; font-size: 20px; cursor: pointer; padding: 4px; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .input-area .send { background: #4a6a8a; color: white; border: none; width: 44px; height: 44px; border-radius: 50%; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 8px rgba(74,106,138,0.2); }
        .plus-btn { background: none; border: none; color: #4a6a8a; font-size: 24px; cursor: pointer; padding: 4px; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: 0.3s; }
        .plus-options { display: none; position: absolute; bottom: 70px; right: 0; background: #ffffff; border-radius: 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); padding: 12px; gap: 8px; flex-direction: row; border: 1px solid #eaeef2; z-index: 50; }
        .plus-options.show { display: flex; }
        .plus-options .option-btn { background: #f5f7fa; border: none; border-radius: 50%; width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #1a2b3c; cursor: pointer; }
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <button class="menu-btn" id="menuToggle"><i class="fas fa-ellipsis-v"></i></button>
    </div>
    <div class="dropdown" id="dropdown">
        <button class="item" data-action="new"><i class="fas fa-plus-circle"></i> محادثة جديدة</button>
        <button class="item" data-action="library"><i class="fas fa-layer-group"></i> المكتبة</button>
        <button class="item" data-action="history"><i class="fas fa-history"></i> المحادثات السابقة</button>
    </div>
    <div id="chat"></div>
    <div class="input-area">
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
    <input type="file" id="fileInput" accept="image/*" style="display: none;" />
    <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display: none;" />
    <input type="file" id="fileInputGeneric" style="display: none;" />
</div>
<script>
    (function() {
        let conversationHistory = [];
        let pendingImageData = null;
        const chatBox = document.getElementById('chat');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const micBtn = document.getElementById('micBtn');
        const fileInput = document.getElementById('fileInput');
        const cameraInput = document.getElementById('cameraInput');
        const menuToggle = document.getElementById('menuToggle');
        const dropdown = document.getElementById('dropdown');
        const plusBtn = document.getElementById('plusBtn');
        const plusOptions = document.getElementById('plusOptions');
        const cameraBtn = document.getElementById('cameraBtn');
        const galleryBtn = document.getElementById('galleryBtn');

        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        let plusOpen = false;
        plusBtn.addEventListener('click', function() {
            plusOpen = !plusOpen;
            plusOptions.classList.toggle('show', plusOpen);
        });

        cameraBtn.addEventListener('click', function() { cameraInput.click(); plusOptions.classList.remove('show'); });
        galleryBtn.addEventListener('click', function() { fileInput.click(); plusOptions.classList.remove('show'); });

        function handleFile(file) {
            const reader = new FileReader();
            reader.onload = function(ev) {
                const imgData = ev.target.result;
                pendingImageData = imgData;
                addMessage(file.name, 'user', false, imgData);
                sendMessageAfterMedia();
            };
            reader.readAsDataURL(file);
        }

        cameraInput.addEventListener('change', function() { if(this.files[0]) handleFile(this.files[0]); });
        fileInput.addEventListener('change', function() { if(this.files[0]) handleFile(this.files[0]); });

        function addMessage(text, sender = 'bot', isSystem = false, imageData = null) {
            const el = document.createElement('div');
            el.className = `msg ${sender}`;
            const time = new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
            if (imageData) {
                el.innerHTML = `<img src="${imageData}" class="image-upload" /><span class="file-label">${text}</span><span class="time"> ${time}</span>`;
            } else {
                el.innerHTML = `${text} <span class="time">${time}</span>`;
            }
            chatBox.appendChild(el);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        async function sendMessageAfterMedia() {
            const text = userInput.value.trim();
            const imageToSend = pendingImageData;
            pendingImageData = null;
            await sendData(text || "حلل هذه الصورة", imageToSend);
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            addMessage(text, 'user');
            userInput.value = '';
            userInput.style.height = '40px';
            await sendData(text, null);
        }

        async function sendData(text, image) {
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, image: image })
                });
                const data = await res.json();
                if (res.ok) {
                    addMessage(data.reply, 'bot');
                } else {
                    addMessage('خطأ: ' + (data.error || 'مشكلة'), 'error');
                }
            } catch (e) {
                addMessage('تعذر الاتصال بالسيرفر.', 'error');
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
        menuToggle.addEventListener('click', (e) => { e.stopPropagation(); dropdown.classList.toggle('show'); });
        document.addEventListener('click', () => dropdown.classList.remove('show'));
    })();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        image_data = data.get("image", None)

        if not user_message and not image_data:
            return jsonify({"reply": "اكتب شيء أساعدك فيه"})

        user_id = request.remote_addr
        if user_id not in session_memory:
            session_memory[user_id] = []

        # إعداد محتويات الطلب لـ Gemini
        contents = []

        # إضافة الذاكرة السابقة (آخر 10 رسائل)
        history = session_memory[user_id][-10:]
        for h in history:
            contents.append(
                types.Content(
                    role="user" if h["role"] == "user" else "model",
                    parts=[types.Part.from_text(text=h["content"])],
                )
            )

        # تجهيز رسالة المستخدم الحالية (مع الصورة إن وجدت)
        current_parts = []
        if image_data:
            # تحويل Base64 إلى جزء صورة لـ Gemini
            header, encoded = image_data.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            current_parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            )

        current_parts.append(
            types.Part.from_text(text=user_message or "حلل هذه الصورة")
        )
        contents.append(types.Content(role="user", parts=current_parts))

        # استدعاء نموذج Gemini مع تفعيل ميزة البحث بالويب (Google Search)
        response = client.models.generate_content(
            model="gemini-1.5-flash",  # <--- تم التغيير هنا فقط
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                tools=[{"google_search": {}}],  # تفعيل بحث جوجل المدمج
            ),
        )

        reply = response.text.strip()
        if not reply:
            reply = "ما قدرت أجيب لك رد، حاول مرة أخرى."

        # حفظ في الذاكرة
        session_memory[user_id].append({"role": "user", "content": user_message})
        session_memory[user_id].append({"role": "assistant", "content": reply})

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ خطأ: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
