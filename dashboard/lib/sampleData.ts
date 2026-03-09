import type {
  EnrichedLeadResponse,
  LeadWebhookPayload,
  LoanType,
  InvestorExperience,
} from "./api";

// ── Keyword signals ──────────────────────────────────────────────────────────

const BRIDGE_SIGNALS = [
  "flip",
  "rehab",
  "bridge",
  "fix",
  "arv",
  "close fast",
  "transitional",
  "value-add",
  "acquisition",
  "renovate",
  "renovation",
  "stabilize",
];

const RENTAL_SIGNALS = [
  "rental",
  "dscr",
  "tenant",
  "portfolio",
  "cash flow",
  "landlord",
  "refinance",
  "refi",
  "long-term",
  "30-year",
  "occupancy",
  "doors",
];

const EXPERIENCED_SIGNALS = [
  "years",
  "portfolio",
  "completed",
  "projects",
  "flips",
  "doors",
  "units",
  "properties",
  "partnered",
  "similar",
];

// ── Outreach templates ───────────────────────────────────────────────────────

const BRIDGE_MESSAGES = [
  (name: string) =>
    `Hi ${name}, thanks for reaching out about your transitional loan needs. Based on the property details you shared, we can likely structure a competitive bridge loan to help you close quickly. Our RTL program is built for exactly this kind of deal — fast closes with rehab financing built in. I'd love to walk you through our term sheet. When's a good time to connect?`,
  (name: string) =>
    `${name}, great to hear about your acquisition. We specialize in residential transitional loans for investors like you — fast approvals, flexible draw schedules for rehab, and competitive rates. Let's get your deal into underwriting so we can hit your closing timeline. Can we schedule a call this week?`,
  (name: string) =>
    `Hi ${name}, I reviewed your loan request and this looks like a strong fit for our bridge loan program. We fund fix-and-flip and value-add projects across all 46 states we operate in. Given your timeline, we can move quickly — our average close is under 15 business days. Let me know when you're free to discuss next steps.`,
];

const RENTAL_MESSAGES = [
  (name: string) =>
    `Hi ${name}, thank you for your interest in our rental loan products. Your portfolio sounds well-managed, and a DSCR-based loan could be a great fit for your next acquisition or cash-out refinance. We offer 30-year fixed terms with no personal income verification required — we qualify on property cash flow alone. Let's review your portfolio details together.`,
  (name: string) =>
    `${name}, I'd love to help you grow your rental portfolio. We offer competitive DSCR loans for single-family and multi-family investment properties, with terms designed for long-term hold strategies. Based on the DSCR metrics you mentioned, you're well-positioned for favorable pricing. When can we connect to discuss your goals?`,
  (name: string) =>
    `Hi ${name}, thanks for reaching out about your rental financing needs. Our term loan products are specifically designed for buy-and-hold investors — 30-year fixed, interest-only options available, and no tax return requirements. Let's schedule a quick call to review your portfolio and find the best structure for you.`,
];

const UNKNOWN_MESSAGES = [
  (name: string) =>
    `Hi ${name}, thanks for your interest in real estate investment financing. We'd love to learn more about your goals — whether you're looking at fix-and-flip opportunities or building a rental portfolio, we have programs tailored to each strategy. Would you have time for a brief call so we can understand your situation better?`,
  (name: string) =>
    `${name}, great to connect! We offer financing for a range of real estate investment strategies, from short-term bridge loans for acquisitions and renovations to long-term DSCR loans for rental properties. I'd love to learn more about what you're looking to do and help you find the right product. When works for a quick chat?`,
];

const BRIDGE_RATIONALES = [
  "Lead mentions property acquisition with rehab intent and a defined timeline, indicating a clear bridge/RTL use case. Experience signals suggest familiarity with the process.",
  "The described deal structure — acquisition, renovation, and defined exit — aligns with a residential transitional loan. Urgency indicators present in the timeline requirements.",
  "Property details and stated investment strategy point to a fix-and-flip or value-add project requiring short-term bridge financing with rehab draws.",
];

