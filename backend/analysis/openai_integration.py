import os
from dotenv import load_dotenv
from pathlib import Path


def _configure_gemini():
    # Load backend/.env explicitly to avoid cwd issues
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()
    except Exception:
        load_dotenv()
    try:
        import google.generativeai as genai
    except Exception:
        return None, None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, None
    try:
        genai.configure(api_key=api_key)
    except Exception:
        return None, None
    return genai, api_key


def call_gemini_refactor(prompt: str):
    genai, api_key = _configure_gemini()
    if not genai or not api_key:
        return {"error": "GEMINI_API_KEY not set or google-generativeai not installed"}
    try:
        preferred = os.getenv("GEMINI_MODEL")
        candidates = [m for m in [preferred, "gemini-1.5-pro-latest", "gemini-1.5-pro", "gemini-1.5-flash-latest", "gemini-1.5-flash"] if m]
        last_err = None
        for name in candidates:
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content(prompt)
                if hasattr(response, "text"):
                    return {"text": response.text, "model": name}
                return {"text": str(response), "model": name}
            except Exception as e:
                last_err = str(e)
                continue
        # Fallback: discover models and pick one that supports generateContent
        try:
            discovered = []
            for m in genai.list_models():
                try:
                    supp = set(getattr(m, "supported_generation_methods", []) or [])
                    if "generateContent" in supp or "generate_content" in supp:
                        discovered.append(m.name)
                except Exception:
                    continue
            for name in discovered:
                try:
                    model = genai.GenerativeModel(name)
                    response = model.generate_content(prompt)
                    if hasattr(response, "text"):
                        return {"text": response.text, "model": name}
                    return {"text": str(response), "model": name}
                except Exception as e:
                    last_err = str(e)
                    continue
            return {"error": last_err or "no model usable", "tried": candidates + discovered}
        except Exception as ee:
            return {"error": last_err or str(ee), "tried": candidates}
    except Exception as e:
        return {"error": str(e)}


def call_ai(prompt: str, provider: str = "gemini"):
    if provider == "gemini":
        return call_gemini_refactor(prompt)
    return {"error": "unsupported provider"}
