import openai
from config import Config

if not Config.OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY is not set!")
else:
    openai.api_key = Config.OPENAI_API_KEY
    print("✅ OpenAI API Key loaded.")

def load_knowledge():
    """قراءة ملف المعرفة الثابت"""
    try:
        with open('Knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

KNOWLEDGE_BASE = load_knowledge()

def get_ai_response(user_message, conversation_history=[]):
    if not Config.OPENAI_API_KEY:
        return "⚠️ مفتاح API غير مضبوط."

    # بناء التعليمات الأساسية (System Prompt) حسب طلبك
    if KNOWLEDGE_BASE:
        system_content = f"""
أنت مساعد ذكي اسمك "نيراس". مهمتك الأساسية: التحدث باللهجة السعودية العامية البيضاء (خفيفة، واضحة، مثل: "كيف الحال؟"، "وش أخبارك؟"، "تمام يا عزيزي"، "طيب بس كذا").

📁 **ملف المعرفة (خاص بالسوالف العامة):**
المعلومات التالية هي قاعدة معرفتك الأساسية للمواضيع العامة والتعريف بنفسك:
"{KNOWLEDGE_BASE}"

🎯 **قواعد الرد بدقة:**
1. إذا سألك المستخدم عن **موضوع عام، أو سوالف، أو تعريف بك، أو أي شيء موجود في ملف المعرفة**، اعتمد على ملف المعرفة فقط في ردك ولا تخرج عنه.
2. إذا سألك المستخدم عن **أخبار حديثة، أحداث جارية، تقنيات جديدة، أو معلومات حديثة العهد** (مثل مباراة الأمس أو إصدار جديد)، استخدم معرفتك العامة المخزنة في ذاكرتك (OpenAI) لتزويده بالمعلومة مع الحفاظ على اللهجة السعودية.
3. إذا كان السؤال عاماً ولم تجد له ذكراً في ملف المعرفة، استخدم معرفتك العامة.

⚠️ **انتبه**: لا تختلق معلومات غير موجودة في ملف المعرفة إذا كان السؤال عن السوالف العامة، قل "ما عندي معلومة عن هالشي" بكل صراحة.
"""
    else:
        # إذا كان ملف المعرفة فارغ، يصبح مساعد عام بلهجة سعودية
        system_content = "أنت مساعد ذكي اسمه نيراس. تحدث باللهجة السعودية العامية البيضاء. جاوب على أي سؤال باستخدام معرفتك العامة."

    # بناء سياق المحادثة (الذاكرة)
    messages = [{"role": "system", "content": system_content}]
    for entry in conversation_history:
        messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['bot']})
    messages.append({"role": "user", "content": user_message})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=800,
            temperature=0.8  # زيادة الإبداع شوي عشان اللهجة تطلع طبيعية
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return f"⚠️ عطل تقني: {str(e)}"
