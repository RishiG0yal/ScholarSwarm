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

SYSTEM_PROMPT = """You are ScholarSwarm Critic Agent, a rigorous academic fact-checker.
Verify whether the given claim is directly supported by the source text.
Return ONLY valid JSON, no markdown:
{
  "verified": true or false,
  "confidence": 0.0 to 1.0,
  "critique": "One sentence: why this claim is or is not supported by the text",
  "source_quote": "The exact sentence or phrase from the source text most relevant to this claim"
}
Rules:
- verified=true ONLY if the claim is directly and explicitly supported
- verified=false if contradicted, exaggerated, or not found
- confidence 0.9+: strong direct evidence | 0.5-0.8: partial | below 0.5: weak or absent
- source_quote must be a real sentence from the provided text, never paraphrased"""


def verify_claims(claims: list, page_texts: dict) -> list:
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            return _verify_with_groq_parallel(claims, page_texts, groq_key)
        except Exception:
            pass

    if gemini_key:
        try:
            return _verify_with_gemini_parallel(claims, page_texts, gemini_key)
        except Exception:
            pass

    return [_fallback_claim(c) for c in claims]


def _verify_with_groq_parallel(claims: list, page_texts: dict, api_key: str) -> list:
    client = Groq(api_key=api_key)

    def verify_one(claim):
        claim_text = claim.get("text", "")
        page_num = claim.get("page", 1)
        source_text = _get_best_source(claim_text, page_texts, page_num)
        user_prompt = (
            f'Claim: "{claim_text}"\n\n'
            f"Source text:\n{source_text}\n\n"
            "Return the JSON structure."
        )
        for model in ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]:
            for attempt in range(2):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.1,
                        max_tokens=400,
                    )
                    raw = _clean_json(response.choices[0].message.content)
                    result = json.loads(raw)
                    return {
                        **claim,
                        "verified": bool(result.get("verified", False)),
                        "confidence": float(result.get("confidence", 0.5)),
                        "critique": result.get("critique", ""),
                        "source_quote": result.get("source_quote", ""),
                    }
                except json.JSONDecodeError:
                    break
                except Exception as e:
                    err = str(e)
                    if "rate_limit" in err.lower() or "429" in err or "TPM" in err:
                        time.sleep(5 * (attempt + 1))
                        continue
                    break
        return _fallback_claim(claim)

    with ThreadPoolExecutor(max_workers=min(len(claims), 4)) as executor:
        return list(executor.map(verify_one, claims))


def _verify_with_gemini_parallel(claims: list, page_texts: dict, api_key: str) -> list:
    from google import genai
    client = genai.Client(api_key=api_key)

    def verify_one(claim):
        claim_text = claim.get("text", "")
        page_num = claim.get("page", 1)
        source_text = _get_best_source(claim_text, page_texts, page_num)
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f'Claim: "{claim_text}"\n\n'
            f"Source text:\n{source_text}\n\n"
            "Return the JSON structure."
        )
        try:
            raw = _clean_json(_gemini_generate(client, prompt))
            result = json.loads(raw)
            return {
                **claim,
                "verified": bool(result.get("verified", False)),
                "confidence": float(result.get("confidence", 0.5)),
                "critique": result.get("critique", ""),
                "source_quote": result.get("source_quote", ""),
            }
        except Exception:
            return _fallback_claim(claim)

    with ThreadPoolExecutor(max_workers=min(len(claims), 4)) as executor:
        return list(executor.map(verify_one, claims))


def _gemini_generate(client, prompt: str) -> str:
    for model_id in GEMINI_TEXT_MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[prompt],
            )
            return response.text
        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                continue
            raise
    raise Exception("All Gemini text models quota exhausted.")


def _get_best_source(claim_text: str, page_texts: dict, claimed_page: int) -> str:
    normalized = {int(k): v for k, v in page_texts.items()}
    stopwords = {"the", "a", "an", "is", "was", "are", "were", "this", "that", "of", "in", "to", "and", "or", "for"}
    keywords = set(claim_text.lower().split()) - stopwords

    adjacent = (
        normalized.get(claimed_page - 1, "") +
        normalized.get(claimed_page, "") +
        normalized.get(claimed_page + 1, "")
    )

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
    return {
        **claim,
        "verified": False,
        "confidence": 0.3,
        "critique": "Verification skipped due to processing error.",
        "source_quote": "",
    }


def _clean_json(raw: str) -> str:
    return re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
