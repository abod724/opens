import openai
from config import Config
import os

openai.api_key = Config.OPENAI_API_KEY

# تحميل المعرفة الثابتة من ملف Knowledge.txt (إن وجد)
def load_knowledge():
    try:
        with open('Knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

KNOWLEDGE_BASE = load_knowledge()

def get_ai_response(user_message, conversation_history=[]):
    """
    إرسال رسالة المستخدم + سياق المحادثة + المعرفة الثابتة إلى OpenAI
    """
    # بناء السياق للمساعد
    messages = [
        {"role": "system", "content": f"أنت مساعد ذكي اسمك نيراس. إليك بعض المعلومات الأساسية: {KNOWLEDGE_BASE}"}
    ]
    # إضافة محادثات سابقة (للحفاظ على السياق)
    for entry in conversation_history:
        messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    
    # إضافة الرسالة الحالية
    messages.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # أو gpt-4 حسب اشتراكك
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # تسجيل الخطأ لظهوره في سجلات Render
        print(f"OpenAI API Error: {e}")
        return f"حدث خطأ في الذكاء الاصطناعي: {str(e)}"
