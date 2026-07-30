import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GEMINI_TEXT_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

SYSTEM_PROMPT = """You are a rigorous academic fact-checker. Verify whether the given claim is directly supported by the provided source text.
Return ONLY valid JSON. No markdown fences, no explanation outside the JSON.

{
  "verified": true or false,
  "confidence": 0.0 to 1.0,
  "critique": "One precise sentence explaining why the claim is supported or not, referencing specific evidence.",
  "source_quote": "The most relevant sentence copied verbatim from the source text. Empty string if none found."
}

Rules:
- verified=true only if the claim is explicitly and directly stated in the source text.
- verified=false if the claim contradicts, overstates, or has no basis in the provided text.
- confidence 0.85-1.0: exact or near-exact match. 0.5-0.84: partial support. 0.0-0.49: weak or absent.
- source_quote must be copied verbatim from the source, never paraphrased."""


def verify_claims(claims: list, page_texts: dict) -> list:
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            return _verify_parallel(claims, page_texts, groq_key, None)
        except Exception:
            pass

    if gemini_key:
        try:
            return _verify_parallel(claims, page_texts, None, gemini_key)
        except Exception:
            pass

    return [_fallback_claim(c) for c in claims]


def _verify_parallel(claims: list, page_texts: dict, groq_key, gemini_key) -> list:
    def verify_one(claim):
        claim_text = claim.get("text", "")
        page_num = claim.get("page", 1)
        source_text = _get_best_source(claim_text, page_texts, page_num)
        user_prompt = f'Claim: "{claim_text}"\n\nSource text:\n{source_text}\n\nReturn the JSON.'

        if groq_key:
            client = Groq(api_key=groq_key)
            for model in ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]:
                for attempt in range(2):
                    try:
                        resp = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.05,
                            max_tokens=400,
                        )
                        result = json.loads(_clean_json(resp.choices[0].message.content))
                        return {**claim, "verified": bool(result.get("verified", False)),
                                "confidence": float(result.get("confidence", 0.5)),
                                "critique": result.get("critique", ""),
                                "source_quote": result.get("source_quote", "")}
                    except json.JSONDecodeError:
                        break
                    except Exception as e:
                        if "rate_limit" in str(e).lower() or "429" in str(e):
                            time.sleep(5 * (attempt + 1))
                            continue
                        break

        if gemini_key:
            from google import genai
            gclient = genai.Client(api_key=gemini_key)
            prompt = f"{SYSTEM_PROMPT}\n\nClaim: \"{claim_text}\"\n\nSource text:\n{source_text}\n\nReturn the JSON."
            try:
                result = json.loads(_clean_json(_gemini_generate(gclient, prompt)))
                return {**claim, "verified": bool(result.get("verified", False)),
                        "confidence": float(result.get("confidence", 0.5)),
                        "critique": result.get("critique", ""),
                        "source_quote": result.get("source_quote", "")}
            except Exception:
                pass

        return _fallback_claim(claim)

    with ThreadPoolExecutor(max_workers=min(len(claims), 4)) as executor:
        return list(executor.map(verify_one, claims))


def _gemini_generate(client, prompt: str) -> str:
    for model_id in GEMINI_TEXT_MODELS:
        try:
            return client.models.generate_content(model=model_id, contents=[prompt]).text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                continue
            raise
    raise Exception("All Gemini text models quota exhausted.")


def _get_best_source(claim_text: str, page_texts: dict, claimed_page: int) -> str:
    normalized = {int(k): v for k, v in page_texts.items()}
    stopwords = {"the", "a", "an", "is", "was", "are", "were", "this", "that", "of", "in", "to", "and", "or", "for"}
    keywords = set(claim_text.lower().split()) - stopwords
    adjacent = (normalized.get(claimed_page - 1, "") + normalized.get(claimed_page, "") + normalized.get(claimed_page + 1, ""))
    if len(adjacent) <= 3000:
        return adjacent
    paragraphs = adjacent.split("\n\n")
    relevant = []
    for para in paragraphs:
        if any(kw in para.lower() for kw in keywords):
            relevant.append(para)
        if sum(len(p) for p in relevant) > 2500:
            break
    return "\n\n".join(relevant[:5]) if relevant else adjacent[:3000]


def _fallback_claim(claim: dict) -> dict:
    return {**claim, "verified": False, "confidence": 0.3,
            "critique": "Verification skipped due to processing error.", "source_quote": ""}


def _clean_json(raw: str) -> str:
    return re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
