# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-03-08

### Added

- End-to-end integration tests for `/enrich` endpoint with mocked LLM responses
- GCS write for enriched leads (`GCS_ENRICHMENT_BUCKET`) for Snowpipe ingest
- GCS dead-letter path for failed lead enrichments (`GCS_FAILED_LEADS_BUCKET`)
- Snowflake setup SQL: storage integration, stage, table, Snowpipe (`snowflake/setup.sql`)
- Snowpipe verification scripts (`scripts/verify-snowpipe.py`, `scripts/verify-snowpipe.sh`)
- MIT LICENSE file
- Postman collection with sync script (`scripts/sync-postman.py`)

## [1.0.0] - 2026-03-07

### Added

- POST /enrich endpoint for webhook-driven lead enrichment
- LLM classification: loan type, investor experience, urgency score
- Personalized outreach message generation
- Pydantic schema validation as AI governance layer
- GET /health endpoint
- Dockerfile for GCP Cloud Run deployment
- Sample lead fixtures for testing
