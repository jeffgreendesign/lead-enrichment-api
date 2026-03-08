#!/usr/bin/env python3
"""Generate a Postman collection from the FastAPI OpenAPI schema + fixtures.

Run:
    python scripts/sync-postman.py

Requires the app to be importable (pip install -e .).
Writes postman/lead-enrichment-api.postman_collection.json.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "fixtures"
POSTMAN_DIR = ROOT / "postman"
COLLECTION_FILE = POSTMAN_DIR / "lead-enrichment-api.postman_collection.json"

BASE_URL = "{{base_url}}"
COLLECTION_NAME = "Lead Enrichment API"


def load_openapi_schema() -> dict[str, Any]:
    """Import the FastAPI app and extract its OpenAPI schema."""
    from lead_enrichment.main import app  # type: ignore[import-untyped]

    return app.openapi()  # type: ignore[no-any-return]


def build_health_request() -> dict[str, Any]:
    return {
        "name": "Health Check",
        "request": {
            "method": "GET",
            "header": [],
            "url": {"raw": f"{BASE_URL}/health", "host": [BASE_URL], "path": ["health"]},
        },
        "response": [],
    }


def build_enrich_request(fixture_path: Path) -> dict[str, Any]:
    """Build a Postman request item from a fixture file."""
    payload = json.loads(fixture_path.read_text())
    name = fixture_path.stem.replace("lead_", "").replace("_", " ").title()

    return {
        "name": f"Enrich — {name}",
        "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {"mode": "raw", "raw": json.dumps(payload, indent=2)},
            "url": {"raw": f"{BASE_URL}/enrich", "host": [BASE_URL], "path": ["enrich"]},
        },
        "response": [],
    }


def build_collection(schema: dict[str, Any]) -> dict[str, Any]:
    """Build the full Postman collection."""
    fixtures = sorted(FIXTURES_DIR.glob("*.json"))

    items = [build_health_request()]
    items.extend(build_enrich_request(f) for f in fixtures)

    return {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": COLLECTION_NAME,
            "description": schema.get("info", {}).get("description", schema.get("description", "")),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
        "variable": [
            {
                "key": "base_url",
                "value": "http://localhost:8080",
                "type": "string",
            }
        ],
    }


def main() -> None:
    schema = load_openapi_schema()
    collection = build_collection(schema)

    POSTMAN_DIR.mkdir(exist_ok=True)
    COLLECTION_FILE.write_text(json.dumps(collection, indent=2) + "\n")

    item_count = len(collection["item"])
    print(f"Wrote {COLLECTION_FILE.relative_to(ROOT)} ({item_count} requests)")


if __name__ == "__main__":
    main()
