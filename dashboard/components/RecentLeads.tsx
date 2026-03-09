"use client";

import type { PipelineStatsData } from "@/lib/api";
import { PieChart, Pie, Cell, Legend, ResponsiveContainer } from "recharts";

const COLORS: Record<string, string> = {
  bridge_rtl: "#d97706",
  rental: "#3b82f6",
  unknown: "#6b7280",
};

export default function RecentLeads({
  stats,
}: {
  stats: PipelineStatsData | null;
}) {
  if (!stats) {
    return (
      <div className="h-64 animate-pulse rounded-lg border border-neutral-800 bg-neutral-900" />
    );
  }

  const data = stats.loan_type_breakdown;
  const hasData = data.some((d) => d.value > 0);

  if (!hasData) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900 text-sm text-neutral-500">
        No enrichment data yet
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            dataKey="value"
            nameKey="name"
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={COLORS[entry.name] || COLORS.unknown}
              />
            ))}
          </Pie>
          <Legend
            verticalAlign="bottom"
            formatter={(value: string) => (
              <span className="text-xs text-neutral-400">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
