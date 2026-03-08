# CLAUDE.md

## Project Overview

Webhook-driven AI lead enrichment API for lending and financial services. Accepts raw lead payloads, classifies loan intent and investor experience via LLM inference, generates personalized outreach, and returns schema-validated structured output. Python/FastAPI on GCP Cloud Run.

## Workflow

- **Small changes** (single file, typo, bug fix): implement directly
- **Multi-file changes or new patterns** (3+ files, new subsystem): use `/design` first
- Always run `/gates` before finishing any task

## Quick Reference

| Aspect          | Value                              |
|-----------------|------------------------------------|
| Runtime         | Python >= 3.12                     |
| Framework       | FastAPI                            |
| LLM SDK         | Anthropic (`anthropic` package)    |
| Validation      | Pydantic v2                        |
| Lint + Format   | `ruff check .` / `ruff format .`   |
| Type check      | `mypy src/`                        |
| Test            | `pytest`                           |
| **All checks**  | **`/gates`**                       |
| Deploy target   | GCP Cloud Run                      |

## Development Commands

```bash
# Setup
pip install -e ".[dev]"

# Dev server (loads .env automatically)
uvicorn src.lead_enrichment.main:app --reload --port 8080 --env-file .env

# Quality gates (run before every commit)
ruff check .
ruff format --check .
mypy src/
bash scripts/security-check.sh --strict
pytest --tb=short

# Auto-fix
ruff check --fix .
ruff format .
```

## Architecture

### Key Systems

**Lead enrichment pipeline** — Three-step process: input validation (Pydantic), LLM classification (Anthropic API), output validation (Pydantic). The output schema acts as an AI governance layer, rejecting malformed LLM responses.

**Dependency injection** — Anthropic client initialized in FastAPI lifespan, injected via `Depends()`. Single client instance across all requests.

**GCS persistence layer** — Enriched leads written to GCS for Snowpipe ingest (`GCS_ENRICHMENT_BUCKET`). Failed enrichments go to a dead-letter bucket (`GCS_FAILED_LEADS_BUCKET`). Both writes are non-fatal: GCS failures log warnings but don't break the API response.

### Directory Map

```text
src/lead_enrichment/
├── main.py          # FastAPI app, routes, lifespan, error handlers
├── enrichment.py    # LLM call, response parsing, validation, GCS write
├── models.py        # Pydantic models (input, LLM output, response)
└── prompts.py       # System prompt + user prompt builder
fixtures/
└── *.json           # Sample lead payloads for testing
scripts/
├── security-check.sh    # Pre-commit secret and safety scanner
├── sync-postman.py      # Regenerate Postman collection from OpenAPI
├── verify-snowpipe.py   # Snowpipe pipeline verification (Python)
└── verify-snowpipe.sh   # Snowpipe pipeline verification (shell)
postman/
└── *.json           # Postman collection (auto-generated)
snowflake/
└── setup.sql        # Storage integration, stage, table, Snowpipe
tests/
└── *.py             # pytest test files
```

### Starting Points

| Task                    | Start Here                          | Why                                    |
|-------------------------|-------------------------------------|----------------------------------------|
| Add/modify routes       | `src/lead_enrichment/main.py`       | All HTTP endpoints defined here        |
| Change LLM behavior     | `src/lead_enrichment/prompts.py`    | System prompt and user prompt templates |
| Change data schema      | `src/lead_enrichment/models.py`     | All Pydantic models and validators     |
| Change LLM call logic   | `src/lead_enrichment/enrichment.py` | API call, parsing, model selection     |
| Change GCS/storage      | `src/lead_enrichment/enrichment.py` | GCS write, dead-letter, blob paths     |

## Code Conventions

### Type Annotations

**Rule:** All functions must have type annotations on parameters and return values.
**Bug it prevents:** mypy strict mode failures and unclear function contracts.

### Pydantic v2 Models

**Rule:** All data shapes use Pydantic `BaseModel` with `field_validator` for business rules.
**Bug it prevents:** Invalid data passing silently through the pipeline.

```python
# WRONG
def process(data: dict) -> dict:

# CORRECT
def process(data: LeadWebhookPayload) -> EnrichedLeadResponse:
```

### Import Style

**Rule:** Use relative imports within the `lead_enrichment` package.
**Bug it prevents:** Broken imports when the package is installed vs run directly.

```python
# WRONG
from lead_enrichment.models import LeadWebhookPayload

# CORRECT
from .models import LeadWebhookPayload
```

## Common Mistakes

### Build Breakers

- Missing `ANTHROPIC_API_KEY` env var — app raises `RuntimeError` at startup
- Pydantic model changes that break the LLM output contract — returns 422 at runtime

### Silent Bugs

- Changing `SYSTEM_PROMPT` without updating `LLMClassification` model — LLM returns fields that don't match the schema
- Adding optional fields to `LeadWebhookPayload` without updating `build_user_prompt()` — new data never reaches the LLM
- Changing GCS blob paths in `enrichment.py` without updating assertions in `tests/test_enrichment.py` — tests mock specific paths like `leads/failed/{id}.json` and `leads/{id}.json`

## How to Add New Things

### New Endpoint

1. Add route in `src/lead_enrichment/main.py`
2. Add request/response models in `src/lead_enrichment/models.py`
3. Add tests in `tests/`
4. Run `/gates`

### New LLM Output Field

1. Add field to `LLMClassification` in `models.py` with validators
2. Update `SYSTEM_PROMPT` in `prompts.py` to instruct the LLM
3. Add field to `EnrichedLeadResponse` in `models.py`
4. Add test for validation in `tests/test_models.py`
5. Run `/gates`

## Architecture Decisions

These choices are intentional. Do not suggest alternatives unless explicitly asked.

- **Synchronous Anthropic client over async**: Cloud Run scales horizontally via instances. Sync is simpler and sufficient.
- **Flat module layout over nested packages**: This is a single-purpose API with 4 source files. No need for sub-packages.
- **Pydantic validation over manual JSON parsing**: Schema acts as an AI governance contract between LLM output and downstream systems.
- **Ruff over Black + isort + flake8**: Single tool replaces three. Already configured in pyproject.toml.

## Debug Playbook

### If the app won't start

- Missing `ANTHROPIC_API_KEY` — set it in `.env` or environment
- Module not found — ensure `pip install -e ".[dev]"` was run

### If /enrich returns 422

- LLM output didn't match `LLMClassification` schema — check `prompts.py` alignment with `models.py`
- `urgency_score` outside 1-5 or `outreach_message` contains placeholder tokens

### If /enrich returns 502

- `llm_parse_error` — LLM returned non-JSON text, check `ANTHROPIC_MODEL` env var
- `upstream_api_error` — Anthropic API issue (rate limit, invalid key, model unavailable)

### If tests fail in CI but pass locally

- Missing env var in CI — check `.github/workflows/ci.yml`
- Different Python version — CI uses 3.12, check local version

## Environment Variables

| Variable           | Required | Default              | Purpose                    |
|--------------------|----------|----------------------|----------------------------|
| `ANTHROPIC_API_KEY`| Yes      | —                    | Anthropic API key          |
| `ANTHROPIC_MODEL`  | No       | `claude-sonnet-4-6`  | Model for LLM inference    |
| `LOG_LEVEL`        | No       | `INFO`               | Python logging level       |
| `PORT`             | No       | `8080`               | Server port (Cloud Run)    |
| `GCS_FAILED_LEADS_BUCKET` | No | —               | GCS bucket for dead-letter failed leads |
| `GCS_ENRICHMENT_BUCKET` | No | —                  | GCS bucket for enriched lead output (Snowpipe source) |
