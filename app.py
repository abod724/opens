from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import init_db, fetch_all
from auth import User, get_user_by_id, get_user_by_email, create_user, check_password
from memory import add_message, get_history, clear_memory
import openai
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret-key-change-in-production")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

init_db()

API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("OPENAI_API_KEY مفقود")
client = openai.OpenAI(api_key=API_KEY)

SYSTEM_PROMPT = """
أنت "نبراس"، مساعد ذكي باللهجة السعودية البيضاء.
مصادرك: معرفتك العامة + البحث بالويب للأسئلة الحديثة.
لا تذكر أي مصدر محدد.
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>دخول - نبراس</title>
<style>body{background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;font-family:'Segoe UI',Arial,sans-serif}.box{background:white;padding:40px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.08);width:340px;text-align:center}h2{color:#1a2b3c}input{width:100%;padding:12px;border:1px solid #dce1e8;border-radius:10px;font-size:16px;margin:8px 0;text-align:center}button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:10px;font-size:18px;cursor:pointer}button:hover{background:#3a5a7a}.error{color:#c33;margin:8px 0}a{color:#4a6a8a;text-decoration:none;display:block;margin-top:10px}
</style></head>
<body><div class="box">
<h2>🔐 دخول نبراس</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST"><input type="email" name="email" placeholder="البريد الإلكتروني" required><input type="password" name="password" placeholder="كلمة المرور" required><button type="submit">دخول</button></form>
<a href="{{ url_for('register') }}">ليس لديك حساب؟ سجل الآن</a>
</div></body></html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>تسجيل - نبراس</title>
<style>body{background:#f5f7fa;display:flex;justify-content:center;align-items:center;height:100vh;font-family:'Segoe UI',Arial,sans-serif}.box{background:white;padding:40px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.08);width:340px;text-align:center}h2{color:#1a2b3c}input{width:100%;padding:12px;border:1px solid #dce1e8;border-radius:10px;font-size:16px;margin:8px 0;text-align:center}button{width:100%;padding:12px;background:#4a6a8a;color:white;border:none;border-radius:10px;font-size:18px;cursor:pointer}button:hover{background:#3a5a7a}.error{color:#c33;margin:8px 0}a{color:#4a6a8a;text-decoration:none;display:block;margin-top:10px}
</style></head>
<body><div class="box">
<h2>📝 حساب جديد</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST"><input type="text" name="name" placeholder="الاسم الكامل" required><input type="email" name="email" placeholder="البريد الإلكتروني" required><input type="password" name="password" placeholder="كلمة المرور" required><button type="submit">تسجيل</button></form>
<a href="{{ url_for('login') }}">لديك حساب؟ سجل دخول</a>
</div></body></html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>نبراس</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif}
body{background:#fff;height:100dvh;display:flex;justify-content:center;align-items:center}
.app{width:100%;max-width:450px;height:100dvh;display:flex;flex-direction:column;background:#fff}
.header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid #eaeef2}
.header .menu-btn{background:none;border:none;font-size:22px;color:#5a6b7c;cursor:padding:4px}
.header .logout-btn{background:#e74c3c;color:#fff;border:none;padding:6px 14px;border-radius:30px;cursor:pointer;font-size:14px}
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
.input-area textarea{flex:1;border:none;background:transparent;padding:12px 4px;font-size:17px;outline:none;color:#1a2b3c;direction:rtl;resize:none;overflow:hidden;min-height:40px;max-height:120px}
.input-area .send{background:#4a6a8a;color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.input-area .btn-icon{background:none;border:none;color:#6a7b8c;font-size:20px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center}
.input-area .mic-btn.listening{color:#c33;background:#fde8e8}
.plus-btn{background:none;border:none;color:#4a6a8a;font-size:24px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px}
.plus-options{display:none;position:absolute;bottom:70px;right:0;background:#fff;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.12);padding:12px;gap:8px;flex-direction:row;border:1px solid #eaeef2;z-index:50}
.plus-options.show{display:flex}
.plus-options .option-btn{background:#f5f7fa;border:none;border-radius:50%;width:52px;height:52px;font-size:22px;color:#1a2b3c;cursor:pointer}
</style></head>
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
let h=[]; let img=null; const c=document.getElementById('chat'), u=document.getElementById('userInput'), s=document.getElementById('sendBtn');
const m=document.getElementById('menuToggle'), d=document.getElementById('dropdown');
const p=document.getElementById('plusBtn'), o=document.getElementById('plusOptions');
const mic=document.getElementById('micBtn'), fi=document.getElementById('fileInput'), ci=document.getElementById('cameraInput'), fg=document.getElementById('fileInputGeneric');
const ac=(t,sender='bot',sys=false,id=null)=>{
const el=document.createElement('div'); el.className='msg '+sender; if(sender==='error')el.classList.add('error');
const tm=new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'});
if(id){el.innerHTML=`<img src="${id}" class="image-upload"/><span class="file-label">${t||'صورة'}</span><span class="time"> ${tm}</span>`;c.appendChild(el);c.scrollTop=c.scrollHeight;return}
if(sender==='bot'&&!sys){el.innerHTML=`<span class="typing-text"></span><span class="time"> ${tm}</span>`;c.appendChild(el);c.scrollTop=c.scrollHeight;let i=0;const sp=el.querySelector('.typing-text');const iv=setInterval(()=>{if(i<t.length){sp.textContent+=t.charAt(i);i++;c.scrollTop=c.scrollHeight}else clearInterval(iv)},20);return}
el.innerHTML=t+` <span class="time">${tm}</span>`;c.appendChild(el);c.scrollTop=c.scrollHeight;
}
const send=async()=>{const txt=u.value.trim(); if(!txt)return; ac(txt,'user'); u.value=''; u.style.height='40px'; try{const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,image:null,history:h})});const d=await res.json();res.ok?ac(d.reply,'bot'):ac('خطأ: '+d.error,'error');}catch(e){ac('تعذر الاتصال.','error')}}
u.addEventListener('keypress',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault(); send()}});
s.addEventListener('click',send);
m.addEventListener('click',e=>{e.stopPropagation(); d.classList.toggle('show')});
document.addEventListener('click',()=>{d.classList.remove('show')});
document.querySelectorAll('.dropdown .item').forEach(b=>{b.addEventListener('click',()=>{d.classList.remove('show'); if(b.dataset.action==='new'){c.innerHTML=''; h=[]; ac('بدأت محادثة جديدة.','bot',true)}})});
p.addEventListener('click',()=>{p.classList.toggle('rotate'); o.classList.toggle('show')});
document.addEventListener('click',e=>{if(!p.contains(e.target)&&!o.contains(e.target)){o.classList.remove('show');p.classList.remove('rotate')}});
ci.addEventListener('change',function(e){if(this.files[0]){const r=new FileReader(); r.onload=ev=>{ac(this.files[0].name,'user',false,ev.target.result); const imgs=JSON.parse(localStorage.getItem('imgs')||'[]'); imgs.push(ev.target.result); localStorage.setItem('imgs',JSON.stringify(imgs)); sendAfterMedia(ev.target.result)}; r.readAsDataURL(this.files[0])}});
fi.addEventListener('change',function(e){if(this.files[0]){const r=new FileReader(); r.onload=ev=>{ac(this.files[0].name,'user',false,ev.target.result); const imgs=JSON.parse(localStorage.getItem('imgs')||'[]'); imgs.push(ev.target.result); localStorage.setItem('imgs',JSON.stringify(imgs)); sendAfterMedia(ev.target.result)}; r.readAsDataURL(this.files[0])}});
fg.addEventListener('change',function(e){if(this.files[0]){ac('📎 تم رفع: '+this.files[0].name,'user'); this.value=''}});
document.getElementById('cameraBtn').addEventListener('click',()=>{ci.click(); o.classList.remove('show');p.classList.remove('rotate')});
document.getElementById('galleryBtn').addEventListener('click',()=>{fi.click(); o.classList.remove('show');p.classList.remove('rotate')});
document.getElementById('filesBtn').addEventListener('click',()=>{fg.click(); o.classList.remove('show');p.classList.remove('rotate')});
let sendMedia=null; function sendAfterMedia(data){sendMedia=data; const txt=u.value.trim(); u.value=''; u.style.height='40px'; sendInternal(txt||"📎 ملف مرفق",data)} async function sendInternal(txt,image){try{const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt,image:image,history:h})});const d=await res.json();res.ok?ac(d.reply,'bot'):ac('خطأ: '+d.error,'error');}catch(e){ac('تعذر الاتصال.','error')}}
if('webkitSpeechRecognition'in window||'SpeechRecognition'in window){let rec=null; mic.addEventListener('click',function(){if(this.classList.contains('listening')){this.classList.remove('listening'); if(rec)rec.stop(); return}const SR=window.SpeechRecognition||window.webkitSpeechRecognition; rec=new SR(); rec.lang='ar-SA'; rec.continuous=false; rec.interimResults=false; this.classList.add('listening'); ac('جاري الاستماع...','bot',true); rec.onresult=e=>{u.value=e.results[0][0].transcript; this.classList.remove('listening'); setTimeout(send,300)}; rec.onerror=()=>{this.classList.remove('listening')}; rec.start()})}
})();
</script>
</body></html>
"""

