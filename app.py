from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import fetch_all, init_db
from auth import User, get_user_by_id, get_user_by_email, create_user, check_password
from memory import add_message, get_history, clear_memory
import openai
import os
import json
from flask import Response

# ==================== تهيئة التطبيق ====================
app = Flask(__name__)

# ==================== قراءة المتغيرات من البيئة ====================
print("🔍 جارٍ قراءة المتغيرات...")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY غير موجود!")
    raise Exception("OPENAI_API_KEY غير موجود في متغيرات البيئة")
else:
    print(f"✅ OPENAI_API_KEY: موجود (يبدأ بـ {OPENAI_API_KEY[:8]}...)")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL غير موجود!")
    raise Exception("DATABASE_URL غير موجود في متغيرات البيئة")
else:
    print(f"✅ DATABASE_URL: موجود (يبدأ بـ {DATABASE_URL[:20]}...)")

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    print("⚠️ SECRET_KEY غير موجود، سيتم استخدام القيمة الافتراضية")
    SECRET_KEY = "default-secret-key-change-in-production"
else:
    print(f"✅ SECRET_KEY: موجود")

app.secret_key = SECRET_KEY

# ==================== تهيئة قاعدة البيانات ====================
init_db()
print("✅ قاعدة البيانات جاهزة")

# ==================== تهيئة OpenAI ====================
client = openai.OpenAI(api_key=OPENAI_API_KEY)
print("✅ OpenAI جاهز")

# ==================== نظام المصادقة ====================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

# ==================== تعليمات النظام ====================
SYSTEM_PROMPT = """
أنت "نبراس"، مساعد شخصي ذكي تتحدث باللهجة العامية السعودية البيضاء.

**مصادر معرفتك:**
1. **معرفتك العامة**.
2. **البحث بالويب** للمعلومات الحديثة (إذا كان السؤال يتطلب ذلك).

**تعليمات مهمة:**
- إذا سألك المستخدم عن أي شيء، حاول الإجابة من معرفتك العامة أولاً.
- إذا كان السؤال يتطلب معلومات حديثة (أخبار، أحداث، طقس)، استخدم البحث بالويب.
- دائماً حافظ على لهجتك العامية السعودية البيضاء.
- لا تذكر أبداً أي مصدر محدد لمعلوماتك.
- إذا لم تجد المعلومة، قل بصراحة "ما عندي علم".
"""

# ==================== واجهات HTML ====================

