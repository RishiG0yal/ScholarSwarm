"""
Pipeline Router — Orchestrates Agent 1, Agent 2, SSE streaming, and Interactive Chat.
Allows separate execution of Agent 1 and Agent 2, custom user instructions, and chat.
"""

import os
import asyncio
import json
import uuid
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse

from backend.models.schemas import (
    PipelineRunRequest,
    Agent1RunRequest,
    Agent2RunRequest,
    PipelineRunResponse,
    PipelineResult,
    PipelineEvent,
    PipelinePhase,
    Agent1Output,
    Agent2Output,
    ExtractedClaim,
    ChatRequest,
    ChatResponse,
)
from backend.routers.upload import get_parsed_doc
from backend.agents.agent1_extractor import extract_claims
from backend.agents.agent2_critic import validate_and_research
from backend.services.llm_service import create_llm_service
from backend.services.search_service import create_search_service
from backend.services.pdf_export import generate_pdf_report
from backend.services.chat_service import process_chat

logger = logging.getLogger("rag_pipeline.routers.pipeline")

router = APIRouter()

# In-memory stores
_agent1_outputs: dict[str, Agent1Output] = {}
_pipeline_results: dict[str, PipelineResult] = {}
_event_queues: dict[str, asyncio.Queue] = {}


# ─── Agent 1 Trigger Endpoint ───────────────────────────────────────

@router.post("/pipeline/agent1/run", response_model=PipelineRunResponse)
@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def start_agent1(request: Request, body: Agent1RunRequest):
    """
    Start Agent 1 (Source Extractor) with optional custom instructions.
    Does NOT auto-run Agent 2 — waits for user confirmation.
    """
    config = request.app.state.config

    parsed_doc = get_parsed_doc(body.file_id)
    if not parsed_doc:
        raise HTTPException(status_code=404, detail="File not found. Upload first.")

    errors = config.validate()
    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {'; '.join(errors)}. Check your .env file.",
        )

    run_id = uuid.uuid4().hex[:12]
    _event_queues[run_id] = asyncio.Queue()

    asyncio.create_task(
        _run_agent1_task(config, run_id, parsed_doc.file_id, body.custom_instructions or "")
    )

    return PipelineRunResponse(
        run_id=run_id,
        file_id=body.file_id,
        message="Agent 1 started",
        stream_url=f"/api/pipeline/{run_id}/stream",
    )


async def _run_agent1_task(config, run_id: str, file_id: str, custom_instructions: str):
    """Background task for Agent 1 execution."""
    queue = _event_queues[run_id]
    parsed_doc = get_parsed_doc(file_id)

    if not parsed_doc:
        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.ERROR,
            message="File not found",
        ))
        await queue.put(None)
        return

    try:
        llm = create_llm_service(
            provider=config.llm.provider,
            api_key=config.llm.active_api_key,
            model=config.llm.agent1_model,
        )

        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.PARSING,
            agent="system",
            progress=100,
            message=f"Document parsed: {parsed_doc.total_chunks} chunks from {parsed_doc.total_pages} pages",
        ))

        agent1_output: Agent1Output | None = None

        async for event in extract_claims(
            llm=llm,
            chunks=parsed_doc.chunks,
            file_id=file_id,
            filename=parsed_doc.filename,
            custom_instructions=custom_instructions,
        ):
            if isinstance(event, PipelineEvent):
                await queue.put(event)
            elif isinstance(event, Agent1Output):
                agent1_output = event

        if not agent1_output or not agent1_output.claims:
            await queue.put(PipelineEvent(
                run_id=run_id,
                phase=PipelinePhase.ERROR,
                message="Agent 1 failed to extract any claims",
            ))
            await queue.put(None)
            return

        # Store output
        _agent1_outputs[run_id] = agent1_output

        # Signal completion of Agent 1 — waiting for user to trigger Agent 2
        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.EXTRACTING,
            agent="agent1",
            progress=100,
            message="Agent 1 extraction complete! Review output or chat, then start Agent 2 when ready.",
            data={
                "agent1_complete": True,
                "run_id": run_id,
                "claims": [
                    {
                        "claim_id": c.claim_id,
                        "claim_type": c.claim_type,
                        "claim_text": c.claim_text,
                        "coordinates": c.coordinates,
                        "verbatim_snippet": c.verbatim_snippet,
                        "confidence": c.confidence,
                    }
                    for c in agent1_output.claims
                ],
            },
        ))

        await llm.close()

    except Exception as e:
        logger.error(f"Agent 1 task failed: {e}", exc_info=True)
        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.ERROR,
            message=f"Agent 1 failed: {str(e)}",
        ))
    finally:
        await queue.put(None)


