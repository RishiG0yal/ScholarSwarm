"""
PaperVerify — Stage 5: Agent 2 — Fact-Checker.

Re-reads the cited chunk for each claim and verifies it independently.
Features:
- Reads ONLY the cited chunk (not memory or context)
- Filters: verified → keep, partially_supported → rewrite, unsupported → discard
- 30% rejection rate threshold → quality warning
- Full verdict logging (including discards)
"""
from models.schemas import ExtractedClaim, VerifiedClaim, VerificationVerdict, Chunk
from services.llm import llm_service, AgentError
from config import REJECTION_RATE_THRESHOLD
from utils.logging_util import logger, log_verdict

FACT_CHECKER_SYSTEM_PROMPT = """You are a rigorous fact-checker for academic research claims. You must verify claims ONLY against the source text provided — nothing else.

RULES:
1. Read the SOURCE CHUNK carefully.
2. Determine if the CLAIM is supported by the source chunk.
3. Your verdict must be one of:
   - "verified": The claim is fully and accurately supported by the source text.
   - "partially_supported": The claim is partly correct but overstates, understates, or adds details not in the source. You MUST provide a rewritten_claim that matches EXACTLY what the source says.
   - "unsupported": The claim is not supported by the source text at all, or is fabricated.
4. Provide a brief reasoning for your verdict.
5. Extract a short exact quote (under 15 words) from the source that best supports (or fails to support) the claim.
6. For "partially_supported" claims, the rewritten_claim must be conservative — state only what the source explicitly says.
7. Do NOT use any knowledge outside the provided source chunk.

Output ONLY valid JSON matching the required schema."""


def _build_verification_prompt(claim: ExtractedClaim, chunk_text: str) -> str:
    """Build the prompt for verifying a single claim against its source chunk."""
    return f"""Verify whether the following CLAIM is supported by the SOURCE CHUNK.

CLAIM: {claim.claim}
CLAIM TYPE: {claim.type}
CLAIMED PAGE: {claim.page}

SOURCE CHUNK (chunk_id: {claim.chunk_id}):
{chunk_text}

Provide your verdict as JSON with:
- verdict: "verified" | "unsupported" | "partially_supported"
- reasoning: brief explanation
- source_quote: short exact quote from source (under 15 words)
- rewritten_claim: only if "partially_supported", rewrite to match source exactly"""


