import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 6000
MAX_CHUNKS = 8

GEMINI_TEXT_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

CHUNK_PROMPT = """You are ScholarSwarm Extractor Agent, an expert AI research analyst.
Analyze this section of a research paper and return ONLY valid JSON, no markdown, no explanation.

{
  "summary": "2-3 sentence summary of what this section covers — be specific, name methods and results",
  "claims": [
    {"text": "Specific verifiable claim — MUST include numbers, model names, or dataset names if present in text", "page": 1}
  ],
  "limitations": ["A limitation explicitly stated in this section — quote or closely paraphrase"],
  "flashcards": [
    {"front": "A specific question whose answer is directly in this section", "back": "Precise answer from the text"}
  ],
  "key_terms": [
    {"term": "Technical term as used in this paper", "definition": "Definition exactly as the paper uses it"}
  ]
}

Rules:
- NEVER invent claims. Every claim must be directly traceable to the source text.
- Claims with numbers (e.g. '94.2% accuracy on MATH benchmark') are far better than vague claims
- Page numbers: estimate from section position (section 1 = pages 1-2, section 3 = pages 5-6, etc.)
- If a section has no limitations, return []
- Flashcard backs must be specific answers, not vague summaries
- Extract 2-4 claims, 0-3 limitations, 2-3 flashcards, 2-4 key terms"""

MERGE_PROMPT = """You are ScholarSwarm Merge Agent. You have partial analyses of multiple sections of one research paper.
Merge them into one final comprehensive, high-quality brief.
Return ONLY valid JSON, no markdown:

{
  "summary": "3-4 sentence summary of the FULL paper. Cover: (1) what problem is solved, (2) what method is proposed, (3) what the key quantitative result is, (4) why this matters",
  "claims": [
    {"text": "The 5 most specific verifiable claims — strongly prefer ones with numbers, percentages, model names", "page": 1}
  ],
  "limitations": ["Up to 5 unique specific limitations explicitly from the paper"],
  "flashcards": [
    {"front": "Specific question covering a different aspect of the paper", "back": "Precise specific answer"}
  ],
  "key_terms": [
    {"term": "Term", "definition": "Definition as used in this specific paper"}
  ]
}

Rules:
- Summary MUST be specific — name the method, name the benchmark, quote the key metric
- Remove duplicate claims — always keep the more specific or quantitative version
- Flashcard backs must be specific, never generic
- Return exactly: 5 claims, 3-5 limitations, 6 flashcards, 8-10 key terms"""


def extract_brief(full_context: str, title: str, authors: str) -> dict:
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            return _extract_with_groq(full_context, title, authors, groq_key)
        except Exception as e:
            if gemini_key:
                pass  # fall through to Gemini
            else:
                raise Exception(f"Extraction failed: {str(e)}")

    if gemini_key:
        try:
            return _extract_with_gemini(full_context, title, authors, gemini_key)
        except Exception as e:
            raise Exception(f"All extraction methods failed: {str(e)}")

    raise Exception("No API keys configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env")


def _extract_with_groq(full_context: str, title: str, authors: str, api_key: str) -> dict:
    client = Groq(api_key=api_key)
    chunks = _split_into_chunks(full_context, CHUNK_SIZE)
    chunks = chunks[:MAX_CHUNKS]

    def process_chunk(args):
        i, chunk = args
        user_prompt = (
            f"Paper Title: {title}\nAuthors: {authors}\n"
            f"Section {i + 1} of {len(chunks)}:\n\n{chunk}\n\n"
            "Analyze this section and return the JSON structure."
        )
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": CHUNK_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=1500,
                )
                raw = _clean_json(response.choices[0].message.content)
                return (i, json.loads(raw))
            except json.JSONDecodeError:
                return (i, None)
            except Exception as e:
                err = str(e)
                if "rate_limit" in err.lower() or "429" in err or "TPM" in err:
                    import time
                    time.sleep(5 * (attempt + 1))
                    continue
                return (i, None)
        return (i, None)

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(len(chunks), 4)) as executor:
        results = list(executor.map(process_chunk, enumerate(chunks)))

    results.sort(key=lambda x: x[0])
    partial_briefs = [r for _, r in results if r is not None]

    if not partial_briefs:
        raise Exception("Groq extraction produced no results.")

    if len(partial_briefs) == 1:
        return partial_briefs[0]

    return _merge_with_groq(client, partial_briefs, title, authors)


