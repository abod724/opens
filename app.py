from flask import Flask, request, jsonify, render_template_string
from google import genai
import os
import requests

app = Flask(__name__)

# ================= الإعدادات =================
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise Exception("GOOGLE_API_KEY مفقود")

client = genai.Client(api_key=API_KEY)

# ================= ملف المعرفة =================
knowledge = ""
for f in ["Knowledge.md", "knowledge.md", "معرفة.md", "README.md"]:
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as file:
            knowledge = file.read()
        break

SYSTEM_PROMPT = f"""
أنت نبراس، مساعد ذكي باللهجة العامية.
مصادرك: 1. ملف المعرفة (أدناه). 2. معرفتك العامة. 3. البحث بالويب للحديث.
ملف المعرفة:
{knowledge or "لا يوجد محتوى خاص."}
"""

# ================= البحث الاختياري =================
def search_web(query):
    engine_id = os.environ.get("CUSTOM_SEARCH_ENGINE_ID")
    if not engine_id:
        return None
    try:
        url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={engine_id}&q={query}"
        res = requests.get(url, timeout=5).json()
        if "items" in res:
            return "\n".join([f"• {i['title']}: {i['link']}" for i in res["items"][:3]])
    except:
        return None
    return None

# ================= الواجهة =================
HTML = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>نبراس</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif}
body{background:#fff;height:100dvh;display:flex;justify-content:center;align-items:center}
.app{width:100%;max-width:450px;height:100dvh;display:flex;flex-direction:column;background:#fff}
.header{display:flex;justify-content:flex-end;padding:14px 18px;border-bottom:1px solid #eaeef2}
.header .menu-btn{background:none;border:none;font-size:22px;color:#5a6b7c;cursor:pointer}
.dropdown{display:none;position:absolute;top:64px;left:14px;right:14px;background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,0.08);z-index:100;border:1px solid #eaedf2}
.dropdown.show{display:flex;flex-direction:column}
.dropdown .item{display:flex;align-items:center;gap:12px;padding:14px 18px;font-size:15px;background:none;border:none;width:100%;text-align:right;cursor:pointer;border-bottom:1px solid #f0f2f5}
.dropdown .item:last-child{border-bottom:none}
#chat{flex:1;overflow-y:auto;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:80%;padding:10px 16px;border-radius:20px;font-size:18px;line-height:1.6;word-wrap:break-word;white-space:pre-wrap}
.msg.user{align-self:flex-end;background:#eef2f7;border-bottom-left-radius:6px}
.msg.bot{align-self:flex-start;background:#fff;border-bottom-right-radius:6px}
.msg .time{font-size:9px;opacity:0.35;display:block;margin-top:4px}
.msg.error{background:#fde8e8;color:#a33;align-self:center;max-width:90%}
.msg .image-upload{max-width:100%;max-height:200px;border-radius:12px;margin:4px 0;border:1px solid #ddd;display:block}
.input-area{display:flex;align-items:flex-end;gap:6px;padding:6px 12px;margin:8px 14px 16px;background:#f5f7fa;border-radius:40px;border:1px solid #dce1e8}
.input-area textarea{flex:1;border:none;background:transparent;padding:12px 4px;font-size:17px;outline:none;color:#1a2b3c;direction:rtl;resize:none;overflow:hidden;min-height:40px;max-height:120px;font-family:'Segoe UI',Arial,sans-serif}
.input-area .send{background:#4a6a8a;color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.input-area .btn-icon{background:none;border:none;color:#6a7b8c;font-size:20px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center}
.input-area .mic-btn.listening{color:#c33;background:#fde8e8}
.plus-btn{background:none;border:none;color:#4a6a8a;font-size:24px;cursor:pointer;padding:4px;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center}
.plus-options{display:none;position:absolute;bottom:70px;right:0;background:#fff;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.12);padding:12px;gap:8px;flex-direction:row;border:1px solid #eaeef2;z-index:50}
.plus-options.show{display:flex}
.plus-options .option-btn{background:#f5f7fa;border:none;border-radius:50%;width:52px;height:52px;display:flex;align-items:center;justify-content:center;font-size:22px;color:#1a2b3c;cursor:pointer}
</style></head>
<body>
<div class="app">
<div class="header"><button class="menu-btn" id="menuToggle"><i class="fas fa-ellipsis-v"></i></button></div>
<div class="dropdown" id="dropdown">
<button class="item" data-action="new"><i class="fas fa-plus-circle"></i> محادثة جديدة</button>
<button class="item" data-action="library"><i class="fas fa-layer-group"></i> المكتبة</button>
<button class="item" data-action="history"><i class="fas fa-history"></i> المحادثات السابقة</button>
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
</body></html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    history = data.get("history", [])
    
    # بناء السياق
    ctx = SYSTEM_PROMPT + "\n"
    for msg in history[-10:]:
        ctx += f"{msg['role']}: {msg['content']}\n"
    
    # بحث ويب احتياطي (إذا كان السؤال حديثاً)
    if any(k in user_msg for k in ["أخبار", "اليوم", "الآن", "جديد"]):
        search_res = search_web(user_msg)
        if search_res:
            ctx += f"\nنتيجة البحث:\n{search_res}\n"

    ctx += f"\nالمستخدم: {user_msg}\nنبراس:"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=ctx
        )
        reply = response.text.strip() or "ما قدرت أجيب رد."
    except Exception as e:
        print(e)
        reply = "حدث خطأ في Gemini."

    return jsonify({"reply": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
