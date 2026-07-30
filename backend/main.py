"""
RAG Validation Pipeline — FastAPI Application Entry Point.

Serves the two-agent pipeline API and the Neo-Brutalism frontend.
Start with: uvicorn backend.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import load_config
from backend.routers import upload, pipeline

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-8s │ %(message)s",
)
logger = logging.getLogger("rag_pipeline")


# ── Application Lifespan ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    config = load_config()
    app.state.config = config

    # Validate configuration
    errors = config.validate()
    if errors:
        for err in errors:
            logger.warning(f"⚠  Config: {err}")
        logger.warning(
            "Pipeline will NOT function until API keys are provided in .env"
        )
    else:
        logger.info(f"✓  LLM Provider : {config.llm.provider}")
        logger.info(f"✓  Agent 1 Model: {config.llm.agent1_model}")
        logger.info(f"✓  Agent 2 Model: {config.llm.agent2_model}")
        logger.info(f"✓  Search       : {config.search.provider}")

    logger.info(f"✓  Uploads dir  : {config.upload_dir}")
    logger.info(f"✓  Reports dir  : {config.reports_dir}")
    logger.info("═══════════════════════════════════════════════════")
    logger.info("  RAG VALIDATION PIPELINE — READY")
    logger.info("═══════════════════════════════════════════════════")

    yield  # App is running

    logger.info("Shutting down RAG Validation Pipeline...")


# ── FastAPI App ─────────────────────────────────────────────────────
app = FastAPI(
    title="RAG Validation Pipeline",
    description="Two-Agent RAG & Validation system with Neo-Brutalism UI",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])


# ── Health Check ────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "RAG Validation Pipeline"}


# ── Static Frontend ────────────────────────────────────────────────
# Serve the frontend directory at root — MUST BE LAST so API routes take priority
import os

_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

