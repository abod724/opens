import openai
from config import Config
from datetime import datetime

if not Config.OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY is not set!")
else:
    openai.api_key = Config.OPENAI_API_KEY
    print("OpenAI API Key loaded.")

def load_knowledge():
    try:
        with open('Knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

KNOWLEDGE_BASE = load_knowledge()

def get_ai_response(user_message, conversation_history=[]):
    if not Config.OPENAI_API_KEY:
        return "مفتاح API غير مضبوط."

    today_date = datetime.now().strftime("%Y-%m-%d")

    if KNOWLEDGE_BASE:
        system_content = f"""
أنت مساعد ذكي اسمك نيراس. تتحدث باللهجة السعودية العامية البيضاء.

ملف المعرفة الخاص بالسوالف العامة:
{KNOWLEDGE_BASE}

قواعد الرد:
1. إذا سألك عن مواضيع عامة أو سوالف، استخدم ملف المعرفة.
2. إذا سألك عن أخبار حديثة أو تقنيات جديدة، استخدم معرفتك العامة.
3. التاريخ الحقيقي لهذا اليوم هو {today_date}.
"""
    else:
        system_content = f"أنت مساعد ذكي اسمه نيراس. تحدث باللهجة السعودية. التاريخ الحقيقي هو {today_date}."

    messages = [{"role": "system", "content": system_content}]
    
    for entry in conversation_history:
        messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    
    messages.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return f"عطل تقني: {str(e)}"
