"use client";

import { useEffect, useRef } from "react";
import type { LogEntry } from "@/lib/EnrichmentContext";

function StatusDot({ status }: { status: LogEntry["status"] }) {
  if (status === "pending") {
    return (
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
      </span>
    );
  }
  if (status === "error") {
    return <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-red-500" />;
  }
  return <span className="inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-green-500" />;
}

function formatTime(date: Date): string {
  const h = date.getHours().toString().padStart(2, "0");
  const m = date.getMinutes().toString().padStart(2, "0");
  const s = date.getSeconds().toString().padStart(2, "0");
  const ms = date.getMilliseconds().toString().padStart(3, "0");
  return `${h}:${m}:${s}.${ms}`;
}

export default function ProcessLog({
  entries,
  isExpanded,
  onToggle,
}: {
  entries: LogEntry[];
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isExpanded && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries.length, isExpanded]);

  if (entries.length === 0) return null;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium text-neutral-400 transition-colors hover:text-neutral-200"
      >
        <svg
          className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span>Process Log</span>
        <span className="rounded bg-neutral-800 px-1.5 py-0.5 text-[10px] tabular-nums text-neutral-500">
          {entries.length}
        </span>
        {entries.some((e) => e.status === "pending") && (
          <span className="ml-auto text-[10px] text-amber-500">running</span>
        )}
        {entries.length > 0 &&
          !entries.some((e) => e.status === "pending") &&
          entries.every((e) => e.status === "success") && (
            <span className="ml-auto text-[10px] text-green-500">complete</span>
          )}
        {entries.some((e) => e.status === "error") && (
          <span className="ml-auto text-[10px] text-red-500">failed</span>
          )}
      </button>

      {isExpanded && (
        <div
          ref={scrollRef}
          className="max-h-64 overflow-y-auto border-t border-neutral-800 px-4 py-2"
        >
          <div className="space-y-1.5">
            {entries.map((entry, i) => (
              <div key={i} className="flex items-start gap-2.5 text-xs">
                <span className="mt-0.5 shrink-0 tabular-nums text-neutral-600 font-mono">
                  {formatTime(entry.timestamp)}
                </span>
                <StatusDot status={entry.status} />
                <span
                  className={
                    entry.status === "error"
                      ? "text-red-400"
                      : entry.status === "pending"
                        ? "text-neutral-300"
                        : "text-neutral-400"
                  }
                >
                  {entry.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