# ─── Agent 2 Trigger Endpoint ───────────────────────────────────────

@router.post("/pipeline/agent2/run", response_model=PipelineRunResponse)
async def start_agent2(request: Request, body: Agent2RunRequest):
    """
    Start Agent 2 (Critic & Web Scrounger) on Agent 1's extracted claims.
    Triggered manually by the user via button.
    """
    config = request.app.state.config

    parsed_doc = get_parsed_doc(body.file_id)
    if not parsed_doc:
        raise HTTPException(status_code=404, detail="File not found")

    run_id = body.run_id or uuid.uuid4().hex[:12]

    # Re-initialize event queue for Agent 2 stream
    _event_queues[run_id] = asyncio.Queue()

    # Determine Agent 1 claims to validate
    agent1_out = _agent1_outputs.get(run_id)
    if body.claims:
        agent1_out = Agent1Output(
            file_id=body.file_id,
            filename=parsed_doc.filename,
            total_claims=len(body.claims),
            claims=body.claims,
        )

    if not agent1_out or not agent1_out.claims:
        raise HTTPException(status_code=400, detail="No extracted claims found for validation.")

    asyncio.create_task(
        _run_agent2_task(config, run_id, parsed_doc.file_id, agent1_out, body.custom_instructions or "")
    )

    return PipelineRunResponse(
        run_id=run_id,
        file_id=body.file_id,
        message="Agent 2 started",
        stream_url=f"/api/pipeline/{run_id}/stream",
    )


async def _run_agent2_task(config, run_id: str, file_id: str, agent1_out: Agent1Output, custom_instructions: str):
    """Background task for Agent 2 execution."""
    queue = _event_queues[run_id]
    parsed_doc = get_parsed_doc(file_id)

    try:
        llm = create_llm_service(
            provider=config.llm.provider,
            api_key=config.llm.active_api_key,
            model=config.llm.agent2_model,
        )
        search_service = create_search_service(
            provider=config.search.provider,
            api_key=config.search.active_api_key,
            cutoff_year=config.pipeline.temporal_cutoff_year,
        )

        agent2_output: Agent2Output | None = None

        async for event in validate_and_research(
            llm=llm,
            search=search_service,
            agent1_output=agent1_out,
            original_chunks=parsed_doc.chunks,
            custom_instructions=custom_instructions,
        ):
            if isinstance(event, PipelineEvent):
                await queue.put(event)
            elif isinstance(event, Agent2Output):
                agent2_output = event

        # Generate PDF report
        pdf_path = None
        if agent2_output:
            try:
                pdf_path = generate_pdf_report(
                    agent2_output=agent2_output,
                    reports_dir=config.reports_dir,
                    run_id=run_id,
                )
                logger.info(f"PDF generated: {pdf_path}")
            except Exception as e:
                logger.error(f"PDF generation failed: {e}")

        # Store final result
        result = PipelineResult(
            run_id=run_id,
            file_id=file_id,
            filename=parsed_doc.filename,
            agent1_output=agent1_out,
            agent2_output=agent2_output,
            pdf_path=pdf_path,
            status=PipelinePhase.COMPLETE,
        )
        _pipeline_results[run_id] = result

        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.COMPLETE,
            agent="system",
            progress=100,
            message="Analysis and validation complete!",
            data={
                "run_id": run_id,
                "pdf_available": pdf_path is not None,
                "verified": agent2_output.verified_count if agent2_output else 0,
                "flagged": agent2_output.flagged_count if agent2_output else 0,
                "unsupported": agent2_output.unsupported_count if agent2_output else 0,
            },
        ))

        await llm.close()
        await search_service.close()

    except Exception as e:
        logger.error(f"Agent 2 task failed: {e}", exc_info=True)
        await queue.put(PipelineEvent(
            run_id=run_id,
            phase=PipelinePhase.ERROR,
            message=f"Agent 2 failed: {str(e)}",
        ))
    finally:
        await queue.put(None)


