"""
Agent 2: Critic & Web Scrounger — 3-Phase Validation Agent.

Phase 1: Internal Critique — Validates Agent 1's claims against original text.
Phase 2: Constrained Web Search — Searches for corroboration with temporal/domain filters.
Phase 3: Report Synthesis — Compiles validated results for PDF export.

This agent has access to web search and uses a separate LLM instance.
"""

import json
import logging
from typing import AsyncGenerator, Optional

from backend.models.schemas import (
    Agent1Output,
    Agent2Output,
    ExtractedClaim,
    ValidationResult,
    ValidationStatus,
    WebFinding,
    TextChunk,
    PipelineEvent,
    PipelinePhase,
)
from backend.services.llm_service import LLMService
from backend.services.search_service import SearchService

logger = logging.getLogger("rag_pipeline.agents.critic")


# ── System Prompts ──────────────────────────────────────────────────

CRITIQUE_SYSTEM_PROMPT = """You are a CRITICAL VALIDATION AGENT. Your job is to verify whether extracted claims are accurately supported by the original source text.

## YOUR TASK:
For each claim, compare it against the original document text chunks and determine:
1. Is the claim accurately represented? (no exaggeration, no misinterpretation)
2. Is the verbatim snippet actually present in the source text?
3. Are the coordinates (page/paragraph) correct?

## OUTPUT FORMAT:
Return a JSON array of objects, each with:
- "claim_id": the ID of the claim being validated
- "status": one of "verified", "discrepancy_flagged", "unsupported"
- "critique": a brief explanation of your validation decision (1-2 sentences)
- "suggested_correction": if discrepancy found, what the claim should say (or null)

Return ONLY valid JSON. No explanations outside the JSON.
"""

WEB_QUERY_SYSTEM_PROMPT = """You are a SEARCH QUERY GENERATOR. Given a verified claim from a research document, generate a precise, targeted web search query to find corroborating or contradicting evidence.

## RULES:
1. The query must be SPECIFIC to the claim — no broad or generic searches.
2. Focus on finding peer-reviewed research, academic sources, and authoritative publications.
3. Include key technical terms, author names, or specific values from the claim.
4. Keep the query concise (under 15 words).

## OUTPUT FORMAT:
Return a JSON object with:
- "query": the search query string
- "key_terms": array of the most important terms in the query

Return ONLY valid JSON.
"""

SYNTHESIS_SYSTEM_PROMPT = """You are a RESEARCH SYNTHESIS AGENT. Given a claim from a document and web search results about that claim, provide a concise synthesis.

## YOUR TASK:
1. Determine the web consensus: Do the search results support, contradict, or add nuance to the claim?
2. Identify any modern updates (research published after 2021) that are relevant.
3. Assess whether each search result supports or contradicts the claim.

## OUTPUT FORMAT:
Return a JSON object with:
- "web_consensus": a 2-3 sentence summary of what web sources say about this claim
- "modern_updates": any notable recent findings or updates (or "No significant updates found")
- "findings_assessment": array of objects, each with:
  - "source_index": index of the search result (0-based)
  - "supports_claim": true/false/null
  - "relevance_note": brief note on how this source relates

Return ONLY valid JSON.
"""


# ── Phase 1: Internal Critique ──────────────────────────────────────

async def _run_internal_critique(
    llm: LLMService,
    claims: list[ExtractedClaim],
    original_chunks: list[TextChunk],
    file_id: str,
) -> dict[str, dict]:
    """
    Phase 1: Validate each claim against the original text chunks.
    Returns a mapping of claim_id -> critique data.
    """
    logger.info(f"Phase 1: Internal critique of {len(claims)} claims")

    # Format the original text for the LLM
    chunk_text = "\n\n".join(
        f"[Page {c.page_number}, Paragraph {c.paragraph_number}]: {c.text}"
        for c in original_chunks
    )

    claims_json = json.dumps(
        [
            {
                "claim_id": c.claim_id,
                "claim_text": c.claim_text,
                "coordinates": c.coordinates,
                "verbatim_snippet": c.verbatim_snippet,
            }
            for c in claims
        ],
        indent=2,
    )

    user_prompt = (
        f"## ORIGINAL DOCUMENT TEXT:\n{chunk_text}\n\n"
        f"## EXTRACTED CLAIMS TO VALIDATE:\n{claims_json}"
    )

    try:
        response = await llm.generate(
            system_prompt=CRITIQUE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=4096,
            response_format="json",
        )

        critique_data = _parse_json(response)
        if isinstance(critique_data, list):
            return {item["claim_id"]: item for item in critique_data if "claim_id" in item}
        return {}

    except Exception as e:
        logger.error(f"Phase 1 critique failed: {e}")
        return {}


