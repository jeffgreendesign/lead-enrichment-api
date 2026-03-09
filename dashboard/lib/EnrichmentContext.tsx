"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { EnrichedLeadResponse, PipelineStatsData } from "./api";

// ── Log entry type ───────────────────────────────────────────────────────────

export interface LogEntry {
  id: number;
  timestamp: Date;
  message: string;
  status: "pending" | "success" | "error";
}

let nextLogId = 0;

// ── Context value ────────────────────────────────────────────────────────────

interface EnrichmentContextValue {
  results: EnrichedLeadResponse[];
  addResult: (result: EnrichedLeadResponse) => void;
  clearResults: () => void;
  stats: PipelineStatsData;

  logEntries: LogEntry[];
  addLogEntry: (entry: Omit<LogEntry, "id">) => number;
  updateLogEntryStatus: (id: number, status: LogEntry["status"]) => void;
  clearLog: () => void;
}

const EnrichmentContext = createContext<EnrichmentContextValue | null>(null);

const MAX_RESULTS = 100;

// ── Provider ─────────────────────────────────────────────────────────────────

export function EnrichmentProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<EnrichedLeadResponse[]>([]);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);

  const addResult = useCallback((result: EnrichedLeadResponse) => {
    setResults((prev) => {
      const next = [...prev, result];
      return next.length > MAX_RESULTS ? next.slice(-MAX_RESULTS) : next;
    });
  }, []);

  const clearResults = useCallback(() => setResults([]), []);

  const addLogEntry = useCallback((entry: Omit<LogEntry, "id">): number => {
    const id = nextLogId++;
    setLogEntries((prev) => [...prev, { ...entry, id }]);
    return id;
  }, []);

  const updateLogEntryStatus = useCallback(
    (id: number, status: LogEntry["status"]) => {
      setLogEntries((prev) =>
        prev.map((e) => (e.id === id ? { ...e, status } : e)),
      );
    },
    [],
  );

  const clearLog = useCallback(() => setLogEntries([]), []);

  const stats = useMemo<PipelineStatsData>(() => {
    if (results.length === 0) {
      return {
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
      };
    }

    const counts: Record<string, number> = {
      bridge_rtl: 0,
      rental: 0,
      unknown: 0,
    };
    let urgencySum = 0;
    let inputSum = 0;
    let outputSum = 0;

    for (const r of results) {
      const lt = r.loan_type in counts ? r.loan_type : "unknown";
      counts[lt]++;
      urgencySum += r.urgency_score;
      inputSum += r.metadata.input_tokens ?? 0;
      outputSum += r.metadata.output_tokens ?? 0;
    }

    return {
      total_leads: results.length,
      avg_urgency: urgencySum / results.length,
      avg_input_tokens: Math.round(inputSum / results.length),
      avg_output_tokens: Math.round(outputSum / results.length),
      last_enriched_at:
        results[results.length - 1]?.metadata.enriched_at ?? null,
      loan_type_breakdown: Object.entries(counts).map(([name, value]) => ({
        name,
        value,
      })),
    };
  }, [results]);

  const value = useMemo<EnrichmentContextValue>(
    () => ({
      results,
      addResult,
      clearResults,
      stats,
      logEntries,
      addLogEntry,
      updateLogEntryStatus,
      clearLog,
    }),
    [
      results,
      addResult,
      clearResults,
      stats,
      logEntries,
      addLogEntry,
      updateLogEntryStatus,
      clearLog,
    ],
  );

  return (
    <EnrichmentContext.Provider value={value}>
      {children}
    </EnrichmentContext.Provider>
  );
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useEnrichment(): EnrichmentContextValue {
  const ctx = useContext(EnrichmentContext);
  if (!ctx) {
    throw new Error("useEnrichment must be used within an EnrichmentProvider");
  }
  return ctx;
}
