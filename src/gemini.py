from dotenv import load_dotenv
from google import genai
import os

assert load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_KEY"])
