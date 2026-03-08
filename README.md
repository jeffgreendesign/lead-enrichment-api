# lead-enrichment-api

A serverless lead enrichment pipeline for lending and financial services, demonstrating how LLM inference integrates into marketing automation workflows. Built as a pattern exploration — webhook payload in, structured enrichment event out, with Pydantic schema validation acting as an AI governance layer throughout.

**Stack:** Python · FastAPI · Anthropic Claude · Pydantic v2 · Docker · Google Cloud Run

---

## What it does

A `POST /enrich` endpoint accepts a raw lead webhook payload (the kind you'd receive from a form submission, CRM, or ad platform) and returns a structured enrichment event ready for downstream ingestion by a CDP like Segment or a marketing automation platform like SendGrid.

The pipeline runs three steps inside the request lifecycle:

1. **Input validation** — Pydantic parses and validates the incoming webhook payload before any processing occurs
2. **LLM classification + personalization** — The lead data is sent to Claude with a structured prompt requesting:
   - Loan type intent (`bridge_rtl` / `rental` / `unknown`)
   - Investor experience level (`first_time` / `experienced` / `unknown`)
   - Urgency score (1–5)
   - A one-line personalized outreach message (e.g., referencing speed-to-close for a flip, DSCR flexibility for a rental portfolio)
   - Classification rationale for auditability
3. **Output validation** — The LLM's JSON response is validated against a strict Pydantic schema before anything is returned. If the model drifts from the contract — wrong types, missing fields, placeholder text in the outreach message — the request fails with a `422` and an explicit `ai_output_validation_failed` error. This is intentional: the schema is the governance layer.

The final response is shaped as an enrichment event: original lead fields plus AI-derived attributes, formatted as if it would be forwarded to a downstream platform.

---

## Architecture

```
Webhook Payload
      │
      ▼
┌─────────────────────┐
│  Input Validation   │  Pydantic: LeadWebhookPayload
│  (FastAPI / Pydantic)│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   LLM Enrichment    │  Claude claude-sonnet-4-6
│   (Anthropic SDK)   │  System prompt + structured JSON request
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Output Validation  │  Pydantic: LLMClassification
│  (AI Governance)    │  422 on schema mismatch — hard fail
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Structured Event   │  EnrichedLeadResponse
│  (CDP / Automation) │  Ready for Segment Track / SendGrid
└─────────┬───────────┘
          │
          ├──▶ API Response (JSON)
          │
          └──▶ GCS ──▶ Snowpipe ──▶ Snowflake
               (enrichment archive)  (analytics / reporting)
```

The governance approach — using Pydantic as a contract between the LLM and the rest of the system — is the core pattern this project explores. Structured output validation is one of the more underrated techniques for making LLM-integrated services production-ready: it forces the model to earn its place in the pipeline on every request.

---

## Project structure

```
lead-enrichment-api/
├── src/
│   └── lead_enrichment/
│       ├── main.py          # FastAPI app, routes, lifecycle, error handlers
│       ├── models.py        # Pydantic models: payload, LLM output, response
│       ├── enrichment.py    # LLM call + parse + validation logic
│       └── prompts.py       # System prompt + user prompt builder
├── tests/
│   ├── conftest.py              # Shared fixtures and test client setup
│   ├── test_health.py           # Health endpoint tests
│   ├── test_models.py           # Pydantic model validation tests
│   ├── test_enrichment.py       # GCS write and dead-letter tests
│   └── test_enrich_endpoint.py  # End-to-end /enrich integration tests
├── fixtures/                # Sample lead payloads for testing
├── snowflake/
│   └── setup.sql            # Snowflake storage integration, stage, table, Snowpipe
├── postman/
│   └── lead-enrichment-api.postman_collection.json
├── scripts/
│   ├── security-check.sh    # Pre-commit secret and safety scanner
│   ├── sync-postman.py      # Regenerate Postman collection from OpenAPI + fixtures
│   ├── verify-snowpipe.py   # Snowpipe connectivity and ingestion verification
│   └── verify-snowpipe.sh   # Shell wrapper for Snowpipe verification
├── .github/
│   └── workflows/
│       └── ci.yml           # Lint, type-check, security scan, test
├── Dockerfile               # Cloud Run-optimized, python:3.12-slim, non-root
├── pyproject.toml           # Dependencies, build config, ruff/pytest settings
├── .pre-commit-config.yaml  # Ruff, security, and standard hooks
├── .env.example
├── CHANGELOG.md
└── README.md
```

---

## Running locally

### Prerequisites

- Python 3.12+
- An Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### Setup

```bash
git clone https://github.com/jeffgreendesign/lead-enrichment-api
cd lead-enrichment-api

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Start the server

```bash
# Development (auto-reload, loads .env automatically)
uvicorn src.lead_enrichment.main:app --reload --port 8080 --env-file .env

# Production-equivalent
uvicorn src.lead_enrichment.main:app --host 0.0.0.0 --port 8080
```

### Run with Docker

```bash
docker build -t lead-enrichment-api .

docker run --rm \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  lead-enrichment-api
```

---

## Testing with curl

**Fix-and-flip bridge loan lead:**

```bash
curl -X POST http://localhost:8080/enrich \
  -H "Content-Type: application/json" \
  -d @fixtures/lead_bridge_fix_flip.json | jq
```

**Rental portfolio lead:**

```bash
curl -X POST http://localhost:8080/enrich \
  -H "Content-Type: application/json" \
  -d @fixtures/lead_rental_portfolio.json | jq
```

**Sparse data (tests graceful handling):**

```bash
curl -X POST http://localhost:8080/enrich \
  -H "Content-Type: application/json" \
  -d @fixtures/lead_sparse.json | jq
```

**All fixtures in sequence:**

```bash
for f in fixtures/*.json; do
  echo "\n── $f ──"
  curl -s -X POST http://localhost:8080/enrich \
    -H "Content-Type: application/json" \
    -d @$f | jq '.loan_type, .investor_experience, .urgency_score, .outreach_message'
done
```

**Interactive API docs:** [http://localhost:8080/docs](http://localhost:8080/docs)

---

## Postman

A Postman collection is included at `postman/lead-enrichment-api.postman_collection.json` with all endpoints and fixture payloads pre-loaded. Import it into Postman and the `{{base_url}}` variable defaults to `http://localhost:8080`.

To regenerate the collection after changing endpoints, models, or fixtures:

```bash
python scripts/sync-postman.py
```

This pulls the OpenAPI schema from the FastAPI app and combines it with every fixture in `fixtures/` to produce an up-to-date collection.

---

## Deploying to Cloud Run

```bash
# Build and push to Artifact Registry
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/lead-enrichment-api:latest

# Deploy
gcloud run deploy lead-enrichment-api \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/lead-enrichment-api:latest \
  --region us-central1 \
  --platform managed \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-... \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10
```

For production, inject `ANTHROPIC_API_KEY` from Secret Manager rather than `--set-env-vars`:

```bash
gcloud run deploy lead-enrichment-api \
  --image ... \
  --set-secrets ANTHROPIC_API_KEY=anthropic-api-key:latest
```

---

## Snowflake Setup (Snowpipe)

Enriched leads are written to GCS on every successful `/enrich` call. Snowpipe auto-ingests these files into Snowflake for analytics.

### Prerequisites

- `GCS_ENRICHMENT_BUCKET` environment variable set on the Cloud Run service
- Snowflake account with `ACCOUNTADMIN` role

### Steps

1. **Run the setup SQL** — paste and run everything from [`snowflake/setup.sql`](snowflake/setup.sql) in a Snowflake worksheet, through the pipe creation. Stop before `MANUAL STEP 1`.

2. **Get the Snowflake service account**

   ```sql
   DESC INTEGRATION gcs_lead_enrichment;
   ```

   Copy the `STORAGE_GCP_SERVICE_ACCOUNT` value (looks like `xxxx@gcpuscentral1-xxxx.iam.gserviceaccount.com`).

3. **Grant it access in GCP** (run in your terminal)

   ```bash
   gcloud storage buckets add-iam-policy-binding gs://lead-enrichment-output \
     --member="serviceAccount:<STORAGE_GCP_SERVICE_ACCOUNT_FROM_STEP_2>" \
     --role="roles/storage.objectViewer"
   ```

4. **Test the stage can read your files**

   ```sql
   LIST @martech.gcs_leads_stage;
   ```

   You should see your enriched lead JSON files listed.

5. **Get the Pub/Sub notification channel**

   ```sql
   SHOW PIPES LIKE 'lead_enrichment_pipe' IN SCHEMA martech;
   ```

   Copy the `notification_channel` value from the output.

6. **Create the GCS notification** (run in your terminal)

   ```bash
   gsutil notification create \
     -t <notification_channel_from_step_5> \
     -f json \
     -e OBJECT_FINALIZE \
     gs://lead-enrichment-output
   ```

7. **Manually load existing files** — Snowpipe only auto-ingests new files, so refresh to pick up any that already exist:

   ```sql
   ALTER PIPE martech.lead_enrichment_pipe REFRESH;
   ```

8. **Verify**

   ```sql
   -- Check pipe status
   SELECT SYSTEM$PIPE_STATUS('martech.lead_enrichment_pipe');

   -- Check data (wait ~60s after refresh)
   SELECT lead_id, loan_type, urgency_score, ingested_at
   FROM martech.raw_webhook_events
   ORDER BY ingested_at DESC;
   ```

---

## Sample enriched response

```json
{
  "lead_id": "lead_001",
  "email": "marcus.bellamy@example-investors.com",
  "first_name": "Marcus",
  "last_name": "Bellamy",
  "loan_type": "bridge_rtl",
  "investor_experience": "experienced",
  "urgency_score": 5,
  "outreach_message": "Marcus, with 21 days to close we can move fast — our bridge product closes in as little as 10 business days with same-day term sheets. Let's talk today.",
  "classification_rationale": "Lead explicitly mentions a 21-day closing requirement and references prior flips, indicating high urgency and experienced investor status. ARV provided confirms fix-and-flip intent.",
  "raw": { "...": "original payload" },
  "metadata": {
    "enriched_at": "2026-03-07T09:15:42Z",
    "model": "claude-sonnet-4-6",
    "schema_version": "1.0"
  }
}
```

---

## AI governance pattern

The validation flow is worth calling out explicitly because it's the part most teams skip. The `LLMClassification` model isn't just parsing — it's enforcing a contract:

- `urgency_score` must be an integer between 1 and 5. The LLM can't return `"high"` or `null`.
- `outreach_message` has a character limit and a validator that rejects unfilled template placeholders. If the model returns `"Hi [Name], ..."` it's a hard failure.
- `loan_type` and `investor_experience` are enums. Hallucinated values fail immediately.

When validation fails, the API returns a `422` with `error: "ai_output_validation_failed"` rather than silently forwarding bad data downstream. That failure mode is part of the design — it surfaces model drift at the API boundary rather than in the CDP or email platform.

---

## Fixtures

The `fixtures/` directory contains seven sample payloads covering common and edge-case scenarios in real estate investment lending:

| File | Scenario |
|------|----------|
| `lead_bridge_fix_flip.json` | Experienced fix-and-flip investor, hard deadline, single-family in Atlanta |
| `lead_rental_portfolio.json` | Seasoned landlord, DSCR refi, 11-unit portfolio in Cleveland |
| `lead_first_time_vague.json` | First-time investor, unclear strategy, Phoenix |
| `lead_commercial_bridge.json` | Value-add multi-family bridge, Tampa, $2.8M |
| `lead_sparse.json` | Minimal data — tests graceful degradation |
| `lead_contradictory.json` | Mixed flip + hold signals — tests classifier edge case handling |
| `lead_experienced_rental_sfr.json` | Clean DSCR rental, tenant in place, Phoenix |

---

## Related projects

This sits alongside other AI tooling and developer automation work I'm building:

- **[textrawl](https://github.com/jeffgreendesign/textrawl)** — Web-to-markdown conversion optimized for LLM workflows and Obsidian
- **[logpare](https://github.com/jeffgreendesign/logpare)** — Log parsing and analysis tooling
- **[guardrail-sim](https://github.com/jeffgreendesign/guardrail-sim)** — Simulation tooling for AI safety and output governance patterns
- **[hirejeffgreen.com](https://hirejeffgreen.com)** — Portfolio and API-first developer presence

---

## License

MIT