# ── Phase 2: Constrained Web Search ────────────────────────────────

async def _run_web_search_for_claim(
    llm: LLMService,
    search: SearchService,
    claim: ExtractedClaim,
) -> tuple[list[WebFinding], str, str]:
    """
    Phase 2: Generate a search query and execute web search for a claim.
    Returns (web_findings, web_consensus, modern_updates).
    """
    # Step 1: Generate targeted search query
    query_prompt = (
        f"Generate a search query for this research claim:\n"
        f"Claim: {claim.claim_text}\n"
        f"Type: {claim.claim_type}\n"
        f"Context: {claim.verbatim_snippet}"
    )

    try:
        query_response = await llm.generate(
            system_prompt=WEB_QUERY_SYSTEM_PROMPT,
            user_prompt=query_prompt,
            temperature=0.3,
            max_tokens=256,
            response_format="json",
        )

        query_data = _parse_json(query_response)
        if isinstance(query_data, dict):
            search_query = query_data.get("query", claim.claim_text[:100])
        else:
            search_query = claim.claim_text[:100]

    except Exception:
        search_query = claim.claim_text[:100]

    # Step 2: Execute web search
    try:
        raw_results = await search.search(query=search_query, max_results=5)
    except Exception as e:
        logger.error(f"Web search failed for claim {claim.claim_id}: {e}")
        return [], "Web search unavailable", "N/A"

    if not raw_results:
        return [], "No web results found", "No modern updates available"

    # Step 3: Synthesize findings
    web_findings: list[WebFinding] = []
    for r in raw_results:
        web_findings.append(
            WebFinding(
                query_used=search_query,
                source_url=r.get("url", ""),
                source_title=r.get("title", ""),
                source_domain=r.get("domain", ""),
                snippet=r.get("snippet", ""),
                published_date=r.get("published_date"),
                supports_claim=None,  # Will be assessed by synthesis
            )
        )

    # Step 4: LLM synthesis of search results
    synthesis_prompt = (
        f"Claim: {claim.claim_text}\n\n"
        f"Search Results:\n"
        + "\n".join(
            f"[{i}] {r.source_title} ({r.source_domain}): {r.snippet}"
            for i, r in enumerate(web_findings)
        )
    )

    try:
        synthesis_response = await llm.generate(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=synthesis_prompt,
            temperature=0.2,
            max_tokens=1024,
            response_format="json",
        )

        synthesis_data = _parse_json(synthesis_response)
        if isinstance(synthesis_data, dict):
            web_consensus = synthesis_data.get("web_consensus", "")
            modern_updates = synthesis_data.get("modern_updates", "")

            # Update supports_claim for each finding
            assessments = synthesis_data.get("findings_assessment", [])
            for assessment in assessments:
                idx = assessment.get("source_index", -1)
                if 0 <= idx < len(web_findings):
                    web_findings[idx].supports_claim = assessment.get("supports_claim")
        else:
            web_consensus = "Synthesis unavailable"
            modern_updates = ""

    except Exception as e:
        logger.warning(f"Synthesis failed for claim {claim.claim_id}: {e}")
        web_consensus = "Synthesis unavailable"
        modern_updates = ""

    return web_findings, web_consensus, modern_updates


# ── Main Agent 2 Pipeline ──────────────────────────────────────────

