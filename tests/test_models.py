from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.lead_enrichment.models import (
    EnrichedLeadResponse,
    EnrichmentMetadata,
    InvestorExperience,
    LeadWebhookPayload,
    LLMClassification,
    LoanType,
)


class TestLeadWebhookPayload:
    def test_minimal_payload(self, sample_payload: dict[str, object]) -> None:
        lead = LeadWebhookPayload(**sample_payload)
        assert lead.lead_id == "test-001"
        assert lead.first_name == "Jane"
        assert lead.phone is None

    def test_full_payload(self, full_payload: dict[str, object]) -> None:
        lead = LeadWebhookPayload(**full_payload)
        assert lead.property_city == "Atlanta"
        assert lead.loan_amount_requested == 285000.0

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            LeadWebhookPayload(lead_id="x", first_name="A", last_name="B")  # type: ignore[call-arg]


class TestLLMClassification:
    def _valid_classification(self, **overrides: object) -> dict[str, object]:
        defaults: dict[str, object] = {
            "loan_type": "bridge_rtl",
            "investor_experience": "experienced",
            "urgency_score": 4,
            "outreach_message": "Hi Jane, great opportunity for your next flip!",
            "classification_rationale": "Strong fix-and-flip signals",
        }
        defaults.update(overrides)
        return defaults

    def test_valid_classification(self) -> None:
        c = LLMClassification(**self._valid_classification())
        assert c.loan_type == LoanType.BRIDGE_RTL
        assert c.urgency_score == 4

    def test_urgency_score_too_low(self) -> None:
        with pytest.raises(ValidationError, match="urgency_score"):
            LLMClassification(**self._valid_classification(urgency_score=0))

    def test_urgency_score_too_high(self) -> None:
        with pytest.raises(ValidationError, match="urgency_score"):
            LLMClassification(**self._valid_classification(urgency_score=6))

    def test_outreach_rejects_name_placeholder(self) -> None:
        with pytest.raises(ValidationError, match="placeholder"):
            LLMClassification(
                **self._valid_classification(outreach_message="Hi [Name], let's talk!")
            )

    def test_outreach_rejects_template_braces(self) -> None:
        with pytest.raises(ValidationError, match="placeholder"):
            LLMClassification(
                **self._valid_classification(outreach_message="Hi {{first_name}}, let's connect!")
            )

    def test_outreach_too_short(self) -> None:
        with pytest.raises(ValidationError):
            LLMClassification(**self._valid_classification(outreach_message="Hi"))


class TestEnrichedLeadResponse:
    def test_constructs_from_components(self, sample_payload: dict[str, object]) -> None:
        payload = LeadWebhookPayload(**sample_payload)
        response = EnrichedLeadResponse(
            lead_id=payload.lead_id,
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            raw=payload,
            loan_type=LoanType.BRIDGE_RTL,
            investor_experience=InvestorExperience.EXPERIENCED,
            urgency_score=4,
            outreach_message="Hi Jane, great deal for your next flip!",
            classification_rationale="Fix-and-flip signals detected",
            metadata=EnrichmentMetadata(model="claude-sonnet-4-6"),
        )
        assert response.lead_id == "test-001"
        assert response.metadata.schema_version == "1.0"
        assert response.metadata.enriched_at.endswith("Z")


class TestEnums:
    def test_loan_type_values(self) -> None:
        assert set(LoanType) == {LoanType.BRIDGE_RTL, LoanType.RENTAL, LoanType.UNKNOWN}

    def test_investor_experience_values(self) -> None:
        assert set(InvestorExperience) == {
            InvestorExperience.FIRST_TIME,
            InvestorExperience.EXPERIENCED,
            InvestorExperience.UNKNOWN,
        }
