"""
Agent 1: Source Extractor — Strict RAG Agent.

Processes text chunks from uploaded documents and extracts claims,
hypotheses, methodologies, and limitations with coordinate mapping.

CRITICAL: This agent operates in strict RAG mode — it ONLY uses information
explicitly present in the provided text chunks. No external knowledge,
no pre-trained memory, no web search.
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from backend.models.schemas import (
    ExtractedClaim,
    Agent1Output,
    TextChunk,
    PipelineEvent,
    PipelinePhase,
)
from backend.services.llm_service import LLMService

logger = logging.getLogger("rag_pipeline.agents.extractor")


# ── System Prompt ───────────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a STRICT DOCUMENT EXTRACTION AGENT. Your ONLY function is to extract information that is EXPLICITLY stated in the provided text chunks.

## ABSOLUTE RULES:
1. You MUST NOT use any pre-trained knowledge or information not present in the text.
2. You MUST NOT infer, assume, or generate any claims beyond what is directly stated.
3. You MUST provide exact verbatim text snippets as evidence for every extraction.
4. You MUST include precise coordinate mapping for every item.

## EXTRACTION TARGETS:
Extract the following categories of information:
- **claims**: Factual assertions, conclusions, or findings stated by the author(s).
- **hypotheses**: Proposed explanations or predictions being tested.
- **methodologies**: Methods, techniques, experimental designs, or analytical approaches described.
- **limitations**: Acknowledged weaknesses, constraints, or caveats.

## OUTPUT FORMAT:
Return a JSON array of objects, each with these fields:
- "claim_type": one of "claim", "hypothesis", "methodology", "limitation"
- "claim_text": a clear, concise statement of the extracted item
- "coordinates": the exact source location as "[Page X, Paragraph Y]"
- "verbatim_snippet": the exact text from the document (word-for-word, up to 200 chars)
- "confidence": a float 0.0 to 1.0 indicating how clearly this was stated

Return ONLY valid JSON. No explanations, no markdown formatting, no preamble.
"""


# ── Chunk Batching ──────────────────────────────────────────────────

def _format_chunks_for_prompt(chunks: list[TextChunk]) -> str:
    """Format text chunks into a structured prompt for the LLM."""
    lines = ["## DOCUMENT TEXT CHUNKS\n"]
    for chunk in chunks:
        lines.append(
            f"--- [Page {chunk.page_number}, Paragraph {chunk.paragraph_number}] ---\n"
            f"{chunk.text}\n"
        )
    return "\n".join(lines)


def _batch_chunks(chunks: list[TextChunk], max_chars: int = 12000) -> list[list[TextChunk]]:
    """Split chunks into batches that fit within token limits."""
    batches: list[list[TextChunk]] = []
    current_batch: list[TextChunk] = []
    current_size = 0

    for chunk in chunks:
        chunk_size = len(chunk.text) + 50  # overhead for metadata
        if current_size + chunk_size > max_chars and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0
        current_batch.append(chunk)
        current_size += chunk_size

    if current_batch:
        batches.append(current_batch)

    return batches


# ── Extraction Logic ────────────────────────────────────────────────

async def extract_claims(
    llm: LLMService,
    chunks: list[TextChunk],
    file_id: str,
    filename: str,
    custom_instructions: str = "",
) -> AsyncGenerator[PipelineEvent | Agent1Output, None]:
    """
    Run Agent 1: Extract claims from document chunks using strict RAG.

    Yields PipelineEvents for progress streaming, then yields the final Agent1Output.
    """
    logger.info(f"Agent 1 starting extraction for '{filename}' ({len(chunks)} chunks)")
    if custom_instructions:
        logger.info(f"  Custom instructions: '{custom_instructions[:100]}...'")

    all_claims: list[ExtractedClaim] = []
    batches = _batch_chunks(chunks)
    total_batches = len(batches)

    system_prompt = EXTRACTION_SYSTEM_PROMPT
    if custom_instructions and custom_instructions.strip():
        system_prompt += f"\n\n## USER CUSTOM INSTRUCTIONS:\n{custom_instructions.strip()}\nFollow these user instructions closely while extracting from the chunks."

    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.EXTRACTING,
        agent="agent1",
        progress=0,
        message=f"Starting extraction: {len(chunks)} chunks in {total_batches} batches",
    )

    for batch_idx, batch in enumerate(batches):
        batch_num = batch_idx + 1
        progress = (batch_num / total_batches) * 100

        yield PipelineEvent(
            run_id=file_id,
            phase=PipelinePhase.EXTRACTING,
            agent="agent1",
            progress=progress * 0.9,  # Reserve 10% for final assembly
            message=f"Processing batch {batch_num}/{total_batches} "
                    f"(Pages {batch[0].page_number}-{batch[-1].page_number})",
        )

        # Format chunks and send to LLM
        user_prompt = _format_chunks_for_prompt(batch)

        try:
            response = await llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=4096,
                response_format="json",
            )

            # Parse the JSON response
            claims_data = _parse_llm_response(response)

            for claim_data in claims_data:
                claim_id = f"claim_{file_id}_{uuid.uuid4().hex[:8]}"
                claim = ExtractedClaim(
                    claim_id=claim_id,
                    claim_type=claim_data.get("claim_type", "claim"),
                    claim_text=claim_data.get("claim_text", ""),
                    coordinates=claim_data.get("coordinates", "[Unknown]"),
                    verbatim_snippet=claim_data.get("verbatim_snippet", "")[:300],
                    confidence=float(claim_data.get("confidence", 0.8)),
                )
                all_claims.append(claim)

            logger.info(
                f"  Batch {batch_num}: extracted {len(claims_data)} claims"
            )

            # Pause briefly between batches to respect Groq rate limits
            if batch_num < total_batches:
                import asyncio
                await asyncio.sleep(2.5)

        except Exception as e:
            logger.error(f"  Batch {batch_num} failed: {e}")
            yield PipelineEvent(
                run_id=file_id,
                phase=PipelinePhase.EXTRACTING,
                agent="agent1",
                progress=progress,
                message=f"⚠ Batch {batch_num} error: {str(e)[:100]}",
            )

    # Final output
    output = Agent1Output(
        file_id=file_id,
        filename=filename,
        total_claims=len(all_claims),
        claims=all_claims,
    )

    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.EXTRACTING,
        agent="agent1",
        progress=100,
        message=f"✓ Extraction complete: {len(all_claims)} claims extracted",
        data={"total_claims": len(all_claims)},
    )

    logger.info(f"Agent 1 complete: {len(all_claims)} total claims extracted")
    yield output


def _parse_llm_response(response: str) -> list[dict]:
    """Parse JSON response from the LLM, handling edge cases."""
    text = response.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Handle wrapped responses like {"claims": [...]}
            for key in ("claims", "results", "extractions", "items"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON: {e}")
        logger.debug(f"Raw response: {text[:500]}")
        return []
