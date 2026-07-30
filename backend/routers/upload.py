"""
Upload Router — Handles file uploads and document preview.
Accepts PDF, DOCX, PPTX, and TXT files.
"""

import os
import uuid
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Request

from backend.models.schemas import UploadResponse, ParsedDocument
from backend.parsers.pdf_parser import parse_pdf
from backend.parsers.docx_parser import parse_docx
from backend.parsers.pptx_parser import parse_pptx
from backend.parsers.txt_parser import parse_txt

logger = logging.getLogger("rag_pipeline.routers.upload")

router = APIRouter()

# In-memory store for parsed documents (keyed by file_id)
_parsed_docs: dict[str, ParsedDocument] = {}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def get_parsed_doc(file_id: str) -> ParsedDocument | None:
    """Retrieve a parsed document by file_id. Used by pipeline router."""
    return _parsed_docs.get(file_id)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload a document file for processing.
    Supported formats: PDF, DOCX, PPTX, TXT.
    """
    config = request.app.state.config

    # Validate file extension
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file contents
    contents = await file.read()
    file_size = len(contents)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size / 1024 / 1024:.1f} MB). Max: 50 MB.",
        )

    # Save to uploads directory
    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{ext}"
    file_path = os.path.join(config.upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"Uploaded: {filename} → {safe_name} ({file_size} bytes)")

    # Parse the document immediately
    try:
        if ext == ".pdf":
            parsed = parse_pdf(file_path, file_id)
        elif ext == ".docx":
            parsed = parse_docx(file_path, file_id)
        elif ext == ".pptx":
            parsed = parse_pptx(file_path, file_id)
        elif ext == ".txt":
            parsed = parse_txt(file_path, file_id)
        else:
            raise HTTPException(status_code=400, detail=f"Parser not available for {ext}")

        # Store parsed document
        _parsed_docs[file_id] = parsed
        logger.info(f"Parsed: {parsed.total_chunks} chunks from {parsed.total_pages} pages")

    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(e)}")

    return UploadResponse(
        file_id=file_id,
        filename=filename,
        file_type=ext.lstrip("."),
        size_bytes=file_size,
        message=f"Uploaded and parsed: {parsed.total_chunks} text chunks from {parsed.total_pages} pages",
    )


@router.get("/files/{file_id}/preview")
async def preview_file(file_id: str):
    """Return parsed text chunks for file preview in the UI."""
    parsed = _parsed_docs.get(file_id)
    if not parsed:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "file_id": parsed.file_id,
        "filename": parsed.filename,
        "file_type": parsed.file_type,
        "total_pages": parsed.total_pages,
        "total_chunks": parsed.total_chunks,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "page": c.page_number,
                "paragraph": c.paragraph_number,
                "text": c.text[:500],  # Truncate for preview
            }
            for c in parsed.chunks
        ],
    }
