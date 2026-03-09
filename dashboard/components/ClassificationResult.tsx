"use client";

import { useState } from "react";
import type { EnrichedLeadResponse } from "@/lib/api";

const LOAN_TYPE_COLORS: Record<string, string> = {
  bridge_rtl: "bg-amber-900/50 text-amber-300 border-amber-700",
  rental: "bg-blue-900/50 text-blue-300 border-blue-700",
  unknown: "bg-neutral-800 text-neutral-400 border-neutral-600",
};

const EXPERIENCE_COLORS: Record<string, string> = {
  experienced: "bg-green-900/50 text-green-300 border-green-700",
  first_time: "bg-purple-900/50 text-purple-300 border-purple-700",
  unknown: "bg-neutral-800 text-neutral-400 border-neutral-600",
};

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span
      className={`inline-block rounded-full border px-3 py-1 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

function UrgencyPips({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(5, Math.round(score)));
  return (
    <div className="flex items-center gap-1">
      <span className="mr-2 text-xs text-neutral-400">Urgency</span>
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className={`h-3 w-3 rounded-full ${
            i <= clamped ? "bg-amber-400" : "bg-neutral-700"
          }`}
        />
      ))}
      <span className="ml-2 text-xs text-neutral-500">{clamped}/5</span>
    </div>
  );
}

export default function ClassificationResult({
  result,
}: {
  result: EnrichedLeadResponse;
}) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="space-y-4 rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Badge
          label={result.loan_type}
          colorClass={LOAN_TYPE_COLORS[result.loan_type] || LOAN_TYPE_COLORS.unknown}
        />
        <Badge
          label={result.investor_experience}
          colorClass={
            EXPERIENCE_COLORS[result.investor_experience] ||
            EXPERIENCE_COLORS.unknown
          }
        />
        <UrgencyPips score={result.urgency_score} />
      </div>

      <div className="rounded-lg border border-neutral-700 bg-neutral-800 p-4">
        <p className="text-sm leading-relaxed text-neutral-100">
          {result.outreach_message}
        </p>
      </div>

      <p className="text-sm text-neutral-500 italic">
        {result.classification_rationale}
      </p>

      <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
        <span>Model: {result.metadata.model}</span>
        {result.metadata.input_tokens != null && (
          <span>In: {result.metadata.input_tokens} tokens</span>
        )}
        {result.metadata.output_tokens != null && (
          <span>Out: {result.metadata.output_tokens} tokens</span>
        )}
      </div>

      <button
        onClick={() => setShowRaw(!showRaw)}
        className="text-xs text-neutral-500 underline hover:text-neutral-300 transition-colors"
      >
        {showRaw ? "Hide" : "View"} Raw JSON
      </button>

      {showRaw && (
        <pre className="mt-2 max-h-80 overflow-auto rounded border border-neutral-700 bg-neutral-950 p-4 text-xs text-neutral-400">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
