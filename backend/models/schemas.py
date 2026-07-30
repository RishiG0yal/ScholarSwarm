"""
Pydantic models and data schemas for the RAG Validation Pipeline.
Defines the data structures flowing between parsers, agents, and the API.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Document Parsing ───────────────────────────────────────────────

class TextChunk(BaseModel):
    """A chunk of text extracted from a document with source coordinates."""
    text: str = Field(..., description="The extracted text content")
    page_number: int = Field(..., description="Page/slide number (1-indexed)")
    paragraph_number: int = Field(..., description="Paragraph number within the page (1-indexed)")
    source_file: str = Field(..., description="Original filename")
    chunk_id: str = Field("", description="Unique identifier for this chunk")


class ParsedDocument(BaseModel):
    """Result of parsing an uploaded document."""
    file_id: str
    filename: str
    file_type: str
    total_pages: int
    total_chunks: int
    chunks: list[TextChunk]


# ─── Agent 1: Source Extractor ──────────────────────────────────────

class ExtractedClaim(BaseModel):
    """A claim extracted by Agent 1 from the source document."""
    claim_id: str = Field(..., description="Unique identifier for this claim")
    claim_type: str = Field(..., description="Type: claim, hypothesis, methodology, limitation")
    claim_text: str = Field(..., description="The extracted claim statement")
    coordinates: str = Field(..., description="Source coordinates, e.g. [Page 4, Paragraph 2]")
    verbatim_snippet: str = Field(..., description="Exact verbatim text from the document")
    confidence: float = Field(1.0, description="Extraction confidence 0.0-1.0")


class Agent1Output(BaseModel):
    """Complete output from Agent 1 (Source Extractor)."""
    file_id: str
    filename: str
    total_claims: int
    claims: list[ExtractedClaim]


# ─── Agent 2: Critic & Web Scrounger ───────────────────────────────

class ValidationStatus(str, Enum):
    VERIFIED = "verified"
    DISCREPANCY = "discrepancy_flagged"
    UNSUPPORTED = "unsupported"
    PENDING = "pending"


class WebFinding(BaseModel):
    """A single web search finding for a claim."""
    query_used: str = Field(..., description="The search query executed")
    source_url: str = Field(..., description="URL of the source")
    source_title: str = Field("", description="Title of the source")
    source_domain: str = Field("", description="Domain of the source (e.g. pubmed.gov)")
    snippet: str = Field(..., description="Relevant text snippet from the source")
    published_date: Optional[str] = Field(None, description="Publication date if available")
    supports_claim: Optional[bool] = Field(None, description="Whether this finding supports the claim")


class ValidationResult(BaseModel):
    """Validation result for a single claim from Agent 2."""
    claim_id: str
    original_claim: ExtractedClaim
    validation_status: ValidationStatus = ValidationStatus.PENDING
    internal_critique: str = Field("", description="Agent 2's internal validation notes")
    web_findings: list[WebFinding] = Field(default_factory=list)
    web_consensus: str = Field("", description="Summary of web search consensus")
    modern_updates: str = Field("", description="Notable updates post-cutoff year")


class Agent2Output(BaseModel):
    """Complete output from Agent 2 (Critic & Web Scrounger)."""
    file_id: str
    filename: str
    total_claims_reviewed: int
    verified_count: int = 0
    flagged_count: int = 0
    unsupported_count: int = 0
    results: list[ValidationResult]


# ─── Pipeline State ────────────────────────────────────────────────

class PipelinePhase(str, Enum):
    UPLOAD = "upload"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    SEARCHING = "searching"
    GENERATING_PDF = "generating_pdf"
    COMPLETE = "complete"
    ERROR = "error"


class PipelineEvent(BaseModel):
    """Server-Sent Event payload for pipeline progress streaming."""
    run_id: str
    phase: PipelinePhase
    agent: Optional[str] = None  # "agent1" or "agent2"
    progress: float = Field(0.0, description="Progress percentage 0-100")
    message: str = ""
    data: Optional[dict] = None


class PipelineResult(BaseModel):
    """Final pipeline result."""
    run_id: str
    file_id: str
    filename: str
    agent1_output: Optional[Agent1Output] = None
    agent2_output: Optional[Agent2Output] = None
    pdf_path: Optional[str] = None
    status: PipelinePhase = PipelinePhase.COMPLETE


# ─── API Request / Response ─────────────────────────────────────────

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    size_bytes: int
    message: str = "File uploaded successfully"


class PipelineRunRequest(BaseModel):
    file_id: str
    custom_instructions: Optional[str] = Field("", description="Custom extraction instructions")


class Agent1RunRequest(BaseModel):
    file_id: str
    custom_instructions: Optional[str] = Field("", description="User-provided extraction instructions")


class Agent2RunRequest(BaseModel):
    run_id: str
    file_id: str
    custom_instructions: Optional[str] = Field("", description="User-provided validation instructions")
    claims: Optional[list[ExtractedClaim]] = None


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")
    agent: str = Field("agent1", description="'agent1' or 'agent2'")


class ChatRequest(BaseModel):
    file_id: str
    agent: str = Field("agent1", description="'agent1' or 'agent2'")
    message: str = Field(..., description="User query or instruction")
    history: list[ChatMessage] = Field(default_factory=list)
    current_claims: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    reply: str
    agent: str
    updated_claims: Optional[list[ExtractedClaim]] = None


class PipelineRunResponse(BaseModel):
    run_id: str
    file_id: str
    message: str = "Pipeline started"
    stream_url: str = ""


class ConfigResponse(BaseModel):
    """Returns non-sensitive configuration for the frontend."""
    llm_provider: str
    agent1_model: str
    agent2_model: str
    search_provider: str
    temporal_cutoff_year: int
    strict_rag_mode: bool
    theme: str
    colors: dict

