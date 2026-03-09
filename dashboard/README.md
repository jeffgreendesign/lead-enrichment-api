# Lead Enrichment Dashboard

Next.js dashboard for the [Lead Enrichment API](../README.md). Provides a lead tester UI, classification result viewer, and pipeline stats.

## Stack

- **Next.js 16** (App Router)
- **React 19**
- **TypeScript**
- **Tailwind CSS v4**
- **Recharts** (donut chart for classification breakdown)

## Local Development

```bash
cd dashboard
npm install
cp .env.local.example .env.local
# Edit .env.local — set LEAD_API_URL to your Cloud Run URL
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Vercel Deployment

1. Connect the same GitHub repository in Vercel
2. Set **Root Directory** to `dashboard/`
3. Add the `LEAD_API_URL` environment variable in Vercel project settings (your Cloud Run URL)
4. Deploy

## Architecture

The dashboard proxies all API requests through Next.js Route Handlers to keep the Cloud Run URL server-side only:

- `POST /api/enrich` → proxies to Cloud Run `/enrich`
- `GET /api/stats` → **stub** returning empty stats (see below)

### Stats Endpoint

The `/api/stats` route currently returns stub/empty data. It will be wired up once a `/stats` endpoint is added to the FastAPI service. Stats should be served by the FastAPI service (which can query Snowflake or aggregate from GCS) — the dashboard should never connect to Snowflake directly.

## Components

| Component | Description |
|-----------|-------------|
| `LeadTester` | Fixture selector + editable JSON textarea + enrichment runner |
| `ClassificationResult` | Renders enriched response with badges, urgency pips, outreach card |
| `PipelineStats` | Metric cards (total leads, avg urgency, token usage) |
| `ProcessLog` | Collapsible log viewer with status indicators |
| `RecentLeads` | Donut chart of loan type classification breakdown |
| `StatsSection` | Grid layout containing PipelineStats + RecentLeads |
