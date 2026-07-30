import os
import re
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from parsers.pdf_parser import extract_text_from_pdf
from parsers.pptx_parser import extract_text_from_pptx
from parsers.figure_analyzer import extract_and_analyze_figures
from parsers.table_extractor import extract_tables_from_pdf
from parsers.equation_parser import extract_equations
from parsers.citation_extractor import extract_citations

from agents.extractor import extract_brief
from agents.critic import verify_claims
from agents.simplifier import simplify_summary

from utils.similarity import tfidf_similarity, blend_confidence, retrieve_top_chunks
from utils.readability import flesch_kincaid
from utils.cache import store_result, get_result
from utils.semantic_scholar import find_similar_papers

load_dotenv()

from demo_cache import preload_demo
preload_demo()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="ScholarSwarm API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
frontend_url = os.environ.get("FRONTEND_URL", "")
if frontend_url:
    ALLOWED_ORIGINS.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_TABLES_IN_RESPONSE = 10
MAX_FIGURES_IN_RESPONSE = 6
MAX_CONTEXT_PER_PAGE = 2000
RESULT_ID_PATTERN = re.compile(r'^([a-f0-9]{8}|demo1234)$')

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/octet-stream",  # some browsers send this for pptx
}

GEMINI_TEXT_MODELS = [
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


class AskRequest(BaseModel):
    result_id: str
    question: str

    @field_validator("result_id")
    @classmethod
    def validate_result_id(cls, v: str) -> str:
        if not RESULT_ID_PATTERN.match(v):
            raise ValueError("Invalid result_id format.")
        return v

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) > 500:
            raise ValueError("Question too long. Max 500 characters.")
        return v


@app.post("/upload")
@limiter.limit("10/minute")
async def upload_paper(request: Request, file: UploadFile = File(...)):
    filename = (file.filename or "").lower()

    if not (filename.endswith(".pdf") or filename.endswith(".pptx")):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files are accepted.")

    # Validate content type
    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {content_type}")

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB.")
    if len(file_bytes) < 1024:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt.")

    try:
        if filename.endswith(".pdf"):
            extracted = extract_text_from_pdf(file_bytes)
        else:
            extracted = extract_text_from_pptx(file_bytes)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse file. It may be corrupt or password-protected.")

    full_text = extracted["full_text"]
    page_texts = extracted["pages"]
    title = extracted["title"]
    authors = extracted["authors"]

    if not full_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. This may be a scanned image PDF. Please try a text-based PDF.",
        )

    tables, figures, equations = [], [], []

    if filename.endswith(".pdf"):
        try:
            tables = extract_tables_from_pdf(file_bytes)
        except Exception:
            pass
        try:
            figures = extract_and_analyze_figures(file_bytes, title)
        except Exception:
            pass
        try:
            equations = extract_equations(file_bytes)
        except Exception:
            pass

    citations = extract_citations(full_text)
    merged_context = _build_merged_context(full_text, tables, figures, equations)

    import time as _time
    t0 = _time.time()
    try:
        brief = extract_brief(merged_context, title, authors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    print(f"[TIMING] Extractor: {_time.time()-t0:.1f}s")

    t1 = _time.time()
    verified_claims = verify_claims(brief.get("claims", []), page_texts)
    print(f"[TIMING] Critic: {_time.time()-t1:.1f}s")

    for claim in verified_claims:
        sim = tfidf_similarity(claim["text"], full_text)
        claim["confidence"] = blend_confidence(claim.get("confidence", 0.5), sim)

    t2 = _time.time()
    simplified = simplify_summary(brief.get("summary", ""), title)
    print(f"[TIMING] Simplifier: {_time.time()-t2:.1f}s")
    readability = flesch_kincaid(full_text)

    result = {
        "title": title,
        "authors": authors,
        "total_pages": extracted["total_pages"],
        "file_type": extracted["file_type"],
        "summary": brief.get("summary", ""),
        "eli5_summary": simplified.get("eli5_summary", ""),
        "reading_level": simplified.get("reading_level", readability["label"]),
        "readability_score": readability["score"],
        "claims": verified_claims,
        "verified_count": sum(1 for c in verified_claims if c.get("verified")),
        "flagged_count": sum(1 for c in verified_claims if not c.get("verified")),
        "limitations": brief.get("limitations", []),
        "flashcards": brief.get("flashcards", []),
        "key_terms": brief.get("key_terms", []),
        "tables": tables[:MAX_TABLES_IN_RESPONSE],
        "figures": figures[:MAX_FIGURES_IN_RESPONSE],
        "equations": equations[:10],
        "citations": citations,
        "citations_count": len(citations),
    }

    result_id = store_result({**result, "_page_texts": page_texts})
    result["result_id"] = result_id
    return result


@app.get("/brief/{result_id}")
@limiter.limit("30/minute")
async def get_brief(request: Request, result_id: str):
    if not RESULT_ID_PATTERN.match(result_id):
        raise HTTPException(status_code=400, detail="Invalid brief ID.")
    data = get_result(result_id)
    if not data:
        raise HTTPException(status_code=404, detail="Brief not found or expired.")
    return {k: v for k, v in data.items() if k != "_page_texts"}


@app.post("/ask")
@limiter.limit("20/minute")
async def ask_paper(request: Request, body: AskRequest):
    cached = get_result(body.result_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Session expired. Please re-upload the paper.")

    page_texts = cached.get("_page_texts", {})
    title = cached.get("title", "")

    top_chunks = retrieve_top_chunks(body.question, page_texts, top_k=4)
    # Cap each page's contribution to avoid exceeding model context window
    context_parts = [
        f"[Page {pn}]\n{text[:MAX_CONTEXT_PER_PAGE]}"
        for pn, text, _ in top_chunks
    ]
    relevant_text = "\n\n---\n\n".join(context_parts)

    answer = _answer_with_best_model(title, relevant_text, body.question)
    source_page = top_chunks[0][0] if top_chunks else None

    return {
        "question": body.question,
        "answer": answer,
        "source_page": source_page,
        "pages_searched": [pn for pn, _, _ in top_chunks],
    }


@app.get("/similar")
@limiter.limit("30/minute")
async def similar_papers(request: Request, title: str = ""):
    if not title:
        return {"papers": []}
    papers = await find_similar_papers(title[:200])
    return {"papers": papers}


@app.get("/health")
def health():
    return {"status": "ok", "service": "ScholarSwarm API", "version": "1.0.0"}


@app.post("/tts")
@limiter.limit("10/minute")
async def text_to_speech(request: Request, body: dict):
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required.")
    if len(text) > 3000:
        text = text[:3000]

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise HTTPException(status_code=503, detail="TTS unavailable (no Gemini API key).")

    try:
        from google import genai as _genai
        from google.genai import types as _types
        import base64
        from fastapi.responses import Response

        client = _genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=_types.Content(
                role="user",
                parts=[_types.Part(text=text)]
            ),
            config=_types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=_types.SpeechConfig(
                    voice_config=_types.VoiceConfig(
                        prebuilt_voice_config=_types.PrebuiltVoiceConfig(voice_name="Kore")
                    )
                ),
            ),
        )
        audio_data = base64.b64decode(
            response.candidates[0].content.parts[0].inline_data.data
        )
        return Response(content=audio_data, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)[:100]}")


