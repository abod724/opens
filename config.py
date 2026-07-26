import os
from dotenv import load_dotenv

load_dotenv()  # تحميل المتغيرات من ملف .env (اختياري)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'my-secret-key')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///niras.db')
