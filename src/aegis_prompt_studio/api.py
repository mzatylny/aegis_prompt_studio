from __future__ import annotations

import secrets
from threading import BoundedSemaphore
from time import perf_counter
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

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
from aegis_prompt_studio.observability import ApiMetrics, configure_json_logger, resolve_request_id
from aegis_prompt_studio.research.pipeline import ResearchPipeline
from aegis_prompt_studio.security.mutations import PromptMutationEngine
from aegis_prompt_studio.security.scanner import PromptSecurityScanner

settings = get_settings()
scanner = PromptSecurityScanner(max_chars=settings.max_input_chars)
mutator = PromptMutationEngine()
pipeline = ResearchPipeline(settings)
research_slots = BoundedSemaphore(settings.max_concurrent_research)
logger = configure_json_logger(__name__, settings.log_level)
metrics = ApiMetrics()

app = FastAPI(
    title="Aegis Prompt Studio API",
    version=__version__,
    description="Prompt-injection analysis and multi-agent research orchestration.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observe_request(request: Request, call_next):
    """Correlate and measure requests without reading or logging their bodies."""
    request_id = resolve_request_id(request.headers.get("X-Request-ID"))
    started = perf_counter()
    status_code = 500
    response: Response | None = None
    metrics.start_request()
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_seconds = perf_counter() - started
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        metrics.finish_request(request.method, route_path, status_code, duration_seconds)
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": route_path,
                "status_code": status_code,
                "duration_ms": round(duration_seconds * 1000, 3),
            },
        )


def require_api_access(x_api_key: str | None) -> None:
    """Require the configured API key without forcing auth in local demo mode."""
    expected = settings.api_access_key
    if not expected:
        return
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": __version__,
        "mode": settings.app_mode,
        "live_enabled": settings.live_enabled,
        "ready": settings.configuration_ready,
    }


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness(response: Response) -> dict[str, str | bool]:
    ready = settings.configuration_ready
    if not ready:
        response.status_code = 503
    return {
        "status": "ready" if ready else "not_ready",
        "mode": settings.app_mode,
        "configured": ready,
    }


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def service_metrics() -> str:
    return metrics.render_prometheus()


@app.post("/v1/security/scan", response_model=SecurityScanResult)
def scan_prompt(
    request: SecurityScanRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> SecurityScanResult:
    require_api_access(x_api_key)
    if len(request.text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Input exceeds configured character limit")
    return scanner.scan(request)


@app.post("/v1/security/mutate", response_model=MutationResult)
def mutate_prompt(
    request: MutationRequest,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> MutationResult:
    require_api_access(x_api_key)
    if len(request.text) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Input exceeds configured character limit")
    return mutator.generate(request.text, request.count)


@app.post("/v1/research/run", response_model=ResearchResult)
def run_research(
    request: ResearchQuestion,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ResearchResult:
    require_api_access(x_api_key)
    if not settings.configuration_ready:
        raise HTTPException(
            status_code=503,
            detail="Live mode requires OPENAI_API_KEY; the service is not ready",
        )
    if len(request.question) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Question exceeds configured character limit")
    if not research_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Research capacity is currently full; retry later",
            headers={"Retry-After": "5"},
        )
    try:
        return pipeline.run(request)
    except Exception as exc:  # pragma: no cover - protects API boundary in live mode
        logger.exception("Research pipeline failed")
        raise HTTPException(
            status_code=502,
            detail="Research pipeline failed. Check server logs for the diagnostic trace.",
        ) from exc
    finally:
        research_slots.release()