# ─── Interactive Chat Endpoint ──────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: Request, body: ChatRequest):
    """Interactive chat endpoint for user follow-up instructions or queries."""
    config = request.app.state.config

    parsed_doc = get_parsed_doc(body.file_id)
    if not parsed_doc:
        raise HTTPException(status_code=404, detail="File not found")

    model_name = config.llm.agent1_model if body.agent == "agent1" else config.llm.agent2_model
    llm = create_llm_service(
        provider=config.llm.provider,
        api_key=config.llm.active_api_key,
        model=model_name,
    )

    try:
        response = await process_chat(llm, body, parsed_doc.chunks)
        await llm.close()
        return response
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        await llm.close()
        raise HTTPException(status_code=500, detail=str(e))


# ─── Stream & Result Endpoints ─────────────────────────────────────

@router.get("/pipeline/{run_id}/stream")
async def stream_pipeline(run_id: str):
    """SSE progress stream."""
    queue = _event_queues.get(run_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Stream queue not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            event = await queue.get()
            if event is None:
                yield "event: done\ndata: {}\n\n"
                break
            if isinstance(event, PipelineEvent):
                data = event.model_dump_json()
                yield f"event: progress\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/pipeline/{run_id}/result")
async def get_pipeline_result(run_id: str):
    """Return the complete pipeline result as JSON."""
    result = _pipeline_results.get(run_id)
    if not result:
        # Check if Agent 1 completed
        agent1_out = _agent1_outputs.get(run_id)
        if agent1_out:
            return {
                "run_id": run_id,
                "file_id": agent1_out.file_id,
                "filename": agent1_out.filename,
                "agent1_output": agent1_out.model_dump(),
                "agent2_output": None,
                "pdf_path": None,
                "status": "extracting_complete",
            }
        raise HTTPException(status_code=404, detail="Result not found")

    return result.model_dump()


@router.get("/pipeline/{run_id}/pdf")
async def download_pdf(run_id: str):
    """Download the generated PDF report."""
    result = _pipeline_results.get(run_id)
    if not result or not result.pdf_path or not os.path.exists(result.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not available")

    base_name = os.path.splitext(result.filename)[0]
    safe_filename = "".join(c for c in base_name if c.isalnum() or c in ("-", "_")).strip() or "Report"
    return FileResponse(
        result.pdf_path,
        media_type="application/pdf",
        filename=f"Analysis_of_the_Papers_{safe_filename}_{run_id}.pdf",
    )


@router.get("/config")
async def get_config(request: Request):
    """Return non-sensitive configuration for the frontend."""
    config = request.app.state.config
    return {
        "llm_provider": config.llm.provider,
        "agent1_model": config.llm.agent1_model,
        "agent2_model": config.llm.agent2_model,
        "search_provider": config.search.provider,
        "temporal_cutoff_year": config.pipeline.temporal_cutoff_year,
        "strict_rag_mode": config.pipeline.strict_rag_mode,
        "theme": config.ui.theme_name,
        "colors": {
            "base": config.ui.color_base,
            "borders": config.ui.color_borders,
            "agent1": config.ui.color_agent1,
            "agent2": config.ui.color_agent2,
        },
    }
