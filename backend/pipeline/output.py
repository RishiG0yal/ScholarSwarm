"""
PaperVerify — Stage 7: Output Generation.

Generates three outputs from verified claims:
a) Verified Brief — 1-page summary with page citations
b) Flashcards — Q&A pairs from verified claims
c) Concept Map — cluster claims by embedding similarity
"""
import numpy as np
from models.schemas import (
    VerifiedClaim, Flashcard, FlashcardSet,
    ConceptNode, ConceptEdge, ConceptMap, AnalysisResults,
)
from services.llm import llm_service, AgentError
from pipeline.embeddings import get_claim_embeddings
from utils.logging_util import logger


# ── Brief Generation ─────────────────────────────────────────────────

BRIEF_SYSTEM_PROMPT = """You are an academic summarizer. Write a concise 1-page summary of the research paper based ONLY on the verified claims provided.

RULES:
1. Every sentence in the summary MUST end with a page citation in the format (Page N).
2. Use ONLY the claims provided — do NOT add any information not present in the claims.
3. Organize the summary logically: methodology → findings → limitations.
4. Keep the summary under 400 words.
5. Use clear, academic but accessible language.
6. Preserve exact numbers and statistics from the claims.
7. Output plain text only (no markdown headers or formatting)."""


async def generate_brief(claims: list[VerifiedClaim]) -> str:
    """Generate a 1-page verified brief from claims."""
    if not claims:
        return "No verified claims were found in this document."

    claims_text = "\n".join(
        f"- [{c.type.upper()}] (Page {c.page}): {c.claim}"
        for c in claims
    )

    prompt = f"""Write a 1-page summary based on these verified claims:

{claims_text}

Remember: every sentence must end with (Page N) citing its source."""

    try:
        brief = await llm_service.generate(
            prompt=prompt,
            system_instruction=BRIEF_SYSTEM_PROMPT,
        )
        logger.info(f"Generated brief ({len(brief.split())} words)")
        return brief.strip()
    except AgentError as e:
        logger.error(f"Brief generation failed: {e}")
        # Fallback: concatenate claims as bullet points
        return "\n".join(
            f"• {c.claim} (Page {c.page})"
            for c in claims
        )


# ── Flashcard Generation ─────────────────────────────────────────────

FLASHCARD_SYSTEM_PROMPT = """You are an educational flashcard creator. Generate Q&A flashcards from verified research claims.

RULES:
1. Each flashcard must have a clear question and a concise answer.
2. Every answer MUST include a page citation: (Page N).
3. Questions should test understanding, not just recall.
4. Use ONLY information from the provided claims.
5. Generate 1-2 flashcards per claim (more for complex findings, fewer for simple ones).
6. Preserve exact numbers and statistics in answers.
7. Make questions specific enough that the answer is unambiguous."""


async def generate_flashcards(claims: list[VerifiedClaim]) -> list[Flashcard]:
    """Generate Q&A flashcards from verified claims."""
    if not claims:
        return []

    claims_text = "\n".join(
        f"- CLAIM (Page {c.page}, chunk {c.chunk_id}): {c.claim}"
        for c in claims
    )

    prompt = f"""Generate educational flashcards from these verified claims:

{claims_text}

For each flashcard, provide: question, answer (with page citation), page number, and chunk_id."""

    try:
        result = await llm_service.generate_structured(
            prompt=prompt,
            response_model=FlashcardSet,
            system_instruction=FLASHCARD_SYSTEM_PROMPT,
        )
        logger.info(f"Generated {len(result.flashcards)} flashcards")
        return result.flashcards
    except AgentError as e:
        logger.error(f"Flashcard generation failed: {e}")
        # Fallback: create simple flashcards from claims
        fallback = []
        for c in claims:
            fallback.append(Flashcard(
                question=f"What was found regarding: {c.claim[:50]}...?",
                answer=f"{c.claim} (Page {c.page})",
                page=c.page,
                chunk_id=c.chunk_id,
            ))
        return fallback


# ── Concept Map Generation ───────────────────────────────────────────

def _compute_similarity_matrix(embeddings: list[list[float]]) -> np.ndarray:
    """Compute cosine similarity matrix."""
    arr = np.array(embeddings)
    # Normalize
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = arr / norms
    # Cosine similarity
    return np.dot(normalized, normalized.T)


def _simple_cluster(similarity_matrix: np.ndarray, threshold: float = 0.5) -> list[int]:
    """Simple threshold-based clustering."""
    n = len(similarity_matrix)
    clusters = [-1] * n
    current_cluster = 0

    for i in range(n):
        if clusters[i] != -1:
            continue
        clusters[i] = current_cluster
        for j in range(i + 1, n):
            if clusters[j] == -1 and similarity_matrix[i][j] > threshold:
                clusters[j] = current_cluster
        current_cluster += 1

    return clusters


async def generate_concept_map(
    claims: list[VerifiedClaim],
    session_id: str,
) -> ConceptMap:
    """
    Generate a concept map from verified claims using embedding similarity.

    If < 5 claims, returns a simple list view instead of a full graph.
    """
    if len(claims) < 5:
        # Simple list — no graph needed
        nodes = [
            ConceptNode(
                id=c.chunk_id,
                label=c.claim[:80] + ("..." if len(c.claim) > 80 else ""),
                cluster=0,
                page=c.page,
                claim_type=c.type,
            )
            for c in claims
        ]
        return ConceptMap(nodes=nodes, edges=[], is_simple_list=True)

    # Generate embeddings for claim texts
    claim_texts = [c.claim for c in claims]
    embeddings = get_claim_embeddings(session_id, claim_texts)

    # Compute similarity
    sim_matrix = _compute_similarity_matrix(embeddings)

    # Cluster
    clusters = _simple_cluster(sim_matrix, threshold=0.45)

    # Build nodes
    nodes = []
    for i, claim in enumerate(claims):
        nodes.append(ConceptNode(
            id=claim.chunk_id,
            label=claim.claim[:80] + ("..." if len(claim.claim) > 80 else ""),
            cluster=clusters[i],
            page=claim.page,
            claim_type=claim.type,
        ))

    # Build edges (only for similarity > 0.4 to avoid clutter)
    edges = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            sim = float(sim_matrix[i][j])
            if sim > 0.4:
                edges.append(ConceptEdge(
                    source=claims[i].chunk_id,
                    target=claims[j].chunk_id,
                    similarity=round(sim, 3),
                ))

    logger.info(
        f"Concept map: {len(nodes)} nodes, {len(edges)} edges, "
        f"{max(clusters) + 1 if clusters else 0} clusters"
    )

    return ConceptMap(nodes=nodes, edges=edges, is_simple_list=False)


# ── Full Output Assembly ─────────────────────────────────────────────

async def generate_all_outputs(
    verified_claims: list[VerifiedClaim],
    session_id: str,
    total_extracted: int,
    total_rejected: int,
    quality_warning: str | None,
    document_warnings: list[str],
) -> AnalysisResults:
    """Generate all output artifacts from verified claims."""

    brief = await generate_brief(verified_claims)
    flashcards = await generate_flashcards(verified_claims)
    concept_map = await generate_concept_map(verified_claims, session_id)

    return AnalysisResults(
        session_id=session_id,
        verified_brief=brief,
        flashcards=flashcards,
        concept_map=concept_map,
        verified_claims=verified_claims,
        total_claims_extracted=total_extracted,
        total_claims_verified=len(verified_claims),
        total_claims_rejected=total_rejected,
        quality_warning=quality_warning,
        document_warnings=document_warnings,
    )
