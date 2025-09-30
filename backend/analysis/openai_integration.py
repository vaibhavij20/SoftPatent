def call_openai_refactor(prompt):
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

def call_gemini_refactor(prompt):
    if not api_key:
        return {'error': 'GEMINI_API_KEY not set'}
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        return {'error': str(e)}