async def validate_and_research(
    llm: LLMService,
    search: SearchService,
    agent1_output: Agent1Output,
    original_chunks: list[TextChunk],
    custom_instructions: str = "",
) -> AsyncGenerator[PipelineEvent | Agent2Output, None]:
    """
    Run Agent 2: Full validation and web research pipeline.

    Yields PipelineEvents for progress streaming, then yields the final Agent2Output.
    """
    file_id = agent1_output.file_id
    claims = agent1_output.claims
    total_claims = len(claims)

    logger.info(f"Agent 2 starting: {total_claims} claims to validate")
    if custom_instructions:
        logger.info(f"  Custom instructions for Agent 2: '{custom_instructions[:100]}...'")

    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.VALIDATING,
        agent="agent2",
        progress=0,
        message=f"Phase 1: Internal critique of {total_claims} claims",
    )

    # ── Phase 1: Internal Critique ──
    critique_map = await _run_internal_critique(llm, claims, original_chunks, file_id)

    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.VALIDATING,
        agent="agent2",
        progress=20,
        message=f"Phase 1 complete: {len(critique_map)} claims critiqued",
    )

    # ── Phase 2: Web Search ──
    results: list[ValidationResult] = []
    verified_count = 0
    flagged_count = 0
    unsupported_count = 0

    for idx, claim in enumerate(claims):
        claim_num = idx + 1
        progress = 20 + (claim_num / total_claims) * 60  # 20-80% range

        # Get critique status
        critique = critique_map.get(claim.claim_id, {})
        status_str = critique.get("status", "verified")
        critique_text = critique.get("critique", "No internal critique available")

        if status_str == "discrepancy_flagged":
            status = ValidationStatus.DISCREPANCY
            flagged_count += 1
        elif status_str == "unsupported":
            status = ValidationStatus.UNSUPPORTED
            unsupported_count += 1
        else:
            status = ValidationStatus.VERIFIED
            verified_count += 1

        yield PipelineEvent(
            run_id=file_id,
            phase=PipelinePhase.SEARCHING,
            agent="agent2",
            progress=progress,
            message=f"Searching web for claim {claim_num}/{total_claims}: "
                    f"{claim.claim_text[:60]}...",
        )

        # Web search (only for verified/discrepancy claims, skip clearly unsupported)
        web_findings = []
        web_consensus = ""
        modern_updates = ""

        if status != ValidationStatus.UNSUPPORTED:
            web_findings, web_consensus, modern_updates = (
                await _run_web_search_for_claim(llm, search, claim)
            )

        results.append(
            ValidationResult(
                claim_id=claim.claim_id,
                original_claim=claim,
                validation_status=status,
                internal_critique=critique_text,
                web_findings=web_findings,
                web_consensus=web_consensus,
                modern_updates=modern_updates,
            )
        )

    # ── Phase 3: Compile Results ──
    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.GENERATING_PDF,
        agent="agent2",
        progress=85,
        message="Phase 3: Compiling final report...",
    )

    output = Agent2Output(
        file_id=file_id,
        filename=agent1_output.filename,
        total_claims_reviewed=total_claims,
        verified_count=verified_count,
        flagged_count=flagged_count,
        unsupported_count=unsupported_count,
        results=results,
    )

    yield PipelineEvent(
        run_id=file_id,
        phase=PipelinePhase.GENERATING_PDF,
        agent="agent2",
        progress=100,
        message=(
            f"✓ Validation complete: {verified_count} verified, "
            f"{flagged_count} flagged, {unsupported_count} unsupported"
        ),
        data={
            "verified": verified_count,
            "flagged": flagged_count,
            "unsupported": unsupported_count,
        },
    )

    logger.info(
        f"Agent 2 complete: {verified_count}V / {flagged_count}F / {unsupported_count}U"
    )
    yield output


# ── Utility ─────────────────────────────────────────────────────────

def _parse_json(text: str):
    """Parse JSON from LLM response, handling common edge cases."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse error: {text[:200]}")
        return {}
