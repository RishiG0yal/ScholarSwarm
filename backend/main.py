"""
PaperVerify — FastAPI Application.

Main entry point with REST API, SSE progress streaming, and static file serving.
"""
import asyncio
import json
import hashlib
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config import (
    TEMP_DIR, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, MAX_PAGES, FRONTEND_DIR,
)
from models.schemas import UploadResponse, ErrorResponse, ProcessingStatus
from services.session import session_manager, SessionData
from utils.logging_util import logger

# ── Pipeline imports ──────────────────────────────────────────────────
from pipeline.ingestion import ingest_pdf
from pipeline.chunking import chunk_document
from pipeline.embeddings import embed_and_store
from pipeline.extractor import extract_claims
from pipeline.fact_checker import fact_check_claims
from pipeline.citation import format_citations
from pipeline.output import generate_all_outputs


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 PaperVerify starting up...")
    session_manager.start_cleanup_task()
    yield
    logger.info("🛑 PaperVerify shutting down...")
    session_manager.stop_cleanup_task()


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="PaperVerify",
    description="AI research paper analyzer with fact-checked citations",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ────────────────────────────────────────────────────────

@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and start processing.

    Validates file size and type, saves to temp storage,
    starts the analysis pipeline as a background task.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted."
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
        )

    # Create session
    session = session_manager.create_session(file.filename)
    session_dir = TEMP_DIR / session.session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save PDF
    pdf_path = session_dir / file.filename
    with open(pdf_path, "wb") as f:
        f.write(content)
    session.pdf_path = pdf_path

    # Quick page count check using PyMuPDF
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()

        if total_pages > MAX_PAGES:
            session_manager.delete_session(session.session_id)
            raise HTTPException(
                status_code=400,
                detail=f"PDF has {total_pages} pages. Maximum is {MAX_PAGES} pages."
            )
    except HTTPException:
        raise
    except Exception as e:
        session.update_status("error", 0, "Failed to read PDF", str(e))
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    # Start processing in background
    asyncio.create_task(_run_pipeline(session))

    return UploadResponse(
        session_id=session.session_id,
        filename=file.filename,
        total_pages=total_pages,
        file_size_mb=round(len(content) / (1024 * 1024), 2),
    )


@app.get("/api/status/{session_id}")
async def stream_status(session_id: str, request: Request):
    """
    Server-Sent Events stream for processing progress.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        last_stage = None
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            session = session_manager.get_session(session_id)
            if not session:
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Session expired'})}\n\n"
                break

            status = session.status
            # Only send if changed
            if status.stage != last_stage or status.stage in ("error", "complete"):
                yield f"data: {status.model_dump_json()}\n\n"
                last_stage = status.stage

            if status.stage in ("complete", "error"):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    """Get the final analysis results for a session."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status.stage == "error":
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Processing failed",
                detail=session.status.error_detail or "Unknown error",
                stage=session.status.stage,
            ).model_dump(),
        )

    if session.status.stage != "complete":
        raise HTTPException(
            status_code=202,
            detail="Processing is still in progress"
        )

    if not session.results:
        raise HTTPException(
            status_code=500,
            detail="Results not available"
        )

    return session.results.model_dump()


@app.get("/api/pdf/{session_id}")
async def serve_pdf(session_id: str):
    """Serve the uploaded PDF for the embedded viewer."""
    session = session_manager.get_session(session_id)
    if not session or not session.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found")

    if not session.pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file has been deleted")

    return FileResponse(
        path=str(session.pdf_path),
        media_type="application/pdf",
        filename=session.filename,
    )


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Manually delete a session and all its data."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager.delete_session(session_id)
    return {"message": "Session deleted successfully"}


# ── Pipeline Runner ──────────────────────────────────────────────────

