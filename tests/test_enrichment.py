from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.lead_enrichment.enrichment import _write_to_gcs, _write_to_gcs_failed, enrich_lead
from src.lead_enrichment.models import (
    EnrichedLeadResponse,
    EnrichmentMetadata,
    InvestorExperience,
    LeadWebhookPayload,
    LLMClassification,
    LoanType,
)
from tests.helpers import mock_parse_response


@pytest.fixture
def payload() -> LeadWebhookPayload:
    return LeadWebhookPayload(
        lead_id="dead-letter-001",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
    )


class TestWriteToGcsFailed:
    @patch("src.lead_enrichment.enrichment.storage.Client")
    def test_writes_correct_blob_path_and_content(
        self,
        mock_client_cls: MagicMock,
        payload: LeadWebhookPayload,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("src.lead_enrichment.enrichment.GCS_FAILED_LEADS_BUCKET", "my-bucket")
        mock_client = mock_client_cls.return_value
        mock_bucket = mock_client.bucket.return_value
        mock_blob = mock_bucket.blob.return_value

        _write_to_gcs_failed(payload, "llm_parse_error", "bad json")

        mock_client.bucket.assert_called_once_with("my-bucket")
        mock_bucket.blob.assert_called_once_with("leads/failed/dead-letter-001.json")
        mock_blob.upload_from_string.assert_called_once()

        uploaded = json.loads(mock_blob.upload_from_string.call_args[0][0])
        assert uploaded["error_type"] == "llm_parse_error"
        assert uploaded["error_detail"] == "bad json"
        assert uploaded["payload"]["lead_id"] == "dead-letter-001"
        assert "failed_at" in uploaded

    @patch("src.lead_enrichment.enrichment.storage.Client")
    def test_gcs_failure_logs_warning_and_does_not_raise(
        self,
        mock_client_cls: MagicMock,
        payload: LeadWebhookPayload,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr("src.lead_enrichment.enrichment.GCS_FAILED_LEADS_BUCKET", "my-bucket")
        mock_client_cls.side_effect = Exception("GCS unavailable")

        with caplog.at_level(logging.WARNING):
            _write_to_gcs_failed(payload, "llm_parse_error", "bad json")

        assert "Failed to write dead-letter" in caplog.text

    def test_missing_bucket_env_skips_gcs(
        self,
        payload: LeadWebhookPayload,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr("src.lead_enrichment.enrichment.GCS_FAILED_LEADS_BUCKET", "")

        with caplog.at_level(logging.WARNING):
            _write_to_gcs_failed(payload, "llm_parse_error", "bad json")

        assert "GCS_FAILED_LEADS_BUCKET not set" in caplog.text


@pytest.fixture
def enriched_response() -> EnrichedLeadResponse:
    enriched_payload = LeadWebhookPayload(
        lead_id="enriched-001",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
    )
    return EnrichedLeadResponse(
        lead_id=enriched_payload.lead_id,
        email=enriched_payload.email,
        first_name=enriched_payload.first_name,
        last_name=enriched_payload.last_name,
        raw=enriched_payload,
        loan_type=LoanType.BRIDGE_RTL,
        investor_experience=InvestorExperience.EXPERIENCED,
        urgency_score=3,
        outreach_message="Hello Jane, let us help with your bridge loan.",
        classification_rationale="Experienced investor seeking bridge financing.",
        metadata=EnrichmentMetadata(model="claude-sonnet-4-6"),
    )


class TestWriteToGcs:
    @patch("src.lead_enrichment.enrichment.storage.Client")
    def test_writes_correct_blob_path_and_content(
        self,
        mock_client_cls: MagicMock,
        enriched_response: EnrichedLeadResponse,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "src.lead_enrichment.enrichment.GCS_ENRICHMENT_BUCKET", "enrichment-bucket"
        )
        mock_client = mock_client_cls.return_value
        mock_bucket = mock_client.bucket.return_value
        mock_blob = mock_bucket.blob.return_value

        _write_to_gcs(enriched_response)

        mock_client.bucket.assert_called_once_with("enrichment-bucket")
        expected_path = f"leads/enriched-001/{enriched_response.metadata.enriched_at}.json"
        mock_bucket.blob.assert_called_once_with(expected_path)
        mock_blob.upload_from_string.assert_called_once()

        uploaded = json.loads(mock_blob.upload_from_string.call_args[0][0])
        assert uploaded["lead_id"] == "enriched-001"
        assert uploaded["loan_type"] == "bridge_rtl"
        assert uploaded["urgency_score"] == 3

    @patch("src.lead_enrichment.enrichment.storage.Client")
    def test_gcs_failure_logs_warning_and_does_not_raise(
        self,
        mock_client_cls: MagicMock,
        enriched_response: EnrichedLeadResponse,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(
            "src.lead_enrichment.enrichment.GCS_ENRICHMENT_BUCKET", "enrichment-bucket"
        )
        mock_client_cls.side_effect = Exception("GCS unavailable")

        with caplog.at_level(logging.WARNING):
            _write_to_gcs(enriched_response)

        assert "Failed to write lead" in caplog.text

    def test_missing_bucket_env_skips_gcs(
        self,
        enriched_response: EnrichedLeadResponse,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr("src.lead_enrichment.enrichment.GCS_ENRICHMENT_BUCKET", "")

        with caplog.at_level(logging.WARNING):
            _write_to_gcs(enriched_response)

        assert "GCS_ENRICHMENT_BUCKET not set" in caplog.text


# ── enrich_lead() integration tests ──────────────────────────────────────────


VALID_CLASSIFICATION = LLMClassification(
    loan_type="bridge_rtl",
    investor_experience="experienced",
    urgency_score=4,
    outreach_message=(
        "Jane, with your timeline we can move fast — "
        "our bridge product closes in as little as 10 business days."
    ),
    classification_rationale="Strong fix-and-flip signals with tight timeline.",
)


class TestEnrichLead:
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_happy_path_returns_enriched_response(
        self,
        mock_gcs: MagicMock,
        payload: LeadWebhookPayload,
    ) -> None:
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_parse_response(
            VALID_CLASSIFICATION, input_tokens=200, output_tokens=80
        )

        result = enrich_lead(payload, mock_client)

        assert isinstance(result, EnrichedLeadResponse)
        assert result.lead_id == "dead-letter-001"
        assert result.loan_type == LoanType.BRIDGE_RTL
        assert result.investor_experience == InvestorExperience.EXPERIENCED
        assert result.urgency_score == 4
        assert result.outreach_message == VALID_CLASSIFICATION.outreach_message
        assert result.metadata.input_tokens == 200
        assert result.metadata.output_tokens == 80
        mock_gcs.assert_called_once()

    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_unparseable_response_raises_value_error(
        self,
        mock_gcs: MagicMock,
        payload: LeadWebhookPayload,
    ) -> None:
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_parse_response(None)

        with pytest.raises(ValueError, match="unparseable"):
            enrich_lead(payload, mock_client)

        mock_gcs.assert_not_called()

    @patch("src.lead_enrichment.enrichment._write_to_gcs_failed")
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_governance_failure_writes_dead_letter_and_raises(
        self,
        mock_gcs: MagicMock,
        mock_gcs_failed: MagicMock,
        payload: LeadWebhookPayload,
    ) -> None:
        bad_classification = LLMClassification.model_construct(
            loan_type="bridge_rtl",
            investor_experience="experienced",
            urgency_score=99,
            outreach_message="Jane, let's talk about your next flip!",
            classification_rationale="Strong signals.",
        )
        mock_client = MagicMock()
        mock_client.messages.parse.return_value = mock_parse_response(bad_classification)

        with pytest.raises(ValidationError):
            enrich_lead(payload, mock_client)

        mock_gcs_failed.assert_called_once()
        call_args = mock_gcs_failed.call_args
        assert call_args[0][1] == "ai_governance_failure"
        mock_gcs.assert_not_called()
