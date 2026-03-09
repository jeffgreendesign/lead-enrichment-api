from __future__ import annotations

from unittest.mock import MagicMock

from src.lead_enrichment.models import LLMClassification


def mock_parse_response(
    classification: LLMClassification | None,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Build a mock ParsedMessage with parsed_output and usage.

    Shared helper used by test_enrich_endpoint.py and test_enrichment.py.
    """
    message = MagicMock()
    message.parsed_output = classification
    message.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    if classification is None:
        block = MagicMock()
        block.text = "I'd be happy to help classify this lead..."
        message.content = [block]
    return message