async def _run_pipeline(session: SessionData):
    """
    Run the full analysis pipeline for a session.
    Updates session status at each stage for SSE streaming.
    """
    try:
        # ── Stage 1: Ingestion ────────────────────────────────────────
        session.update_status("ingestion", 10, "Extracting text from PDF...")
        doc_result = await ingest_pdf(session.pdf_path)

        if not any(p.text.strip() for p in doc_result.pages):
            session.update_status(
                "error", 10,
                "No text could be extracted from this PDF.",
                "PDF extraction failed: The document appears to contain only images "
                "without extractable text. Install Tesseract OCR for scanned PDF support.",
            )
            return

        # ── Stage 2: Chunking ────────────────────────────────────────
        session.update_status("chunking", 25, "Splitting text into semantic chunks...")
        chunks = await chunk_document(
            pages=doc_result.pages,
            session_id=session.session_id,
        )

        if not chunks:
            session.update_status(
                "error", 25,
                "Chunking failed: no text chunks produced.",
                "The document may be too short or contain only non-text elements.",
            )
            return

        # ── Stage 3: Embeddings ──────────────────────────────────────
        session.update_status("embedding", 40, "Generating embeddings...")
        collection_name, is_short_paper = await embed_and_store(
            chunks=chunks,
            session_id=session.session_id,
            pdf_path=session.pdf_path,
            total_pages=doc_result.total_pages,
        )
        session.chromadb_collection_name = collection_name

        # ── Stage 4: Extraction ──────────────────────────────────────
        session.update_status("extraction", 55, "Extracting claims from paper...")
        extracted_claims = await extract_claims(
            chunks=chunks,
            is_short_paper=is_short_paper,
        )

        if not extracted_claims:
            session.update_status(
                "error", 55,
                "No claims could be extracted from this paper.",
                "The AI agent could not identify any verifiable claims. "
                "This may happen with very short or non-standard papers.",
            )
            return

        # ── Stage 5: Fact-Checking ───────────────────────────────────
        session.update_status(
            "fact_checking", 70,
            f"Fact-checking {len(extracted_claims)} claims against source text..."
        )
        verified_claims, quality_warning = await fact_check_claims(
            claims=extracted_claims,
            chunks=chunks,
        )

        total_rejected = len(extracted_claims) - len(verified_claims)

        if not verified_claims:
            session.update_status(
                "error", 70,
                "No claims could be verified.",
                "All extracted claims failed fact-checking. "
                "This may indicate the paper's content doesn't contain verifiable claims, "
                "or the extraction quality was too low.",
            )
            return

        # ── Stage 6: Citation Formatting ─────────────────────────────
        session.update_status("citation", 80, "Formatting citations...")
        cited_claims = format_citations(verified_claims)

        # ── Stage 7: Output Generation ───────────────────────────────
        session.update_status("output_generation", 90, "Generating study aids...")
        results = await generate_all_outputs(
            verified_claims=cited_claims,
            session_id=session.session_id,
            total_extracted=len(extracted_claims),
            total_rejected=total_rejected,
            quality_warning=quality_warning,
            document_warnings=doc_result.warnings,
        )

        # ── Complete ─────────────────────────────────────────────────
        session.results = results
        session.update_status(
            "complete", 100,
            f"Analysis complete! {len(cited_claims)} verified claims found."
        )

        logger.info(
            f"✅ Pipeline complete for session {session.session_id}: "
            f"{len(cited_claims)} verified claims, "
            f"{len(results.flashcards)} flashcards"
        )

    except ValueError as e:
        # Expected errors (corrupted PDF, password-protected, etc.)
        error_msg = str(e)
        stage = session.status.stage
        session.update_status("error", session.status.progress_pct, error_msg, error_msg)
        logger.error(f"Pipeline error at {stage}: {error_msg}")

    except Exception as e:
        # Unexpected errors
        stage = session.status.stage
        error_msg = f"Unexpected error during {stage}: {str(e)}"
        session.update_status("error", session.status.progress_pct, error_msg, str(e))
        logger.error(error_msg, exc_info=True)


# ── Static Files (Frontend) ──────────────────────────────────────────

# Serve frontend static files
if FRONTEND_DIR.exists():
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend page."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        return {"message": "PaperVerify API is running. Frontend not found."}


# ── Run ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