@app.route('/')
@login_required
def index():
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
    data = request.get_json()
    user_message = data.get("message", "").strip()
    image_data = data.get("image", None)
    
    if not user_message and not image_data:
        return jsonify({"reply": "اكتب شي"})
    
    add_message(current_user.id, "user", user_message)
    chat_history = get_history(current_user.id, limit=10)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for entry in chat_history:
        messages.append({"role": entry["role"], "content": entry["content"]})
    
    if image_data:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_message or "حلل هذه الصورة"},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
        })
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )
        reply = response.choices[0].message.content.strip() or "ما قدرت أجيب رد."
    except Exception as e:
        print(e)
        reply = "حدث خطأ، حاول مرة أخرى."
    
    add_message(current_user.id, "assistant", reply)
    return jsonify({"reply": reply})

@app.route('/conversations')
@login_required
def view_conversations():
    rows = fetch_all(
        "SELECT id, role, content, created_at FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
        (current_user.id,)
    )
    html = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>محادثاتي</title>
    <style>body{background:#f5f7fa;padding:20px;font-family:'Segoe UI',Arial,sans-serif}
    table{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.05)}
    th{background:#4a6a8a;color:white;padding:12px;text-align:right}
    td{padding:10px 12px;border-bottom:1px solid #eaeef2}
    tr:hover{background:#f8f9fa}
    .role-user{color:#2d7d46;font-weight:bold}
    .role-assistant{color:#4a6a8a;font-weight:bold}
    .content{max-width:300px;white-space:pre-wrap;word-break:break-word}
    .time{font-size:12px;color:#999}
    .back{display:inline-block;margin-bottom:15px;padding:8px 16px;background:#4a6a8a;color:white;text-decoration:none;border-radius:8px}
    .back:hover{background:#3a5a7a}
    </style></head>
    <body>
    <a href="/" class="back">⬅ العودة</a>
    <h1>📋 محادثاتي</h1>
    <table>
        <tr><th>#</th><th>الدور</th><th>المحتوى</th><th>التاريخ</th></tr>
    """
    for row in rows:
        role_display = '👤 مستخدم' if row[1] == 'user' else '🤖 نبراس'
        html += f"<tr><td>{row[0]}</td><td class='role-{row[1]}'>{role_display}</td><td class='content'>{row[2][:200]}</td><td class='time'>{row[3]}</td></tr>"
    html += "</table></body></html>"
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
