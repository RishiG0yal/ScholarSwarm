"""
PaperVerify — Pydantic models for all data structures.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Stage 1: Ingestion ────────────────────────────────────────────────

class PageText(BaseModel):
    """Text extracted from a single PDF page."""
    page_number: int
    text: str
    is_ocr: bool = False
    has_tables: bool = False
    table_captions: list[str] = Field(default_factory=list)
    figure_captions: list[str] = Field(default_factory=list)


class DocumentResult(BaseModel):
    """Full result from PDF ingestion."""
    pages: list[PageText]
    total_pages: int
    is_ocr_processed: bool = False
    is_non_english: bool = False
    detected_language: str = "en"
    warnings: list[str] = Field(default_factory=list)


# ── Stage 2: Chunking ────────────────────────────────────────────────

class Chunk(BaseModel):
    """A semantic chunk of text with metadata."""
    chunk_id: str
    text: str
    page_number: int
    section_guess: str = "Unknown"
    word_count: int = 0


# ── Stage 4: Extraction ──────────────────────────────────────────────

class ExtractedClaim(BaseModel):
    """A claim extracted by Agent 1."""
    claim: str
    type: Literal["finding", "limitation", "method"]
    page: int
    chunk_id: str
    confidence: Literal["high", "medium", "low"]
    is_conflicting: bool = False


class ExtractionResult(BaseModel):
    """Batch output from the extractor agent."""
    claims: list[ExtractedClaim]


# ── Stage 5: Fact-Checking ───────────────────────────────────────────

class VerificationVerdict(BaseModel):
    """Fact-checker's verdict on a single claim."""
    verdict: Literal["verified", "unsupported", "partially_supported"]
    reasoning: str = ""
    rewritten_claim: Optional[str] = None
    source_quote: str = ""


class VerifiedClaim(BaseModel):
    """A claim that survived fact-checking."""
    claim: str
    original_claim: str
    type: Literal["finding", "limitation", "method"]
    page: int
    chunk_id: str
    confidence: Literal["high", "medium", "low"]
    verdict: Literal["verified", "partially_supported"]
    source_quote: str
    is_conflicting: bool = False


# ── Stage 7: Outputs ─────────────────────────────────────────────────

class Flashcard(BaseModel):
    """A single Q&A flashcard."""
    question: str
    answer: str
    page: int
    chunk_id: str


class FlashcardSet(BaseModel):
    """Output from the flashcard generator."""
    flashcards: list[Flashcard]


class ConceptNode(BaseModel):
    """A node in the concept map."""
    id: str
    label: str
    cluster: int = 0
    page: int = 0
    claim_type: str = "finding"


class ConceptEdge(BaseModel):
    """An edge in the concept map."""
    source: str
    target: str
    similarity: float = 0.0


class ConceptMap(BaseModel):
    """Concept map structure."""
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]
    is_simple_list: bool = False  # True when < 5 claims


class AnalysisResults(BaseModel):
    """Final output delivered to the frontend."""
    session_id: str
    verified_brief: str = ""
    flashcards: list[Flashcard] = Field(default_factory=list)
    concept_map: Optional[ConceptMap] = None
    verified_claims: list[VerifiedClaim] = Field(default_factory=list)
    total_claims_extracted: int = 0
    total_claims_verified: int = 0
    total_claims_rejected: int = 0
    quality_warning: Optional[str] = None
    document_warnings: list[str] = Field(default_factory=list)


# ── Processing Status ────────────────────────────────────────────────

class ProcessingStatus(BaseModel):
    """Real-time processing status sent via SSE."""
    session_id: str
    stage: Literal[
        "uploading", "ingestion", "chunking", "embedding",
        "extraction", "fact_checking", "citation",
        "output_generation", "complete", "error"
    ]
    progress_pct: int = 0
    message: str = ""
    error_detail: Optional[str] = None


# ── API Response Models ──────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response after successful PDF upload."""
    session_id: str
    filename: str
    total_pages: int
    file_size_mb: float
    warnings: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: str
    detail: str
    stage: Optional[str] = None
