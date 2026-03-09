from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

import anthropic
from google.cloud import storage
from pydantic import ValidationError

from .models import (
    EnrichedLeadResponse,
    EnrichmentMetadata,
    LeadWebhookPayload,
    LLMClassification,
)
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("ANTHROPIC_MAX_TOKENS", "512"))
GCS_FAILED_LEADS_BUCKET = os.getenv("GCS_FAILED_LEADS_BUCKET")
GCS_ENRICHMENT_BUCKET = os.getenv("GCS_ENRICHMENT_BUCKET")


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


def _write_to_gcs(response: EnrichedLeadResponse) -> None:
    """Write enriched lead to GCS for Snowpipe ingest. Non-fatal: logs a warning on failure."""
    if not GCS_ENRICHMENT_BUCKET:
        logger.warning(
            "GCS_ENRICHMENT_BUCKET not set, skipping write for %s",
            response.lead_id,
        )
        return

    try:
        blob_path = f"leads/{response.lead_id}/{response.metadata.enriched_at}.json"
        client = storage.Client()
        bucket = client.bucket(GCS_ENRICHMENT_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            response.model_dump_json(),
            content_type="application/json",
        )
        logger.info(
            "Wrote lead %s to gs://%s/%s",
            response.lead_id,
            GCS_ENRICHMENT_BUCKET,
            blob_path,
        )
    except Exception:
        logger.warning(
            "Failed to write lead %s to GCS",
            response.lead_id,
            exc_info=True,
        )


def enrich_lead(
    payload: LeadWebhookPayload,
    client: anthropic.Anthropic,
    *,
    request_id: str | None = None,
) -> EnrichedLeadResponse:
    lead_dict = payload.model_dump(exclude_none=True)
    user_prompt = build_user_prompt(lead_dict)

    logger.info(
        "Sending lead %s to %s for classification",
        payload.lead_id,
        MODEL,
        extra={"request_id": request_id},
    )

    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=LLMClassification,
    )

    classification = response.parsed_output
    if classification is None:
        first_block = response.content[0] if response.content else None
        raw_text = getattr(first_block, "text", "<empty>")
        raise ValueError(f"LLM returned unparseable output: {raw_text[:500]}")

    try:
        # Re-validate to enforce Pydantic governance rules (e.g. placeholder detection)
        classification = LLMClassification.model_validate(classification.model_dump())
    except ValidationError:
        _write_to_gcs_failed(payload, "ai_governance_failure", str(classification.model_dump()))
        raise

    logger.info(
        "Classified lead %s as %s/%s (urgency=%d)",
        payload.lead_id,
        classification.loan_type,
        classification.investor_experience,
        classification.urgency_score,
        extra={"request_id": request_id},
    )

    result = EnrichedLeadResponse(
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
        metadata=EnrichmentMetadata(
            model=MODEL,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ),
    )
    _write_to_gcs(result)
    return result
