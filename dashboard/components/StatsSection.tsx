"use client";

import { useEffect, useState } from "react";
import { fetchStats, type PipelineStatsData } from "@/lib/api";
import PipelineStats from "./PipelineStats";
import RecentLeads from "./RecentLeads";

export default function StatsSection() {
  const [stats, setStats] = useState<PipelineStatsData | null>(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
  }, []);

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
