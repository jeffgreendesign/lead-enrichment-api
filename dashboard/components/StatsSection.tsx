"use client";

import { useEnrichment } from "@/lib/EnrichmentContext";
import PipelineStats from "./PipelineStats";
import RecentLeads from "./RecentLeads";

export default function StatsSection() {
  const { stats, results, clearResults } = useEnrichment();

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-medium uppercase tracking-wider text-neutral-500">
            Classification Split
          </h2>
          {results.length > 0 && (
            <button
              onClick={clearResults}
              className="text-xs text-neutral-600 transition-colors hover:text-neutral-400"
            >
              Clear
            </button>
          )}
        </div>
        <RecentLeads stats={stats} />
      </section>

      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
          Pipeline Stats
        </h2>
        <PipelineStats stats={stats} />
      </section>
    </div>
  );
}
