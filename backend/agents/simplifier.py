import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_TEXT_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

SYSTEM_PROMPT = """You are ScholarSwarm Simplifier Agent, an expert science communicator.
Rewrite the research summary so a smart 16-year-old with no domain knowledge can understand it.
Return ONLY valid JSON, no markdown:
{
  "eli5_summary": "3-4 sentences. Use everyday language and one concrete analogy. No jargon. Cover: what problem was solved, how it was solved, and why it matters.",
  "reading_level": "High School" or "Undergraduate" or "Graduate" or "Expert"
}"""


def simplify_summary(original_summary: str, title: str) -> dict:
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        result = _simplify_with_groq(original_summary, title, groq_key)
        if result:
            return result

    if gemini_key:
        result = _simplify_with_gemini(original_summary, title, gemini_key)
        if result:
            return result

    return {"eli5_summary": original_summary, "reading_level": "Graduate"}


def _simplify_with_groq(original_summary: str, title: str, api_key: str) -> dict | None:
    from groq import Groq
    client = Groq(api_key=api_key)
    user_prompt = (
        f"Paper Title: {title}\n\n"
        f"Academic Summary:\n{original_summary}\n\n"
        "Rewrite for a smart 16-year-old. Return the JSON structure."
    )
    try:
        response = client.chat.completions.create(
            model="groq/compound-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        raw = _clean_json(response.choices[0].message.content)
        return json.loads(raw)
    except Exception:
        # Fallback to 70b if compound-mini fails
        try:
            from groq import Groq as _Groq
            c = _Groq(api_key=api_key)
            response = c.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=500,
            )
            raw = _clean_json(response.choices[0].message.content)
            return json.loads(raw)
        except Exception:
            return None


def _simplify_with_gemini(original_summary: str, title: str, api_key: str) -> dict | None:
    from google import genai
    client = genai.Client(api_key=api_key)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Paper Title: {title}\n\n"
        f"Academic Summary:\n{original_summary}\n\n"
        "Return the JSON structure."
    )
    for model_id in GEMINI_TEXT_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt],
            )
            raw = _clean_json(response.text)
            return json.loads(raw)
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                continue
            return None
    return None


def _clean_json(raw: str) -> str:
    return re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
