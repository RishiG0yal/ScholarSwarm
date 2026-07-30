"""
PaperVerify — Stage 4: Agent 1 — Claim Extractor.

Reads chunks and extracts structured claims with:
- Exact preservation of numbers/statistics
- Chunk-level traceability (no claim without a page reference)
- Conflicting statement detection
- Short paper bypass (process whole doc at once)
- Batch processing for long papers
"""
import json
from models.schemas import Chunk, ExtractedClaim, ExtractionResult
from services.llm import llm_service, AgentError, MissingApiKeyError
from config import CHUNK_BATCH_SIZE
from utils.logging_util import logger

EXTRACTOR_SYSTEM_PROMPT = """You are a precise research paper claim extractor. Your job is to extract verifiable claims from academic text.

RULES — follow these EXACTLY:
1. Extract key findings, methodology steps, and stated limitations.
2. Every claim MUST reference a specific chunk_id and page number from the source text.
3. NEVER paraphrase numbers, statistics, percentages, or quantitative results — keep them EXACTLY as stated.
4. If the text contains contradictory statements (e.g., abstract says X but results say Y), extract BOTH claims and set is_conflicting to true.
5. Only extract claims that are explicitly stated in the text — do NOT infer or assume.
6. Classify each claim as:
   - "finding": A result, conclusion, or discovery
   - "limitation": A stated weakness, constraint, or caveat
   - "method": A methodology step, technique, or approach used
7. Set confidence:
   - "high": Claim is clearly and directly stated
   - "medium": Claim requires minor interpretation
   - "low": Claim is ambiguous or indirect
8. If a claim cannot be traced to a specific chunk, DO NOT include it.

Output ONLY valid JSON matching the required schema. Do not include any text outside the JSON."""


def _build_extraction_prompt(chunks: list[Chunk]) -> str:
    """Build the prompt for claim extraction from a batch of chunks."""
    chunks_text = "\n\n".join(
        f"--- CHUNK: {c.chunk_id} | PAGE: {c.page_number} | SECTION: {c.section_guess} ---\n{c.text}"
        for c in chunks
    )

    return f"""Extract all verifiable claims from the following academic text chunks.

For each claim, provide:
- claim: the exact claim text
- type: "finding", "limitation", or "method"
- page: the page number where this claim appears
- chunk_id: the chunk_id where this claim appears
- confidence: "high", "medium", or "low"
- is_conflicting: true if this contradicts another statement in the paper

SOURCE TEXT:
{chunks_text}

Extract all claims as a JSON object with a "claims" array."""


def _fallback_claims_from_chunks(chunks: list[Chunk]) -> list[ExtractedClaim]:
    """Create simple claims from chunk text when the LLM is unavailable."""
    fallback_claims: list[ExtractedClaim] = []
    for chunk in chunks:
        cleaned_text = " ".join(chunk.text.split())
        if not cleaned_text:
            continue
        sentence = cleaned_text[:220]
        fallback_claims.append(
            ExtractedClaim(
                claim=sentence,
                type="finding",
                page=chunk.page_number,
                chunk_id=chunk.chunk_id,
                confidence="medium",
                is_conflicting=False,
            )
        )
    return fallback_claims


async def extract_claims(
    chunks: list[Chunk],
    is_short_paper: bool = False,
) -> list[ExtractedClaim]:
    """
    Extract structured claims from document chunks using the LLM.

    Args:
        chunks: List of text chunks with metadata.
        is_short_paper: If True, process all chunks in a single call.

    Returns:
        List of ExtractedClaim objects.
    """
    if not chunks:
        return []

    all_claims: list[ExtractedClaim] = []

    if is_short_paper:
        # Process entire document in one call
        logger.info("Short paper — extracting claims in single batch")
        batches = [chunks]
    else:
        # Process in batches
        batches = [
            chunks[i:i + CHUNK_BATCH_SIZE]
            for i in range(0, len(chunks), CHUNK_BATCH_SIZE)
        ]
        logger.info(f"Processing {len(batches)} batch(es) of chunks")

    for batch_idx, batch in enumerate(batches):
        try:
            prompt = _build_extraction_prompt(batch)
            result = await llm_service.generate_structured(
                prompt=prompt,
                response_model=ExtractionResult,
                system_instruction=EXTRACTOR_SYSTEM_PROMPT,
            )

            # Filter out claims without valid chunk references
            valid_chunk_ids = {c.chunk_id for c in batch}
            valid_claims = []

            for claim in result.claims:
                if claim.chunk_id in valid_chunk_ids and claim.page > 0:
                    valid_claims.append(claim)
                else:
                    logger.warning(
                        f"Discarded claim with invalid reference: "
                        f"chunk_id='{claim.chunk_id}', page={claim.page}"
                    )

            all_claims.extend(valid_claims)
            logger.info(
                f"Batch {batch_idx + 1}/{len(batches)}: "
                f"extracted {len(valid_claims)} valid claims"
            )

        except MissingApiKeyError as e:
            logger.warning(f"Falling back to local extraction because the API key is missing: {e}")
            fallback_claims = _fallback_claims_from_chunks(batch)
            all_claims.extend(fallback_claims)
            logger.info(
                f"Batch {batch_idx + 1}/{len(batches)}: used fallback extraction for {len(fallback_claims)} claims"
            )
            continue
        except AgentError as e:
            message = str(e)
            if "429" in message or "quota" in message.lower() or "RESOURCE_EXHAUSTED" in message:
                logger.warning(f"Gemini quota exhausted — using fallback extraction: {e}")
                fallback_claims = _fallback_claims_from_chunks(batch)
                all_claims.extend(fallback_claims)
                logger.info(
                    f"Batch {batch_idx + 1}/{len(batches)}: used fallback extraction for {len(fallback_claims)} claims due to quota limits"
                )
                continue
            logger.error(f"Extraction failed for batch {batch_idx + 1}: {e}")
            # Continue with other batches rather than failing entirely
            continue

    logger.info(f"Total claims extracted: {len(all_claims)}")
    return all_claims
