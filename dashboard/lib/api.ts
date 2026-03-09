/**
 * API client and TypeScript types for the lead enrichment API.
 *
 * These interfaces mirror the Pydantic models in src/lead_enrichment/models.py.
 * Keep them in sync manually when the Python models change.
 */

export const LEAD_API_URL = process.env.LEAD_API_URL || "";

// ── Types ─────────────────────────────────────────────────────────────────────

export type LoanType = "bridge_rtl" | "rental" | "unknown";
export type InvestorExperience = "first_time" | "experienced" | "unknown";

export interface LeadWebhookPayload {
  lead_id: string;
  submitted_at?: string | null;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string | null;
  property_address?: string | null;
  property_city?: string | null;
  property_state?: string | null;
  property_type?: string | null;
  loan_amount_requested?: number | null;
  purchase_price?: number | null;
  estimated_arv?: number | null;
  notes?: string | null;
  source?: string | null;
  utm_campaign?: string | null;
}

export interface EnrichmentMetadata {
  enriched_at: string;
  model: string;
  schema_version: string;
  input_tokens: number | null;
  output_tokens: number | null;
}

export interface EnrichedLeadResponse {
  lead_id: string;
  email: string;
  first_name: string;
  last_name: string;
  raw: LeadWebhookPayload;
  loan_type: LoanType;
  investor_experience: InvestorExperience;
  urgency_score: number;
  outreach_message: string;
  classification_rationale: string;
  metadata: EnrichmentMetadata;
}

export interface PipelineStatsData {
  total_leads: number;
  avg_urgency: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
  last_enriched_at: string | null;
  loan_type_breakdown: { name: string; value: number }[];
}

// ── API helpers ───────────────────────────────────────────────────────────────

export async function enrichLead(
  payload: LeadWebhookPayload,
): Promise<EnrichedLeadResponse> {
  const res = await fetch("/api/enrich", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || error.detail?.message || res.statusText);
  }

  return res.json();
}

export async function fetchStats(): Promise<PipelineStatsData> {
  const res = await fetch("/api/stats");
  if (!res.ok) {
    throw new Error("Failed to fetch stats");
  }
  return res.json();
}
