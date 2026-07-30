import os
import json
import re
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 4000
MAX_CHUNKS = 12

GEMINI_TEXT_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

CHUNK_PROMPT = """You are an expert academic research analyst. Analyze this section of a research paper and extract structured information.
Return ONLY valid JSON. No markdown fences, no explanation text.

{
  "summary": "2-3 sentences describing what this section covers. Name specific methods, models, datasets, or metrics mentioned.",
  "claims": [
    {"text": "A specific, verifiable claim from this section. Must include quantitative results (numbers, percentages, model names, dataset names) when present.", "page": 1}
  ],
  "limitations": ["A limitation explicitly acknowledged in this section. If none, return []."],
  "flashcards": [
    {"front": "A precise question answered directly by this section.", "back": "The exact answer from the text — never vague or generic."}
  ],
  "key_terms": [
    {"term": "A technical term introduced or defined in this section.", "definition": "The definition as used in this specific paper."}
  ]
}

Strict rules:
- Every claim must be traceable to the source text. Never fabricate.
- Quantitative claims (e.g. 'achieves 94.2% on MATH-500') score higher than qualitative ones.
- Page numbers: infer from context — introduction ≈ pages 1-2, methods ≈ 3-5, results ≈ 6-9, conclusion ≈ 10+.
- Extract 2-5 claims, 0-3 limitations, 2-4 flashcards, 2-5 key terms per section."""

MERGE_PROMPT = """You are an expert research synthesis agent. You have received partial analyses of multiple sections of one academic paper.
Merge them into a single, high-quality, comprehensive brief.
Return ONLY valid JSON. No markdown fences, no explanation text.

{
  "summary": "3-4 sentences covering the complete paper: (1) the core research problem, (2) the proposed method or approach, (3) the key quantitative results with specific numbers, (4) the broader significance.",
  "claims": [
    {"text": "The claim text — prefer quantitative, specific, and directly verifiable claims.", "page": 1}
  ],
  "limitations": ["A specific limitation explicitly stated in the paper."],
  "flashcards": [
    {"front": "A precise question about a key aspect of the paper.", "back": "The specific, accurate answer from the paper."}
  ],
  "key_terms": [
    {"term": "Technical term.", "definition": "Definition as used in this paper — not a generic dictionary definition."}
  ]
}

Strict rules:
- Summary must name the method and benchmark and quote the key metric. 'Achieves state-of-the-art' alone is not acceptable.
- For claims: remove all duplicates. Always keep the more specific, quantitative version.
- For flashcards: cover different aspects (problem, method, results, implications, datasets).
- Return exactly: 5 claims, 3-5 limitations, 6 flashcards, 8-10 key terms."""


def extract_brief(full_context: str, title: str, authors: str) -> dict:
    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            return _extract_with_groq(full_context, title, authors, groq_key)
        except Exception as e:
            if not gemini_key:
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
            "Analyze this section and return the JSON."
        )
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": CHUNK_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.15,
                    max_tokens=1200,
                )
                return (i, json.loads(_clean_json(response.choices[0].message.content)))
            except json.JSONDecodeError:
                return (i, None)
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e) or "TPM" in str(e):
                    import time
                    time.sleep(5 * (attempt + 1))
                    continue
                return (i, None)
        return (i, None)

    with ThreadPoolExecutor(max_workers=min(len(chunks), 4)) as executor:
        results = sorted(list(executor.map(process_chunk, enumerate(chunks))), key=lambda x: x[0])

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
        f"Partial section analyses:\n{combined}\n\n"
        "Merge into one final comprehensive brief. Return the JSON."
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
        return json.loads(_clean_json(response.choices[0].message.content))
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
            "Return the JSON."
        )
        try:
            raw = _clean_json(_gemini_generate(client, prompt))
            partial_briefs.append(json.loads(raw))
        except Exception:
            continue

    if not partial_briefs:
        raise Exception("Gemini extraction produced no results.")

    if len(partial_briefs) == 1:
        return partial_briefs[0]

    combined = json.dumps(partial_briefs, indent=2)[:10000]
    try:
        raw = _clean_json(_gemini_generate(client, f"{MERGE_PROMPT}\n\nPaper Title: {title}\nAuthors: {authors}\n\nPartial analyses:\n{combined}\n\nReturn the JSON."))
        return json.loads(raw)
    except Exception:
        return _merge_locally(partial_briefs)


def _gemini_generate(client, prompt: str) -> str:
    for model_id in GEMINI_TEXT_MODELS:
        try:
            return client.models.generate_content(model=model_id, contents=[prompt]).text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
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
