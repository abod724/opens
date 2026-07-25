import openai
import requests
from config import Config

openai.api_key = Config.OPENAI_API_KEY

def load_knowledge():
    try:
        with open("knowledge.md", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def web_search(query):
    if not Config.BING_API_KEY:
        return None

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": Config.BING_API_KEY}
    params = {"q": query, "mkt": "ar-SA"}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10).json()
        if "webPages" in res:
            return res["webPages"]["value"][0]["snippet"]
    except:
        return None

def chat_with_myais(messages):
    system_prompt = """
أنت نبراس، مساعد ذكي متكامل.
تحدث باللهجة السعودية العامية البيضاء، اجعل ردودك طبيعية كإنسان، قصيرة ومباشرة.
لا تطيل ولا تتفلسف، وتفاعل مع المستخدم بكل ود واحترام.
إذا سألك عن معلومات حديثة أو أحداث جارية، استخدم البحث لجلبها دقيقة.
إذا سألك عن نفسك: أنا نبراس، مساعدك الذكي، تم تطويري وبرمجتي على يد مطورين باستخدام أحدث التقنيات، وأنا هنا لمساعدتك في كل ما تحتاج.
"""

    knowledge = load_knowledge()
    full_system = system_prompt + "\n\n--- معلومات إضافية ---\n" + knowledge

    last_user_msg = messages[-1]["content"]
    web_result = web_search(last_user_msg)

    if web_result:
        messages.append({"role": "system", "content": f"معلومات حديثة من البحث: {web_result}"})

    full_messages = [{"role": "system", "content": full_system}] + messages

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=full_messages,
        temperature=0.7
    )

    return response.choices[0].message["content"]

# ✅ هذا هو المهم ليتوافق مع app.py
def process_message(messages):
    return chat_with_myais(messages)
