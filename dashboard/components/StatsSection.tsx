"use client";

import { useEffect, useState } from "react";
import { fetchStats, type PipelineStatsData } from "@/lib/api";
import PipelineStats from "./PipelineStats";
import RecentLeads from "./RecentLeads";

export default function StatsSection() {
  const [stats, setStats] = useState<PipelineStatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load stats");
      });
  }, []);

  if (error) {
    return (
      <div className="grid gap-8 md:grid-cols-2">
        <div className="sr-only" role="alert" aria-live="assertive" aria-atomic="true">
          {error}
        </div>
        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Classification Split
          </h2>
          <div className="rounded-lg border border-red-800 bg-red-950 p-6 text-sm text-red-300">
            {error}
          </div>
        </section>

        <section>
          <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
            Pipeline Stats
          </h2>
          <div className="rounded-lg border border-red-800 bg-red-950 p-6 text-sm text-red-300">
            {error}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <section>
        <h2 className="mb-4 text-sm font-medium uppercase tracking-wider text-neutral-500">
          Classification Split
        </h2>
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
