import openai
from config import Config

openai.api_key = Config.OPENAI_API_KEY

def load_knowledge():
    try:
        with open("Knowledge.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def chat_with_myais(messages):
    system_prompt = """
أنت نبراس، مساعد ذكي باللهجة السعودية.
ردودك قصيرة، واضحة، مباشرة، بدون فلسفة.
"""

    knowledge = load_knowledge()
    full_system = system_prompt + "\n\n--- معلومات إضافية ---\n" + knowledge

    full_messages = [{"role": "system", "content": full_system}] + messages

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=full_messages,
        temperature=0.7
    )

    return response.choices[0].message["content"]

def process_message(user_message):
    messages = [{"role": "user", "content": user_message}]
    return chat_with_myais(messages)
