from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

import anthropic
from google.cloud import storage

from .models import (
    EnrichedLeadResponse,
    EnrichmentMetadata,
    LeadWebhookPayload,
    LLMClassification,
)
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 512
GCS_FAILED_LEADS_BUCKET = os.getenv("GCS_FAILED_LEADS_BUCKET")


def _write_to_gcs_failed(
    payload: LeadWebhookPayload,
    error_type: str,
    error_detail: str,
) -> None:
    """Write a failed lead to GCS for later review. Non-fatal: logs a warning on failure."""
    if not GCS_FAILED_LEADS_BUCKET:
        logger.warning(
            "GCS_FAILED_LEADS_BUCKET not set, skipping dead-letter write for %s",
            payload.lead_id,
        )
        return

    try:
        blob_path = f"leads/failed/{payload.lead_id}.json"
        document = {
            "payload": payload.model_dump(exclude_none=True),
            "error_type": error_type,
            "error_detail": error_detail,
            "failed_at": datetime.now(UTC).isoformat(),
        }
        client = storage.Client()
        bucket = client.bucket(GCS_FAILED_LEADS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(document, default=str),
            content_type="application/json",
        )
        logger.info(
            "Wrote failed lead %s to gs://%s/%s",
            payload.lead_id,
            GCS_FAILED_LEADS_BUCKET,
            blob_path,
        )
    except Exception:
        logger.warning(
            "Failed to write dead-letter for lead %s to GCS",
            payload.lead_id,
            exc_info=True,
        )


def _parse_llm_response(raw_text: str) -> LLMClassification:
    """
    Parse and validate the LLM's JSON response against LLMClassification.
    Raises ValidationError if the output doesn't conform — this is intentional.
    That exception surfaces as a 422 to the caller, signalling AI governance failure.
    """
    try:
        data = json.loads(raw_text.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON output: {e}\n\nRaw: {raw_text[:500]}")

    return LLMClassification.model_validate(data)


def enrich_lead(
    payload: LeadWebhookPayload,
    client: anthropic.Anthropic,
) -> EnrichedLeadResponse:
    lead_dict = payload.model_dump(exclude_none=True)
    user_prompt = build_user_prompt(lead_dict)

    logger.info("Sending lead %s to %s for classification", payload.lead_id, MODEL)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    block = response.content[0]
    if not hasattr(block, "text"):
        raise ValueError(f"Expected TextBlock, got {type(block).__name__}")
    raw_text: str = block.text
    logger.debug("Raw LLM response for lead %s: %s", payload.lead_id, raw_text)

    classification = _parse_llm_response(raw_text)

    return EnrichedLeadResponse(
        lead_id=payload.lead_id,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        raw=payload,
        loan_type=classification.loan_type,
        investor_experience=classification.investor_experience,
        urgency_score=classification.urgency_score,
        outreach_message=classification.outreach_message,
        classification_rationale=classification.classification_rationale,
        metadata=EnrichmentMetadata(model=MODEL),
    )
