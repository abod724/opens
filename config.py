import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    BING_API_KEY = os.getenv("BING_API_KEY", "")
    DB_PATH = os.getenv("DB_PATH", "myais.db")