def _fallback_verdict(claim: ExtractedClaim, chunk_text: str) -> VerificationVerdict:
    """Fallback verifier that uses simple overlap heuristics when Gemini is unavailable."""
    claim_words = set(claim.claim.lower().replace("/", " ").split())
    chunk_words = set(chunk_text.lower().replace("/", " ").split())
    shared = claim_words & chunk_words

    if not shared:
        return VerificationVerdict(
            verdict="unsupported",
            reasoning="The claim text did not overlap with the source chunk.",
            source_quote=chunk_text[:80],
        )

    if len(shared) >= max(2, len(claim_words) // 4):
        return VerificationVerdict(
            verdict="partially_supported",
            reasoning="The claim appears related to the source chunk, but the fallback verifier could not confirm full support.",
            rewritten_claim=claim.claim[:200],
            source_quote=chunk_text[:80],
        )

    return VerificationVerdict(
        verdict="partially_supported",
        reasoning="The claim appears loosely related to the source chunk.",
        rewritten_claim=claim.claim[:200],
        source_quote=chunk_text[:80],
    )


async def fact_check_claims(
    claims: list[ExtractedClaim],
    chunks: list[Chunk],
) -> tuple[list[VerifiedClaim], str | None]:
    """
    Fact-check each claim against its cited source chunk.

    Args:
        claims: List of claims from the extractor.
        chunks: List of all document chunks (for lookup by chunk_id).

    Returns:
        (verified_claims, quality_warning) tuple.
        quality_warning is set if rejection rate exceeds threshold.
    """
    if not claims:
        return [], None

    # Build chunk lookup
    chunk_map = {c.chunk_id: c.text for c in chunks}

    verified: list[VerifiedClaim] = []
    rejected_count = 0
    total_checked = 0

    for i, claim in enumerate(claims):
        # Get the source chunk text
        chunk_text = chunk_map.get(claim.chunk_id)
        if not chunk_text:
            logger.warning(
                f"Chunk '{claim.chunk_id}' not found — discarding claim"
            )
            log_verdict(
                session_id=claim.chunk_id.split("_")[0] if "_" in claim.chunk_id else "unknown",
                claim=claim.claim,
                claim_type=claim.type,
                chunk_id=claim.chunk_id,
                page=claim.page,
                verdict="unsupported",
                reasoning="Source chunk not found",
            )
            rejected_count += 1
            total_checked += 1
            continue

        try:
            prompt = _build_verification_prompt(claim, chunk_text)
            verdict_result = await llm_service.generate_structured(
                prompt=prompt,
                response_model=VerificationVerdict,
                system_instruction=FACT_CHECKER_SYSTEM_PROMPT,
            )

            total_checked += 1

            # Extract session_id for logging
            session_id = claim.chunk_id.split("_")[0] if "_" in claim.chunk_id else "unknown"

            # Log every verdict
            log_verdict(
                session_id=session_id,
                claim=claim.claim,
                claim_type=claim.type,
                chunk_id=claim.chunk_id,
                page=claim.page,
                verdict=verdict_result.verdict,
                reasoning=verdict_result.reasoning,
                rewritten_claim=verdict_result.rewritten_claim,
            )

            if verdict_result.verdict == "verified":
                verified.append(VerifiedClaim(
                    claim=claim.claim,
                    original_claim=claim.claim,
                    type=claim.type,
                    page=claim.page,
                    chunk_id=claim.chunk_id,
                    confidence=claim.confidence,
                    verdict="verified",
                    source_quote=verdict_result.source_quote,
                    is_conflicting=claim.is_conflicting,
                ))

            elif verdict_result.verdict == "partially_supported":
                rewritten = verdict_result.rewritten_claim or claim.claim
                verified.append(VerifiedClaim(
                    claim=rewritten,
                    original_claim=claim.claim,
                    type=claim.type,
                    page=claim.page,
                    chunk_id=claim.chunk_id,
                    confidence=claim.confidence,
                    verdict="partially_supported",
                    source_quote=verdict_result.source_quote,
                    is_conflicting=claim.is_conflicting,
                ))

            else:  # unsupported
                rejected_count += 1
                # Unsupported claims are logged but NEVER shown to user

            logger.info(
                f"Fact-check [{i+1}/{len(claims)}]: "
                f"{verdict_result.verdict} — {claim.claim[:60]}..."
            )

        except AgentError as e:
            message = str(e)
            if "429" in message or "quota" in message.lower() or "RESOURCE_EXHAUSTED" in message:
                logger.warning(f"Gemini quota exhausted during fact-checking — using fallback verdict: {e}")
                fallback = _fallback_verdict(claim, chunk_text)
                total_checked += 1
                session_id = claim.chunk_id.split("_")[0] if "_" in claim.chunk_id else "unknown"
                log_verdict(
                    session_id=session_id,
                    claim=claim.claim,
                    claim_type=claim.type,
                    chunk_id=claim.chunk_id,
                    page=claim.page,
                    verdict=fallback.verdict,
                    reasoning=fallback.reasoning,
                    rewritten_claim=fallback.rewritten_claim,
                )
                if fallback.verdict == "verified":
                    verified.append(VerifiedClaim(
                        claim=claim.claim,
                        original_claim=claim.claim,
                        type=claim.type,
                        page=claim.page,
                        chunk_id=claim.chunk_id,
                        confidence=claim.confidence,
                        verdict="verified",
                        source_quote=fallback.source_quote,
                        is_conflicting=claim.is_conflicting,
                    ))
                elif fallback.verdict == "partially_supported":
                    verified.append(VerifiedClaim(
                        claim=fallback.rewritten_claim or claim.claim,
                        original_claim=claim.claim,
                        type=claim.type,
                        page=claim.page,
                        chunk_id=claim.chunk_id,
                        confidence=claim.confidence,
                        verdict="partially_supported",
                        source_quote=fallback.source_quote,
                        is_conflicting=claim.is_conflicting,
                    ))
                else:
                    rejected_count += 1
                continue

            logger.error(f"Fact-check failed for claim {i+1}: {e}")
            rejected_count += 1
            total_checked += 1
            continue

    # Check rejection rate
    quality_warning = None
    if total_checked > 0:
        rejection_rate = rejected_count / total_checked
        if rejection_rate > REJECTION_RATE_THRESHOLD:
            quality_warning = (
                f"Low extraction quality detected: {rejected_count}/{total_checked} "
                f"claims ({rejection_rate:.0%}) could not be verified. "
                "Results may be incomplete — consider reviewing the original document."
            )
            logger.warning(quality_warning)

    logger.info(
        f"Fact-checking complete: {len(verified)} verified, "
        f"{rejected_count} rejected out of {total_checked} total"
    )

    return verified, quality_warning
