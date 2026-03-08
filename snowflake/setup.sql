-- Snowpipe setup for lead enrichment pipeline
-- Ingests enriched lead JSON from GCS into Snowflake automatically.
--
-- Prerequisites:
--   - GCS_ENRICHMENT_BUCKET exists and the Cloud Run service writes to it
--   - ACCOUNTADMIN role in Snowflake
--
-- After running this script, complete the two manual steps marked below.

-- ============================================================================
-- 1. Schema
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS martech;
USE SCHEMA martech;

-- ============================================================================
-- 2. Storage integration
-- ============================================================================

CREATE OR REPLACE STORAGE INTEGRATION gcs_lead_enrichment
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'GCS'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('gcs://lead-enrichment-output/leads/');

-- ============================================================================
-- MANUAL STEP 1: Grant GCS access to Snowflake's service account
-- ============================================================================
--
--   1. Run:  DESC INTEGRATION gcs_lead_enrichment;
--   2. Copy the STORAGE_GCP_SERVICE_ACCOUNT value
--   3. In GCP IAM, grant that service account "Storage Object Viewer"
--      on your GCS_ENRICHMENT_BUCKET bucket
--

-- ============================================================================
-- 3. File format
-- ============================================================================

CREATE OR REPLACE FILE FORMAT martech.lead_json_format
  TYPE = 'JSON'
  STRIP_OUTER_ARRAY = FALSE;

-- ============================================================================
-- 4. External stage
-- ============================================================================

CREATE OR REPLACE STAGE martech.gcs_leads_stage
  STORAGE_INTEGRATION = gcs_lead_enrichment
  URL = 'gcs://lead-enrichment-output/leads/'
  FILE_FORMAT = martech.lead_json_format;

-- ============================================================================
-- 5. Target table
-- ============================================================================

CREATE OR REPLACE TABLE martech.raw_webhook_events (
  ingested_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  src             VARIANT,
  lead_id         VARCHAR AS (src:lead_id::VARCHAR),
  loan_type       VARCHAR AS (src:loan_type::VARCHAR),
  urgency_score   NUMBER  AS (src:urgency_score::NUMBER)
);

-- ============================================================================
-- 6. Snowpipe
-- ============================================================================

CREATE OR REPLACE PIPE martech.lead_enrichment_pipe
  AUTO_INGEST = TRUE
  AS
  COPY INTO martech.raw_webhook_events (src)
  FROM @martech.gcs_leads_stage;

-- ============================================================================
-- MANUAL STEP 2: Create GCS Pub/Sub notification for auto-ingest
-- ============================================================================
--
--   1. Run:  SHOW PIPES LIKE 'lead_enrichment_pipe' IN SCHEMA martech;
--   2. Copy the notification_channel value from the output
--   3. Create the notification:
--
--        gsutil notification create \
--          -t <notification_channel> \
--          -f json \
--          -e OBJECT_FINALIZE \
--          gs://lead-enrichment-output
--

-- ============================================================================
-- 7. Load existing files (Snowpipe only auto-ingests new files)
-- ============================================================================

-- ALTER PIPE martech.lead_enrichment_pipe REFRESH;

-- ============================================================================
-- 8. Verification
-- ============================================================================
-- After completing both manual steps, confirm the pipe is running:
--
--   SELECT SYSTEM$PIPE_STATUS('martech.lead_enrichment_pipe');
--
--   -- Check data (wait ~60s after refresh)
--   SELECT lead_id, loan_type, urgency_score, ingested_at
--   FROM martech.raw_webhook_events
--   ORDER BY ingested_at DESC;
--
