from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from aegis_prompt_studio import __version__
from aegis_prompt_studio.config import get_settings
from aegis_prompt_studio.models import (
    MutationRequest,
    MutationResult,
    ResearchQuestion,
    ResearchResult,
    SecurityScanRequest,
    SecurityScanResult,
)
from aegis_prompt_studio.research.pipeline import ResearchPipeline
from aegis_prompt_studio.security.mutations import PromptMutationEngine
from aegis_prompt_studio.security.scanner import PromptSecurityScanner

settings = get_settings()
scanner = PromptSecurityScanner(max_chars=settings.max_input_chars)
mutator = PromptMutationEngine()
pipeline = ResearchPipeline(settings)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Aegis Prompt Studio API",
    version=__version__,
    description="Prompt-injection analysis and multi-agent research orchestration.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": __version__,
        "mode": settings.app_mode,
        "live_enabled": settings.live_enabled,
    }


@app.post("/v1/security/scan", response_model=SecurityScanResult)
def scan_prompt(request: SecurityScanRequest) -> SecurityScanResult:
    if len(request.text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Input exceeds configured character limit")
    return scanner.scan(request)


@app.post("/v1/security/mutate", response_model=MutationResult)
def mutate_prompt(request: MutationRequest) -> MutationResult:
    if len(request.text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Input exceeds configured character limit")
    return mutator.generate(request.text, request.count)


@app.post("/v1/research/run", response_model=ResearchResult)
def run_research(request: ResearchQuestion) -> ResearchResult:
    if len(request.question) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Question exceeds configured character limit")
    try:
        return pipeline.run(request)
    except Exception as exc:  # pragma: no cover - protects API boundary in live mode
        logger.exception("Research pipeline failed")
        raise HTTPException(
            status_code=502,
            detail="Research pipeline failed. Check server logs for the diagnostic trace.",
        ) from exc
