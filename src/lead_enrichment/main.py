from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import anthropic
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .enrichment import _write_to_gcs_failed, enrich_lead
from .models import EnrichedLeadResponse, LeadWebhookPayload

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── App lifecycle ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
    app.state.anthropic_client = anthropic.Anthropic(api_key=api_key)
    logger.info("Anthropic client initialized")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Lead Enrichment API",
    description=(
        "Webhook-driven lead enrichment pipeline for lending and financial services. "
        "Classifies loan intent, investor experience, and generates personalized outreach "
        "using LLM inference with schema-validated structured output."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Dependencies ───────────────────────────────────────────────────────────────


def get_anthropic_client(request: Request) -> anthropic.Anthropic:
    client: anthropic.Anthropic = request.app.state.anthropic_client
    return client


AnthropicDep = Annotated[anthropic.Anthropic, Depends(get_anthropic_client)]


# ── Exception handlers ─────────────────────────────────────────────────────────


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ai_output_validation_failed",
            "detail": exc.errors(),
            "message": (
                "The LLM response did not conform to the required output schema. "
                "The enrichment request was rejected by the AI governance layer."
            ),
        },
    )


# ── Routes ─────────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/enrich",
    response_model=EnrichedLeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Enrich a raw lead webhook payload",
    description=(
        "Accepts a raw lead payload, sends it to an LLM for classification and "
        "personalization, validates the structured output, and returns an enriched "
        "event formatted for downstream CDP or marketing automation ingestion."
    ),
)
async def enrich_lead_endpoint(
    payload: LeadWebhookPayload,
    client: AnthropicDep,
) -> EnrichedLeadResponse:
    try:
        result = enrich_lead(payload, client)
    except ValueError as e:
        _write_to_gcs_failed(payload, "llm_parse_error", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "llm_parse_error", "message": str(e)},
        )
    except anthropic.APIError as e:
        logger.error("Anthropic API error for lead %s: %s", payload.lead_id, e)
        _write_to_gcs_failed(payload, "upstream_api_error", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "upstream_api_error", "message": str(e)},
        )

    return result
