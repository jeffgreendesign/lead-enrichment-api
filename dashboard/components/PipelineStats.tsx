"use client";

import { useEffect, useState } from "react";
import { fetchStats, type PipelineStatsData } from "@/lib/api";

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-neutral-100">{value}</p>
    </div>
  );
}

export default function PipelineStats() {
  const [stats, setStats] = useState<PipelineStatsData | null>(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
  }, []);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-20 animate-pulse rounded-lg border border-neutral-800 bg-neutral-900"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <MetricCard label="Total Leads" value={stats.total_leads} />
        <MetricCard
          label="Avg Urgency"
          value={stats.avg_urgency ? stats.avg_urgency.toFixed(1) : "—"}
        />
        <MetricCard
          label="Avg Input Tokens"
          value={stats.avg_input_tokens || "—"}
        />
        <MetricCard
          label="Avg Output Tokens"
          value={stats.avg_output_tokens || "—"}
        />
      </div>
      <p className="text-xs text-neutral-600">
        Last enrichment:{" "}
        {stats.last_enriched_at
          ? new Date(stats.last_enriched_at).toLocaleString()
          : "None yet"}
      </p>
    </div>
  );
}
