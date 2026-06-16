import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

def get_groq_api_key():
    return os.getenv("GROQ_API_KEY", "")