def _merge_with_groq(client: Groq, partial_briefs: list, title: str, authors: str) -> dict:
    combined = json.dumps(partial_briefs, indent=2)[:10000]
    user_prompt = (
        f"Paper Title: {title}\nAuthors: {authors}\n\n"
        f"Partial analyses from {len(partial_briefs)} sections:\n{combined}\n\n"
        "Merge into one final comprehensive brief. Return the JSON structure."
    )
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": MERGE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = _clean_json(response.choices[0].message.content)
        return json.loads(raw)
    except Exception:
        return _merge_locally(partial_briefs)


def _extract_with_gemini(full_context: str, title: str, authors: str, api_key: str) -> dict:
    from google import genai
    client = genai.Client(api_key=api_key)
    chunks = _split_into_chunks(full_context, CHUNK_SIZE)
    partial_briefs = []

    for i, chunk in enumerate(chunks[:MAX_CHUNKS]):
        prompt = (
            f"{CHUNK_PROMPT}\n\n"
            f"Paper Title: {title}\nAuthors: {authors}\n"
            f"Section {i + 1} of {min(len(chunks), MAX_CHUNKS)}:\n\n{chunk}\n\n"
            "Return the JSON structure."
        )
        try:
            raw = _clean_json(_gemini_generate(client, prompt))
            partial = json.loads(raw)
            partial_briefs.append(partial)
        except Exception:
            continue

    if not partial_briefs:
        raise Exception("Gemini extraction produced no results.")

    if len(partial_briefs) == 1:
        return partial_briefs[0]

    combined = json.dumps(partial_briefs, indent=2)[:10000]
    merge_prompt = (
        f"{MERGE_PROMPT}\n\n"
        f"Paper Title: {title}\nAuthors: {authors}\n\n"
        f"Partial analyses:\n{combined}\n\nReturn the JSON structure."
    )
    try:
        raw = _clean_json(_gemini_generate(client, merge_prompt))
        return json.loads(raw)
    except Exception:
        return _merge_locally(partial_briefs)


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


def _split_into_chunks(text: str, chunk_size: int) -> list:
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 100]


def _merge_locally(partial_briefs: list) -> dict:
    seen_claims, seen_limits, seen_fronts, seen_terms = set(), set(), set(), set()
    all_claims, all_limits, all_flashcards, all_terms, summaries = [], [], [], [], []

    for brief in partial_briefs:
        if brief.get("summary"):
            summaries.append(brief["summary"])
        for c in brief.get("claims", []):
            key = c.get("text", "")[:80]
            if key not in seen_claims:
                seen_claims.add(key)
                all_claims.append(c)
        for l in brief.get("limitations", []):
            key = l[:80]
            if key not in seen_limits:
                seen_limits.add(key)
                all_limits.append(l)
        for f in brief.get("flashcards", []):
            key = f.get("front", "")[:80]
            if key not in seen_fronts:
                seen_fronts.add(key)
                all_flashcards.append(f)
        for t in brief.get("key_terms", []):
            key = t.get("term", "").lower()
            if key not in seen_terms:
                seen_terms.add(key)
                all_terms.append(t)

    return {
        "summary": " ".join(summaries[:2]),
        "claims": all_claims[:5],
        "limitations": all_limits[:5],
        "flashcards": all_flashcards[:6],
        "key_terms": all_terms[:10],
    }


def _clean_json(raw: str) -> str:
    return re.sub(r'```(?:json)?', '', raw).strip().rstrip('`').strip()
