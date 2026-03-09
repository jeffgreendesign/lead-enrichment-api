from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

# ── Enums ─────────────────────────────────────────────────────────────────────


class LoanType(StrEnum):
    BRIDGE_RTL = "bridge_rtl"
    RENTAL = "rental"
    UNKNOWN = "unknown"


class InvestorExperience(StrEnum):
    FIRST_TIME = "first_time"
    EXPERIENCED = "experienced"
    UNKNOWN = "unknown"


# ── Incoming webhook payload ───────────────────────────────────────────────────


class LeadWebhookPayload(BaseModel):
    lead_id: str
    submitted_at: str | None = None
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    property_address: str | None = None
    property_city: str | None = None
    property_state: str | None = None
    property_type: str | None = None
    loan_amount_requested: float | None = None
    purchase_price: float | None = None
    estimated_arv: float | None = None
    notes: str | None = None
    source: str | None = None
    utm_campaign: str | None = None


# ── LLM structured output ─────────────────────────────────────────────────────


class LLMClassification(BaseModel):
    """
    Schema the LLM is instructed to return. Pydantic validation here acts as
    the AI governance layer — if the model drifts from this contract, we surface
    a validation error rather than forwarding malformed data downstream.
    """

    loan_type: LoanType = Field(
        description="Classified loan intent: bridge/RTL for fix-and-flip, rental for hold strategy"
    )
    investor_experience: InvestorExperience = Field(
        description="Investor experience level inferred from lead signals"
    )
    urgency_score: int = Field(
        ge=1,
        le=5,
        description="Urgency score 1–5, where 5 is highest urgency (e.g. deal under contract)",
    )
    outreach_message: str = Field(
        min_length=10,
        max_length=280,
        description="One-line personalized outreach message for this lead",
    )
    classification_rationale: str = Field(
        max_length=500,
        description="Brief explanation of why these classifications were assigned",
    )

    @field_validator("urgency_score")
    @classmethod
    def validate_urgency(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError(f"urgency_score must be between 1 and 5, got {v}")
        return v

    @field_validator("outreach_message")
    @classmethod
    def no_placeholder_text(cls, v: str) -> str:
        disallowed = ["[name]", "[first name]", "{{", "}}"]
        for token in disallowed:
            if token.lower() in v.lower():
                raise ValueError(f"outreach_message contains unfilled placeholder: {token!r}")
        return v


# ── Enriched response (CDP/marketing automation shape) ────────────────────────


class EnrichmentMetadata(BaseModel):
    enriched_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    model: str
    schema_version: str = "1.0"
    input_tokens: int | None = None
    output_tokens: int | None = None


class EnrichedLeadResponse(BaseModel):
    """
    Final response formatted for downstream CDP / marketing automation ingestion.
    Mirrors the shape expected by platforms like Segment Track or SendGrid
    Dynamic Templates — original lead fields plus enrichment attributes.
    """

    lead_id: str
    email: str
    first_name: str
    last_name: str

    # Original payload pass-through
    raw: LeadWebhookPayload

    # AI enrichment fields
    loan_type: LoanType
    investor_experience: InvestorExperience
    urgency_score: int
    outreach_message: str
    classification_rationale: str

    # Audit trail
    metadata: EnrichmentMetadata
