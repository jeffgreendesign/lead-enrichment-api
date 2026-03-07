from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")


@pytest.fixture
def client() -> TestClient:
    from src.lead_enrichment.main import app

    app.state.anthropic_client = MagicMock()
    return TestClient(app)


@pytest.fixture
def sample_payload() -> dict[str, object]:
    return {
        "lead_id": "test-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
    }


@pytest.fixture
def full_payload() -> dict[str, object]:
    return {
        "lead_id": "test-002",
        "first_name": "Marcus",
        "last_name": "Bellamy",
        "email": "marcus@example.com",
        "phone": "555-0100",
        "property_address": "123 Oak St",
        "property_city": "Atlanta",
        "property_state": "GA",
        "property_type": "single_family",
        "loan_amount_requested": 285000.0,
        "purchase_price": 195000.0,
        "estimated_arv": 385000.0,
        "notes": "Need to close fast",
        "source": "website",
        "utm_campaign": "spring-2026",
    }
