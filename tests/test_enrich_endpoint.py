from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
from fastapi.testclient import TestClient

from src.lead_enrichment.models import LLMClassification


def _mock_parse_response(classification: LLMClassification | None) -> MagicMock:
    """Build a mock ParsedMessage with parsed_output and usage."""
    message = MagicMock()
    message.parsed_output = classification
    message.usage = MagicMock(input_tokens=100, output_tokens=50)
    if classification is None:
        block = MagicMock()
        block.text = "I'd be happy to help classify this lead..."
        message.content = [block]
    return message


VALID_CLASSIFICATION = LLMClassification(
    loan_type="bridge_rtl",
    investor_experience="experienced",
    urgency_score=4,
    outreach_message=(
        "Marcus, with your timeline we can move fast — "
        "our bridge product closes in as little as 10 business days."
    ),
    classification_rationale=(
        "Lead references prior flips and a tight closing window, "
        "indicating experienced investor with high urgency."
    ),
)


class TestEnrichEndpointHappyPath:
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_returns_enriched_response(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.parse.return_value = (  # type: ignore[union-attr]
            _mock_parse_response(VALID_CLASSIFICATION)
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == "test-002"
        assert body["loan_type"] == "bridge_rtl"
        assert body["investor_experience"] == "experienced"
        assert body["urgency_score"] == 4
        assert body["outreach_message"] == VALID_CLASSIFICATION.outreach_message
        assert body["metadata"]["schema_version"] == "1.0"
        assert body["metadata"]["input_tokens"] == 100
        assert body["metadata"]["output_tokens"] == 50
        mock_gcs.assert_called_once()

    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_sparse_payload_succeeds(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        sample_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.parse.return_value = (  # type: ignore[union-attr]
            _mock_parse_response(VALID_CLASSIFICATION)
        )

        resp = client.post("/enrich", json=sample_payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == "test-001"
        assert body["loan_type"] == "bridge_rtl"


class TestEnrichEndpointGovernance:
    @patch("src.lead_enrichment.enrichment._write_to_gcs_failed")
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_urgency_out_of_range_returns_422(
        self,
        mock_gcs: MagicMock,
        mock_gcs_failed: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        bad_classification = LLMClassification.model_construct(
            loan_type="bridge_rtl",
            investor_experience="experienced",
            urgency_score=99,
            outreach_message="Marcus, let's talk about your next flip!",
            classification_rationale="Strong signals.",
        )
        client.app.state.anthropic_client.messages.parse.return_value = (  # type: ignore[union-attr]
            _mock_parse_response(bad_classification)
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 422
        assert resp.json()["error"] == "ai_output_validation_failed"
        mock_gcs.assert_not_called()
        mock_gcs_failed.assert_called_once()

    @patch("src.lead_enrichment.enrichment._write_to_gcs_failed")
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_placeholder_in_outreach_returns_422(
        self,
        mock_gcs: MagicMock,
        mock_gcs_failed: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        bad_classification = LLMClassification.model_construct(
            loan_type="bridge_rtl",
            investor_experience="experienced",
            urgency_score=4,
            outreach_message="Hi [Name], we can help you.",
            classification_rationale="Strong signals.",
        )
        client.app.state.anthropic_client.messages.parse.return_value = (  # type: ignore[union-attr]
            _mock_parse_response(bad_classification)
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 422
        assert resp.json()["error"] == "ai_output_validation_failed"
        mock_gcs.assert_not_called()
        mock_gcs_failed.assert_called_once()


class TestEnrichEndpointErrorPaths:
    @patch("src.lead_enrichment.main._write_to_gcs_failed")
    def test_unparseable_llm_response_returns_502(
        self,
        mock_gcs_failed: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.parse.return_value = (  # type: ignore[union-attr]
            _mock_parse_response(None)
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "llm_parse_error"
        mock_gcs_failed.assert_called_once()

    @patch("src.lead_enrichment.main._write_to_gcs_failed")
    def test_anthropic_api_error_returns_502(
        self,
        mock_gcs_failed: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.parse.side_effect = (  # type: ignore[union-attr]
            anthropic.APIConnectionError(request=MagicMock())
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "upstream_api_error"
        mock_gcs_failed.assert_called_once()


class TestRequestIDMiddleware:
    def test_returns_generated_request_id(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) > 0

    def test_echoes_provided_request_id(self, client: TestClient) -> None:
        resp = client.get("/health", headers={"X-Request-ID": "my-custom-id-123"})
        assert resp.headers["X-Request-ID"] == "my-custom-id-123"