LOGIN_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>دخول - نبراس</title>
    <style>
        body{background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;font-family:'Segoe UI',Arial,sans-serif;margin:0}
        .box{background:white;padding:40px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.08);width:340px;text-align:center}
        h2{color:#1a2b3c}
        input{width:100%;padding:12px;border:1px solid #dce1e8;border-radius:10px;font-size:16px;margin:8px 0;text-align:center;box-sizing:border-box}
        button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:10px;font-size:18px;cursor:pointer}
        button:hover{background:#3a5a7a}
        .error{color:#c33;margin:8px 0}
        a{color:#4a6a8a;text-decoration:none;display:block;margin-top:10px}
    </style>
</head>
<body>
<div class="box">
    <h2>🔐 دخول نبراس</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
        <input type="email" name="email" placeholder="البريد الإلكتروني" required>
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">دخول</button>
    </form>
    <a href="{{ url_for('register') }}">ليس لديك حساب؟ سجل الآن</a>
</div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل - نبراس</title>
    <style>
        body{background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;font-family:'Segoe UI',Arial,sans-serif;margin:0}
        .box{background:white;padding:40px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.08);width:340px;text-align:center}
        h2{color:#1a2b3c}
        input{width:100%;padding:12px;border:1px solid #dce1e8;border-radius:10px;font-size:16px;margin:8px 0;text-align:center;box-sizing:border-box}
        button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:10px;font-size:18px;cursor:pointer}
        button:hover{background:#3a5a7a}
        .error{color:#c33;margin:8px 0}
        a{color:#4a6a8a;text-decoration:none;display:block;margin-top:10px}
    </style>
</head>
<body>
<div class="box">
    <h2>📝 حساب جديد</h2>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
        <input type="text" name="name" placeholder="الاسم الكامل" required>
        <input type="email" name="email" placeholder="البريد الإلكتروني" required>
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">تسجيل</button>
    </form>
    <a href="{{ url_for('login') }}">لديك حساب؟ سجل دخول</a>
</div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif}
        body{background:#fff;height:100dvh;display:flex;justify-content:center;align-items:center}
        .app{width:100%;max-width:450px;height:100dvh;display:flex;flex-direction:column;background:#fff}
        .header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #eaeef2}
        .header .menu-btn{background:none;border:none;font-size:22px;color:#5a6b7c;cursor:pointer;padding:4px}
        .header .logout-btn{background:#e74c3c;color:#fff;border:none;padding:6px 14px;border-radius:30px;cursor:pointer;font-size:14px;text-decoration:none}
        .header .logout-btn:hover{background:#c0392b}
        .dropdown{display:none;position:absolute;top:64px;left:14px;right:14px;background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,0.08);z-index:100;border:1px solid #eaedf2}
        .dropdown.show{display:flex;flex-direction:column}
        .dropdown .item{padding:14px 18px;font-size:15px;background:none;border:none;width:100%;text-align:right;cursor:pointer;border-bottom:1px solid #f0f2f5}
        .dropdown .item:hover{background:#f5f7fa}
        #chat{flex:1;overflow-y:auto;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
        .msg{max-width:80%;padding:10px 16px;border-radius:20px;font-size:18px;line-height:1.6;word-wrap:break-word;white-space:pre-wrap}
        .msg.user{align-self:flex-end;background:#eef2f7;border-bottom-left-radius:6px}
        .msg.bot{align-self:flex-start;background:#fff;border-bottom-right-radius:6px}
        .msg .time{font-size:9px;opacity:0.35;display:block;margin-top:4px}
        .msg.error{background:#fde8e8;color:#a33;align-self:center;max-width:90%}
        .msg .image-upload{max-width:100%;max-height:200px;border-radius:12px;margin:4px 0;border:1px solid #ddd;display:block}
        .input-area{display:flex;align-items:flex-end;gap:6px;padding:6px 12px;margin:8px 14px 16px;background:#f5f7fa;border-radius:40px;border:1px solid #dce1e8}
        .input-area textarea{flex:1;border:none;background:transparent;padding:12px 4px;font-size:17px;outline:none;color:#1a2b3c;direction:rtl;resize:none;overflow:hidden;min-height:40px;max-height:120px;font-family:inherit}
        .input-area .send{background:#4a6a8a;color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}
        .input-area .btn-icon{background:none;border:none;color:#6a7b8c;font-size:20px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center}
        .input-area .mic-btn.listening{color:#c33;background:#fde8e8}
        .plus-btn{background:none;border:none;color:#4a6a8a;font-size:24px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center}
        .plus-options{display:none;position:absolute;bottom:70px;right:0;background:#fff;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.12);padding:12px;gap:8px;flex-direction:row;border:1px solid #eaeef2;z-index:50}
        .plus-options.show{display:flex}
        .plus-options .option-btn{background:#f5f7fa;border:none;border-radius:50%;width:52px;height:52px;font-size:22px;color:#1a2b3c;cursor:pointer}
        .plus-options .option-btn:hover{background:#e8ecf0}
    </style>
</head>
<body>
<div class="app">
    <div class="header">
        <button class="menu-btn" id="menuToggle"><i class="fas fa-ellipsis-v"></i></button>
        <span style="font-size:16px;color:#1a2b3c;font-weight:bold">نبراس</span>
        <a href="/logout" class="logout-btn"><i class="fas fa-sign-out-alt"></i> خروج</a>
    </div>
    <div class="dropdown" id="dropdown">
        <button class="item" data-action="new"><i class="fas fa-plus-circle"></i> محادثة جديدة</button>
        <button class="item" data-action="library"><i class="fas fa-layer-group"></i> المكتبة</button>
        <button class="item" data-action="history"><i class="fas fa-history"></i> محادثاتي</button>
    </div>
    <div id="chat"></div>
    <div class="input-area">
        <button class="btn-icon mic-btn" id="micBtn"><i class="fas fa-microphone"></i></button>
        <button class="plus-btn" id="plusBtn"><i class="fas fa-plus"></i></button>
        <div class="plus-options" id="plusOptions">
            <button class="option-btn camera" id="cameraBtn"><i class="fas fa-camera"></i></button>
            <button class="option-btn gallery" id="galleryBtn"><i class="fas fa-images"></i></button>
            <button class="option-btn files" id="filesBtn"><i class="fas fa-folder"></i></button>
        </div>
        <textarea id="userInput" placeholder="اكتب رسالة..." rows="1"></textarea>
        <button class="send" id="sendBtn"><i class="fas fa-arrow-left"></i></button>
    </div>
    <input type="file" id="fileInput" accept="image/*" style="display:none">
    <input type="file" id="cameraInput" accept="image/*" capture="environment" style="display:none">
    <input type="file" id="fileInputGeneric" style="display:none">
</div>
<script>
(function(){
let h=[]; let pendingImage=null;
const chat=document.getElementById('chat'), input=document.getElementById('userInput'), send=document.getElementById('sendBtn');
const menu=document.getElementById('menuToggle'), dropdown=document.getElementById('dropdown');
const plus=document.getElementById('plusBtn'), options=document.getElementById('plusOptions');
const mic=document.getElementById('micBtn'), file=document.getElementById('fileInput'), cam=document.getElementById('cameraInput'), gen=document.getElementById('fileInputGeneric');

const addMsg=(text,sender='bot',sys=false,img=null)=>{
    const el=document.createElement('div'); el.className='msg '+sender;
    if(sender==='error')el.classList.add('error');
    const tm=new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'});
    if(img){
        el.innerHTML=`<img src="${img}" class="image-upload"/><span class="file-label">${text||'صورة'}</span><span class="time"> ${tm}</span>`;
        chat.appendChild(el); chat.scrollTop=chat.scrollHeight; return;
    }
    if(sender==='bot'&&!sys){
        el.innerHTML=`<span class="typing-text"></span><span class="time"> ${tm}</span>`;
        chat.appendChild(el); chat.scrollTop=chat.scrollHeight;
        let i=0; const sp=el.querySelector('.typing-text');
        const iv=setInterval(()=>{if(i<text.length){sp.textContent+=text.charAt(i);i++;chat.scrollTop=chat.scrollHeight}else clearInterval(iv)},20);
        return;
    }
    el.innerHTML=text+` <span class="time">${tm}</span>`;
    chat.appendChild(el); chat.scrollTop=chat.scrollHeight;
};

const sendMsg=async()=>{
    const txt=input.value.trim(); if(!txt)return;
    addMsg(txt,'user'); input.value=''; input.style.height='40px';
    try{
        const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,image:null,history:h})});
        const d=await res.json();
        res.ok?addMsg(d.reply,'bot'):addMsg('خطأ: '+d.error,'error');
    }catch(e){addMsg('تعذر الاتصال.','error')}
};

input.addEventListener('keypress',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault(); sendMsg()}});
send.addEventListener('click',sendMsg);
menu.addEventListener('click',e=>{e.stopPropagation(); dropdown.classList.toggle('show')});
document.addEventListener('click',()=>{dropdown.classList.remove('show')});
document.querySelectorAll('.dropdown .item').forEach(b=>{
    b.addEventListener('click',()=>{
        dropdown.classList.remove('show');
        if(b.dataset.action==='new'){chat.innerHTML=''; h=[]; addMsg('بدأت محادثة جديدة.','bot',true)}
        else if(b.dataset.action==='history'){window.location.href='/conversations'}
    })
});
plus.addEventListener('click',()=>{plus.classList.toggle('rotate'); options.classList.toggle('show')});
document.addEventListener('click',e=>{if(!plus.contains(e.target)&&!options.contains(e.target)){options.classList.remove('show');plus.classList.remove('rotate')}});

const handleFile=(file)=>{
    const reader=new FileReader();
    reader.onload=ev=>{
        const data=ev.target.result;
        pendingImage=data;
        addMsg(file.name,'user',false,data);
        let imgs=JSON.parse(localStorage.getItem('imgs')||'[]'); imgs.push(data); localStorage.setItem('imgs',JSON.stringify(imgs));
        sendAfterMedia(data);
    };
    reader.readAsDataURL(file);
};

cam.addEventListener('change',function(){if(this.files[0])handleFile(this.files[0])});
file.addEventListener('change',function(){if(this.files[0])handleFile(this.files[0])});
gen.addEventListener('change',function(){if(this.files[0]){addMsg('📎 تم رفع: '+this.files[0].name,'user'); this.value=''}});
document.getElementById('cameraBtn').addEventListener('click',()=>{cam.click(); options.classList.remove('show');plus.classList.remove('rotate')});
document.getElementById('galleryBtn').addEventListener('click',()=>{file.click(); options.classList.remove('show');plus.classList.remove('rotate')});
document.getElementById('filesBtn').addEventListener('click',()=>{gen.click(); options.classList.remove('show');plus.classList.remove('rotate')});

const sendAfterMedia=(data)=>{
    const txt=input.value.trim(); input.value=''; input.style.height='40px';
    sendInternal(txt||"📎 ملف مرفق",data);
};
const sendInternal=async(txt,image)=>{
    try{
        const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,image:image,history:h})});
        const d=await res.json();
        res.ok?addMsg(d.reply,'bot'):addMsg('خطأ: '+d.error,'error');
    }catch(e){addMsg('تعذر الاتصال.','error')}
};

if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
    let rec=null;
    mic.addEventListener('click',function(){
        if(this.classList.contains('listening')){this.classList.remove('listening'); if(rec)rec.stop(); return}
        const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
        rec=new SR(); rec.lang='ar-SA'; rec.continuous=false; rec.interimResults=false;
        this.classList.add('listening'); addMsg('جاري الاستماع...','bot',true);
        rec.onresult=e=>{input.value=e.results[0][0].transcript; this.classList.remove('listening'); setTimeout(sendMsg,300)};
        rec.onerror=()=>{this.classList.remove('listening')};
        rec.start();
    });
}
})();
</script>
</body>
</html>
"""

# ==================== المسارات ====================

@app.route('/')
@login_required
def index():
    resume_id = request.args.get('resume')
    if resume_id:
        session['resume_id'] = resume_id
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat')
@login_required
def chat_page():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if check_password(email, password):
            user = get_user_by_email(email)
            login_user(user)
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error="❌ بريد أو كلمة مرور خاطئة")
    return render_template_string(LOGIN_HTML, error="")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        if get_user_by_email(email):
            return render_template_string(REGISTER_HTML, error="❌ البريد موجود مسبقاً")
        create_user(email, password, name)
        return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML, error="")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        image_data = data.get("image", None)

        if not user_message and not image_data:
            return jsonify({"reply": "اكتب شيء أساعدك فيه"})

        add_message(current_user.id, "user", user_message)
        chat_history = get_history(current_user.id, limit=10)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for entry in chat_history:
            messages.append({"role": entry["role"], "content": entry["content"]})

        if image_data:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message or "حلل هذه الصورة باللهجة العامية"},
                    {"type": "image_url", "image_url": {"url": image_data}}
                ]
            })

        if any(word in user_message for word in ["أخبار", "اليوم", "الآن", "جديد", "تحديث", "آخر", "حدث", "وقت", "الساعة"]):
            try:
                print(f"🔍 محاولة البحث بالويب عن: {user_message}")
                search_response = client.responses.create(
                    model="gpt-4o-mini",
                    instructions=f"{SYSTEM_PROMPT}\n\nسياق المحادثة السابقة: {chat_history}",
                    input=f"ابحث في الويب عن أحدث المعلومات حول: {user_message}، وقدم لي ملخصاً مفيداً.",
                    tools=[{"type": "web_search"}],
                    temperature=0.7,
                    max_output_tokens=800
                )
                search_result = search_response.output_text.strip()
                if search_result:
                    messages.append({
                        "role": "user",
                        "content": f"نتيجة البحث عن '{user_message}':\n{search_result}\n\nاستخدم هذه المعلومات في ردك."
                    })
                    print("✅ تم الحصول على نتائج البحث.")
            except Exception as e:
                print(f"⚠️ فشل البحث بالويب: {e}")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip()
        if not reply:
            reply = "ما قدرت أجيب لك رد، حاول مرة أخرى."

        add_message(current_user.id, "assistant", reply)

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"❌ خطأ في /chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/conversations')
@login_required
def view_conversations():
    try:
        user_id = str(current_user.id)
        rows = fetch_all(
            "SELECT id, role, content, created_at FROM conversations WHERE user_id = %s ORDER BY created_at ASC",
            (user_id,)
        )

        if not rows:
            return "<h2 style='text-align:center;margin-top:50px;'>📭 لا توجد محادثات حتى الآن.</h2>"

        chapters = []
        current_chapter = []
        for row in rows:
            if row[1] == 'user' and len(current_chapter) >= 8:
                chapters.append(current_chapter)
                current_chapter = [row]
            else:
                current_chapter.append(row)
        if current_chapter:
            chapters.append(current_chapter)

        html = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>محادثاتي - نبراس</title>
            <style>
                body{background:#f5f7fa;padding:20px;font-family:'Segoe UI',Arial,sans-serif}
                .back{display:inline-block;margin-bottom:20px;padding:8px 16px;background:#4a6a8a;color:white;text-decoration:none;border-radius:8px}
                .back:hover{background:#3a5a7a}
                .chapter{background:white;border-radius:12px;margin-bottom:12px;box-shadow:0 2px 10px rgba(0,0,0,0.05);overflow:hidden}
                .chapter-header{
                    padding:14px 20px;
                    background:#f8f9fa;
                    cursor:pointer;
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    border-bottom:1px solid #eaeef2;
                    transition:background 0.2s;
                }
                .chapter-header:hover{background:#eef2f7}
                .chapter-header h3{
                    margin:0;
                    font-size:18px;
                    color:#1a2b3c;
                }
                .chapter-header .arrow{
                    transition:transform 0.3s;
                    font-size:20px;
                }
                .chapter-body{
                    padding:0 20px;
                    max-height:0;
                    overflow:hidden;
                    transition:max-height 0.4s ease, padding 0.3s ease;
                }
                .chapter-body.open{
                    max-height:2000px;
                    padding:15px 20px;
                }
                .msg-item{
                    display:flex;
                    gap:10px;
                    padding:6px 0;
                    border-bottom:1px solid #f0f2f5;
                }
                .msg-item:last-child{border-bottom:none}
                .msg-role{font-weight:bold;min-width:60px}
                .msg-role.user{color:#2d7d46}
                .msg-role.bot{color:#4a6a8a}
                .msg-content{flex:1;word-break:break-word}
                .msg-time{font-size:12px;color:#999;min-width:80px;text-align:left}
                .actions{margin-top:10px;display:flex;gap:10px}
                .actions a{
                    background:#4a6a8a;color:white;padding:5px 14px;
                    border-radius:20px;text-decoration:none;font-size:14px;
                }
                .actions a:hover{background:#3a5a7a}
            </style>
        </head>
        <body>
            <a href="/" class="back">⬅ العودة للرئيسية</a>
            <h1>📋 محادثاتي</h1>
            <div id="chapters-container">
        """

        for idx, chapter in enumerate(chapters, 1):
            title = f"المبحث {idx}"
            for row in chapter:
                if row[1] == 'user':
                    first_msg = row[2][:40]
                    title = f"المبحث {idx}: {first_msg}"
                    break

            msgs_html = ""
            for row in chapter:
                role_display = '👤 مستخدم' if row[1] == 'user' else '🤖 نبراس'
                role_class = 'user' if row[1] == 'user' else 'bot'
                msgs_html += f"""
                <div class="msg-item">
                    <span class="msg-role {role_class}">{role_display}</span>
                    <span class="msg-content">{row[2][:300]}</span>
                    <span class="msg-time">{row[3]}</span>
                </div>
                """

            first_id = chapter[0][0]
            html += f"""
            <div class="chapter">
                <div class="chapter-header" onclick="toggleChapter(this)">
                    <h3>{title}</h3>
                    <span class="arrow">▼</span>
                </div>
                <div class="chapter-body">
                    {msgs_html}
                    <div class="actions">
                        <a href="/?resume={first_id}">▶️ مواصلة المحادثة</a>
                        <a href="/export" style="background:#2d7d46;">📥 تصدير المحادثات</a>
                    </div>
                </div>
            </div>
            """

        html += """
            </div>
            <script>
                function toggleChapter(header) {
                    var body = header.nextElementSibling;
                    var arrow = header.querySelector('.arrow');
                    if (body.classList.contains('open')) {
                        body.classList.remove('open');
                        arrow.textContent = '▼';
                    } else {
                        body.classList.add('open');
                        arrow.textContent = '▲';
                    }
                }
                document.addEventListener('DOMContentLoaded', function() {
                    var firstChapter = document.querySelector('.chapter-header');
                    if (firstChapter) {
                        toggleChapter(firstChapter);
                    }
                });
            </script>
        </body>
        </html>
        """
        return html

    except Exception as e:
        print(f"❌ خطأ في /conversations: {e}")
        return f"<h2 style='text-align:center;margin-top:50px;color:#c33;'>⚠️ حدث خطأ: {str(e)}</h2>", 500

# ==================== مسار التصدير (الجديد) ====================

@app.route('/export')
@login_required
def export_conversations():
    user_id = str(current_user.id)
    rows = fetch_all(
        "SELECT role, content, created_at FROM conversations WHERE user_id = %s ORDER BY created_at ASC",
        (user_id,)
    )

    data = []
    for row in rows:
        data.append({
            "role": row[0],
            "content": row[1],
            "time": row[2].isoformat() if row[2] else None
        })

    json_data = json.dumps(data, ensure_ascii=False, indent=2)

    return Response(
        json_data,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=memory_{current_user.id}.json'}
    )

# ==================== تشغيل التطبيق ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
