"""
Chat Service — Handles interactive conversation with Agent 1 and Agent 2.
Allows users to ask questions, request personalized refinements, or modify claims.
"""

import json
import logging
from typing import Optional

from backend.models.schemas import ChatRequest, ChatResponse, ExtractedClaim, TextChunk
from backend.services.llm_service import LLMService

logger = logging.getLogger("rag_pipeline.services.chat")

AGENT1_CHAT_PROMPT = """You are AGENT 1 (Source Extractor RAG Assistant). You have analyzed a document and extracted research claims, hypotheses, methodologies, and limitations.

The user is interacting with you to ask questions about the document, request refined extractions, or give personalized instructions.

## CONTEXT:
Document text chunks:
{document_context}

Current extracted claims:
{claims_context}

## RULES:
1. Answer the user's question accurately based ON THE DOCUMENT TEXT provided.
2. If the user asks to add, modify, or refine claims, provide a helpful text reply AND include an updated JSON array of claims inside a ```json ... ``` code block if claim changes are requested.
3. Be helpful, precise, and clear.
"""

AGENT2_CHAT_PROMPT = """You are AGENT 2 (Critic & Web Scrounger Assistant). You validate research claims against source documents and web sources.

The user is asking questions about the validation results, web findings, modern updates, or asking for further clarification.

## CONTEXT:
Current validation & web findings context:
{claims_context}

## RULES:
1. Provide clear, accurate answers explaining the validation status or web research findings.
2. If modern post-2021 updates were found, summarize them.
3. Be informative, objective, and clear.
"""


async def process_chat(
    llm: LLMService,
    req: ChatRequest,
    chunks: list[TextChunk],
) -> ChatResponse:
    """Process an interactive chat message with Agent 1 or Agent 2."""
    doc_context = "\n\n".join(
        f"[Page {c.page_number}, ¶{c.paragraph_number}]: {c.text}"
        for c in chunks[:15]  # Top 15 chunks for context
    )

    claims_context = json.dumps(req.current_claims or [], indent=2)

    if req.agent == "agent2":
        sys_prompt = AGENT2_CHAT_PROMPT.format(claims_context=claims_context)
    else:
        sys_prompt = AGENT1_CHAT_PROMPT.format(
            document_context=doc_context,
            claims_context=claims_context,
        )

    # Build conversation history
    history_str = ""
    for msg in req.history[-6:]:
        history_str += f"\n{msg.role.upper()}: {msg.content}"

    user_prompt = f"{history_str}\nUSER: {req.message}" if history_str else req.message

    try:
        reply_text = await llm.generate(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        # Check if updated claims JSON was embedded in reply
        updated_claims = None
        if "```json" in reply_text:
            try:
                json_part = reply_text.split("```json")[1].split("```")[0].strip()
                claims_data = json.loads(json_part)
                if isinstance(claims_data, list):
                    updated_claims = [
                        ExtractedClaim(
                            claim_id=c.get("claim_id", f"claim_chat_{i}"),
                            claim_type=c.get("claim_type", "claim"),
                            claim_text=c.get("claim_text", ""),
                            coordinates=c.get("coordinates", "[Chat]"),
                            verbatim_snippet=c.get("verbatim_snippet", ""),
                        )
                        for i, c in enumerate(claims_data)
                    ]
            except Exception as e:
                logger.warning(f"Failed to parse chat updated claims JSON: {e}")

        return ChatResponse(
            reply=reply_text,
            agent=req.agent,
            updated_claims=updated_claims,
        )

    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return ChatResponse(
            reply=f"I'm sorry, an error occurred while processing your message: {str(e)}",
            agent=req.agent,
        )
