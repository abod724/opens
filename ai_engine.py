import openai
from config import Config
import os

# تحقق من وجود المفتاح
if not Config.OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY is not set in Environment Variables!")
else:
    openai.api_key = Config.OPENAI_API_KEY
    print("✅ OpenAI API Key loaded.")

def load_knowledge():
    try:
        with open('Knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

KNOWLEDGE_BASE = load_knowledge()

def get_ai_response(user_message, conversation_history=[]):
    if not Config.OPENAI_API_KEY:
        return "⚠️ مفتاح API الخاص بالذكاء الاصطناعي غير مضبوط. راجع إعدادات Render."

    messages = [
        {"role": "system", "content": f"أنت مساعد ذكي اسمه نيراس. معلوماتك: {KNOWLEDGE_BASE}"}
    ]
    for entry in conversation_history:
        messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    messages.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return f"⚠️ مشكلة في الذكاء الاصطناعي: {str(e)}"
