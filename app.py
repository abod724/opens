from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
import os
import requests

app = Flask(__name__)

# قراءة المفتاح من متغيرات البيئة
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise Exception("❌ المفتاح غير موجود")

client = OpenAI(api_key=API_KEY)

# قراءة ملف المعرفة
KNOWLEDGE_FILE = "Knowledge.md"
knowledge_content = ""
if os.path.exists(KNOWLEDGE_FILE):
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            knowledge_content = f.read()
    except:
        knowledge_content = ""

# دالة البحث في الويب
def search_web(query):
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "t": "nibras", "kl": "ar-sa"}
        res = requests.get(url, params=params, timeout=10).json()
        return res.get("AbstractText") or None
    except:
        return None

# إعدادات شخصية نبراس
SYSTEM_PROMPT = f"""
أنت "نبراس"، مساعد مخصص لأهل السعودية والخليج، متخصص في تربية الحلال والطيور والمقانيص والبر.
تحدث باللهجة السعودية العامية الواضحة، جمل قصيرة ومباشرة، لا تطيل ولا تتفلسف.
إذا كان السؤال عن معلومات حديثة، أسعار، مواعيد، أخبار، أو شيء لم تكن تعرفه، قم بالبحث تلقائياً وأجب بالصحيح.
اجعل ردودك طبيعية كإنسان، ورحب وتفاعل بود. لا تذكر المصادر إلا إذا طلب منك.

معلوماتك الخاصة:
{knowledge_content}
"""

# الواجهة
@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>نبراس</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:Arial,sans-serif}
        html,body{height:100%;overflow:hidden;background:#fff}
        .app{width:100%;height:100vh;display:flex;flex-direction:column}
        .header{position:sticky;top:0;z-index:999;display:flex;justify-content:flex-end;padding:12px 16px;border-bottom:1px solid #eee}
        .menu-btn{border:none;background:none;font-size:18px;color:#333;cursor:pointer;padding:6px}
        .dropdown{position:absolute;top:50px;left:12px;right:12px;background:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.1);display:none;flex-direction:column;z-index:1000;border:1px solid #eee}
        .dropdown.show{display:flex}
        .dropdown .item{padding:12px 16px;font-size:14px;color:#333;border:none;background:none;text-align:right;cursor:pointer;border-bottom:1px solid #f5f5f5}
        .dropdown .item:last-child{border-bottom:none}
        #chat{flex:1;overflow-y:auto;padding:12px}
        .msg{max-width:80%;padding:10px 14px;border-radius:18px;font-size:15px;margin-bottom:8px;position:relative}
        .msg.user{align-self:flex-end;background:#f0f0f0;border-bottom-left-radius:6px}
        .msg.bot{align-self:flex-start;background:#f8f8f8;border-bottom-right-radius:6px}
        .time{font-size:10px;color:#999;margin-top:4px;display:block}
        .speak-btn{position:absolute;left:8px;bottom:4px;border:none;background:none;color:#888;font-size:14px;cursor:pointer;padding:2px}
        .input-area{display:flex;align-items:center;gap:6px;padding:8px 12px;margin:8px;background:#f9f9f9;border-radius:30px;border:1px solid #eee;position:sticky;bottom:0}
        .input-area input{flex:1;border:none;background:transparent;padding:10px;font-size:15px;outline:none}
        .btn-icon{border:none;background:none;color:#666;font-size:18px;cursor:pointer}
        .send{background:#333;color:white;border:none;width:36px;height:36px;border-radius:50%;cursor:pointer}
    </style>
</head>
<body>
<div class="app">
    <div class="header"><button class="menu-btn" id="menu"><i class="fas fa-ellipsis-v"></i></button></div>
    <div class="dropdown" id="list">
        <button class="item" data-click="new"><i class="fas fa-plus"></i> محادثة جديدة</button>
        <button class="item" data-click="history"><i class="fas fa-clock"></i> السابقة</button>
    </div>
    <div id="chat"></div>
    <div class="input-area">
        <button class="btn-icon" id="mic"><i class="fas fa-microphone"></i></button>
        <input type="text" id="txt" placeholder="اكتب رسالتك..." />
        <button class="send" id="go"><i class="fas fa-paper-plane"></i></button>
    </div>
</div>
<script>
function speak(t){if('speechSynthesis'in window){let u=new SpeechSynthesisUtterance(t);u.lang='ar-SA';u.rate=0.9;speechSynthesis.speak(u);}}
function addMsg(tp,txt){let d=document.createElement('div');d.className='msg '+tp;d.innerHTML=txt+`<span class="time">${new Date().toLocaleTimeString('ar-SA',{hour:'2-digit',minute:'2-digit'})}</span>`;if(tp==='bot'){let b=document.createElement('button');b.className='speak-btn';b.innerHTML='<i class="fas fa-volume-up"></i>';b.title='استمع';b.onclick=()=>speak(txt);d.appendChild(b);}chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
document.getElementById('menu').onclick=()=>document.getElementById('list').classList.toggle('show');
document.addEventListener('click',e=>{if(!e.target.closest('.header')&&!e.target.closest('.dropdown'))document.getElementById('list').classList.remove('show');});
document.querySelectorAll('.item').forEach(b=>{b.onclick=()=>{document.getElementById('list').classList.remove('show');if(b.dataset.click==='new')chat.innerHTML=''}});
let rec=null;document.getElementById('mic').onclick=function(){if(!('webkitSpeechRecognition'in window))return;if(rec){rec.stop();this.classList.remove('on');return;}rec=new webkitSpeechRecognition();rec.lang='ar-SA';rec.onresult=e=>{txt.value=e.results[0][0].transcript;this.classList.remove('on');go.click()};this.classList.add('on');rec.start();};
document.getElementById('go').onclick=send;document.getElementById('txt').onkeydown=e=>e.key==='Enter'&&send();
async function send(){let t=txt.value.trim();if(!t)return;addMsg('user',t);txt.value='';try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t})});let d=await r.json();addMsg('bot',d.reply||'تم الاستلام')}catch{addMsg('bot','تعذر الاتصال')}}
</script>
</body>
</html>
    ''')

# نقطة استقبال الرسائل
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg = data.get("message", "").strip()
    if not msg: return jsonify({"reply": "اكتب رسالتك"}),400

    # تحديد الحاجة للبحث
    need_search = any(w in msg.lower() for w in ["متى","كم سعر","اسعار","احدث","اخبار","نتيجة","موسم","سنة","تاريخ","اليوم"])
    search_res = search_web(msg) if need_search else ""
    full_prompt = f"{SYSTEM_PROMPT}\n\nالسؤال: {msg}\n\nمعلومات حديثة: {search_res or 'لا يوجد'}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":full_prompt},{"role":"user","content":msg}],
        temperature=0.7
    )
    return jsonify({"reply": res.choices[0].message.content.strip()})

if __name__ == '__main__': app.run(debug=False)
