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

SYSTEM_PROMPT = """You are an expert science communicator. Rewrite the given academic research summary for a curious, intelligent 16-year-old with no prior knowledge of the field.
Return ONLY valid JSON. No markdown fences, no text outside the JSON.

{
  "eli5_summary": "3-4 sentences. Use everyday language. Include one concrete real-world analogy. Explain: (1) what problem existed and why it mattered, (2) what the researchers did to solve it, (3) what the result was and why it is significant. Never use jargon without immediately explaining it.",
  "reading_level": "High School" or "Undergraduate" or "Graduate" or "Expert"
}

Reading level guide — assess based on the original summary's vocabulary and concepts:
- High School: everyday vocabulary, no domain expertise needed
- Undergraduate: basic STEM background helpful
- Graduate: requires field-specific knowledge
- Expert: requires deep expertise in the subfield"""


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
    user_prompt = f"Paper Title: {title}\n\nAcademic Summary:\n{original_summary}\n\nRewrite for a 16-year-old. Return the JSON."

    for model in ["groq/compound-mini", "llama-3.3-70b-versatile"]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.35,
                max_tokens=500,
            )
            return json.loads(_clean_json(response.choices[0].message.content))
        except Exception:
            continue
    return None


def _simplify_with_gemini(original_summary: str, title: str, api_key: str) -> dict | None:
    from google import genai
    client = genai.Client(api_key=api_key)
    prompt = f"{SYSTEM_PROMPT}\n\nPaper Title: {title}\n\nAcademic Summary:\n{original_summary}\n\nReturn the JSON."

    for model_id in GEMINI_TEXT_MODELS:
        try:
            response = client.models.generate_content(model=model_id, contents=[prompt])
            return json.loads(_clean_json(response.text))
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                continue
            return None
    return None


def _clean_json(raw: str) -> str:
    return re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