const RENTAL_RATIONALES = [
  "Lead describes an existing rental portfolio with strong DSCR metrics, seeking long-term financing. Cash flow focus and hold strategy indicate a rental/DSCR product fit.",
  "Portfolio refinance request with documented occupancy and rental income data. Investment history demonstrates experienced rental investor seeking permanent financing.",
  "Buy-and-hold strategy with tenant in place and documented rental income. DSCR qualification pathway is clear based on the provided property economics.",
];

const UNKNOWN_RATIONALES = [
  "Insufficient property details or unclear investment strategy to determine a specific loan product classification. Additional discovery is needed to route this lead appropriately.",
  "Lead shows interest in real estate investing but has not yet identified a specific property or strategy. Early-stage lead requiring nurture sequence before product matching.",
];

// ── Generator ────────────────────────────────────────────────────────────────

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shortId(): string {
  return Math.random().toString(36).slice(2, 6);
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function countSignals(text: string, signals: string[]): number {
  return signals.filter((s) =>
    new RegExp(`\\b${escapeRegex(s)}\\b`, "i").test(text),
  ).length;
}

function weightedPick<T>(items: [T, number][]): T {
  const total = items.reduce((sum, [, w]) => sum + w, 0);
  let r = Math.random() * total;
  for (const [item, weight] of items) {
    r -= weight;
    if (r <= 0) return item;
  }
  return items[items.length - 1][0];
}

export function generateSampleResult(
  fixture: LeadWebhookPayload,
): EnrichedLeadResponse {
  const notes = fixture.notes ?? "";
  const bridgeScore = countSignals(notes, BRIDGE_SIGNALS);
  const rentalScore = countSignals(notes, RENTAL_SIGNALS);
  const experienceScore = countSignals(notes, EXPERIENCED_SIGNALS);

  // Weighted loan type selection
  const loanType: LoanType = weightedPick([
    ["bridge_rtl", Math.max(1, bridgeScore * 3)],
    ["rental", Math.max(1, rentalScore * 3)],
    ["unknown", notes.length === 0 ? 5 : 1],
  ]);

  // Weighted experience selection
  const hasFirstTimeSignals =
    notes.toLowerCase().includes("first time") ||
    notes.toLowerCase().includes("get started") ||
    notes.toLowerCase().includes("how does");

  const experience: InvestorExperience = weightedPick([
    ["experienced", Math.max(1, experienceScore * 3)],
    ["first_time", hasFirstTimeSignals ? 5 : 1],
    ["unknown", notes.length === 0 ? 4 : 1],
  ]);

  // Urgency based on signals
  const hasUrgency =
    notes.toLowerCase().includes("fast") ||
    notes.toLowerCase().includes("days") ||
    notes.toLowerCase().includes("urgent") ||
    notes.toLowerCase().includes("quickly");
  const urgencyScore = hasUrgency ? randomInt(3, 5) : randomInt(1, 4);

  // Pick appropriate outreach and rationale
  const firstName = fixture.first_name;
  let outreachMessage: string;
  let rationale: string;

  if (loanType === "bridge_rtl") {
    outreachMessage = pickRandom(BRIDGE_MESSAGES)(firstName);
    rationale = pickRandom(BRIDGE_RATIONALES);
  } else if (loanType === "rental") {
    outreachMessage = pickRandom(RENTAL_MESSAGES)(firstName);
    rationale = pickRandom(RENTAL_RATIONALES);
  } else {
    outreachMessage = pickRandom(UNKNOWN_MESSAGES)(firstName);
    rationale = pickRandom(UNKNOWN_RATIONALES);
  }

  return {
    lead_id: `${fixture.lead_id}_${shortId()}`,
    email: fixture.email,
    first_name: fixture.first_name,
    last_name: fixture.last_name,
    raw: fixture,
    loan_type: loanType,
    investor_experience: experience,
    urgency_score: urgencyScore,
    outreach_message: outreachMessage,
    classification_rationale: rationale,
    metadata: {
      enriched_at: new Date().toISOString(),
      model: "claude-sonnet-4-6",
      schema_version: "1.0",
      input_tokens: randomInt(280, 620),
      output_tokens: randomInt(180, 420),
    },
  };
}
