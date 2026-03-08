from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from src.lead_enrichment.enrichment import _write_to_gcs_failed
from src.lead_enrichment.models import LeadWebhookPayload


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