def _answer_with_best_model(title: str, context: str, question: str) -> str:
    system = (
        "You are ScholarSwarm, an expert research assistant. "
        "Answer questions using ONLY the provided source text from the paper. "
        "If the exact answer is not in the source text, say so clearly. "
        "Always cite the page number. Be specific and concise."
    )
    user = f"Paper: {title}\n\nSource text:\n{context}\n\nQuestion: {question}"

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        for model in ["groq/compound", "llama-3.3-70b-versatile"]:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.1,
                    max_tokens=700,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    continue
                break

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            for model_id in GEMINI_TEXT_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_id,
                        contents=[system + "\n\n" + user],
                    )
                    return response.text.strip()
                except Exception as e:
                    err = str(e)
                    if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
                        continue
                    break
        except Exception:
            pass

    raise HTTPException(status_code=500, detail="Could not process question. Please try again.")


def _build_merged_context(text: str, tables: list, figures: list, equations: list) -> str:
    context = text
    if tables:
        context += "\n\n=== EXTRACTED TABLES ===\n"
        for t in tables[:6]:
            context += f"\nTable {t['table_index']} (Page {t['page']}):\n{t.get('raw_markdown', '')}\n"
    if figures:
        context += "\n\n=== FIGURE DESCRIPTIONS (Vision AI) ===\n"
        for f in figures[:6]:
            context += f"\nFigure {f['index']} (Page {f['page']}): {f['description']}\n"
    if equations:
        context += "\n\n=== EQUATIONS ===\n"
        for eq in equations[:8]:
            desc = f" — {eq['description']}" if eq.get("description") else ""
            context += f"Page {eq['page']}: {eq['latex']}{desc}\n"
    return context
