from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import anthropic
from fastapi.testclient import TestClient


def _mock_llm_response(text: str) -> MagicMock:
    """Build a mock Anthropic Message with a single TextBlock."""
    block = MagicMock()
    block.text = text
    message = MagicMock()
    message.content = [block]
    return message


VALID_CLASSIFICATION = {
    "loan_type": "bridge_rtl",
    "investor_experience": "experienced",
    "urgency_score": 4,
    "outreach_message": (
        "Marcus, with your timeline we can move fast — "
        "our bridge product closes in as little as 10 business days."
    ),
    "classification_rationale": (
        "Lead references prior flips and a tight closing window, "
        "indicating experienced investor with high urgency."
    ),
}


class TestEnrichEndpointHappyPath:
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_returns_enriched_response(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.create.return_value = (  # type: ignore[union-attr]
            _mock_llm_response(json.dumps(VALID_CLASSIFICATION))
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == "test-002"
        assert body["loan_type"] == "bridge_rtl"
        assert body["investor_experience"] == "experienced"
        assert body["urgency_score"] == 4
        assert body["outreach_message"] == VALID_CLASSIFICATION["outreach_message"]
        assert body["metadata"]["schema_version"] == "1.0"
        mock_gcs.assert_called_once()

    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_sparse_payload_succeeds(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        sample_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.create.return_value = (  # type: ignore[union-attr]
            _mock_llm_response(json.dumps(VALID_CLASSIFICATION))
        )

        resp = client.post("/enrich", json=sample_payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["lead_id"] == "test-001"
        assert body["loan_type"] == "bridge_rtl"


class TestEnrichEndpointGovernance:
    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_urgency_out_of_range_returns_422(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        bad = {**VALID_CLASSIFICATION, "urgency_score": 99}
        client.app.state.anthropic_client.messages.create.return_value = (  # type: ignore[union-attr]
            _mock_llm_response(json.dumps(bad))
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 422
        assert resp.json()["error"] == "ai_output_validation_failed"
        mock_gcs.assert_not_called()

    @patch("src.lead_enrichment.enrichment._write_to_gcs")
    def test_placeholder_in_outreach_returns_422(
        self,
        mock_gcs: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        bad = {**VALID_CLASSIFICATION, "outreach_message": "Hi [Name], we can help you."}
        client.app.state.anthropic_client.messages.create.return_value = (  # type: ignore[union-attr]
            _mock_llm_response(json.dumps(bad))
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 422
        assert resp.json()["error"] == "ai_output_validation_failed"
        mock_gcs.assert_not_called()


class TestEnrichEndpointErrorPaths:
    @patch("src.lead_enrichment.main._write_to_gcs_failed")
    def test_non_json_llm_response_returns_502(
        self,
        mock_gcs_failed: MagicMock,
        client: TestClient,
        full_payload: dict[str, object],
    ) -> None:
        client.app.state.anthropic_client.messages.create.return_value = (  # type: ignore[union-attr]
            _mock_llm_response("I'd be happy to help classify this lead...")
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
        client.app.state.anthropic_client.messages.create.side_effect = (  # type: ignore[union-attr]
            anthropic.APIConnectionError(request=MagicMock())
        )

        resp = client.post("/enrich", json=full_payload)

        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "upstream_api_error"
        mock_gcs_failed.assert_called_once()
