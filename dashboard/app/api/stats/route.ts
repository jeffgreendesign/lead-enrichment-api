import { NextResponse } from "next/server";

/**
 * Stats endpoint — currently returns stub data.
 *
 * TODO: Wire this up to a `/stats` endpoint on the FastAPI service once it exists.
 * Stats should come from the FastAPI service (which can query Snowflake or aggregate
 * from GCS). Do NOT connect to Snowflake directly from Vercel — all data access
 * should go through the FastAPI service.
 */
export async function GET() {
  return NextResponse.json({
    total_leads: 0,
    avg_urgency: 0,
    avg_input_tokens: 0,
    avg_output_tokens: 0,
    last_enriched_at: null,
    loan_type_breakdown: [
      { name: "bridge_rtl", value: 0 },
      { name: "rental", value: 0 },
      { name: "unknown", value: 0 },
    ],
  });
}
