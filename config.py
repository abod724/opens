import os

class Config:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    BING_API_KEY = os.environ.get("BING_API_KEY", "")
