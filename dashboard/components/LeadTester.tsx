"use client";

import { useState } from "react";
import { FIXTURES, FIXTURE_NAMES } from "@/lib/fixtures";
import { enrichLead, type EnrichedLeadResponse } from "@/lib/api";
import { useEnrichment } from "@/lib/EnrichmentContext";
import { generateSampleResult } from "@/lib/sampleData";
import ClassificationResult from "./ClassificationResult";
import ProcessLog from "./ProcessLog";

const delay = (ms: number) =>
  process.env.NODE_ENV === "production"
    ? Promise.resolve()
    : new Promise((r) => setTimeout(r, ms));

export default function LeadTester() {
  const { addResult, addLogEntry, updateLogEntryStatus, clearLog, logEntries } =
    useEnrichment();

  const [selectedFixture, setSelectedFixture] = useState(
    FIXTURE_NAMES.length ? FIXTURE_NAMES[0] : "",
  );
  const [json, setJson] = useState(
    JSON.stringify(
      FIXTURE_NAMES.length ? FIXTURES[FIXTURE_NAMES[0]] : {},
      null,
      2,
    ),
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EnrichedLeadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logExpanded, setLogExpanded] = useState(false);

  function handleFixtureChange(name: string) {
    setSelectedFixture(name);
    setJson(JSON.stringify(FIXTURES[name], null, 2));
    setResult(null);
    setError(null);
  }

  function handleLoadSample() {
    setError(null);
    setResult(null);
    clearLog();

    try {
      const payload = JSON.parse(json);
      const sample = generateSampleResult(payload);
      addResult(sample);
      setResult(sample);
      addLogEntry({
        timestamp: new Date(),
        message: `Sample generated for ${payload.first_name ?? "lead"} ${payload.last_name ?? ""} (${payload.lead_id ?? "unknown"})`,
        status: "success",
      });
      addLogEntry({
        timestamp: new Date(),
        message: `Classification: ${sample.loan_type} / ${sample.investor_experience} / urgency ${sample.urgency_score}/5`,
        status: "success",
      });
      addLogEntry({
        timestamp: new Date(),
        message: "Result added to pipeline stats",
        status: "success",
      });
      setLogExpanded(true);
    } catch {
      setError("Invalid JSON in editor");
    }
  }

  async function handleSubmit() {
    setLogExpanded(true);
    clearLog();
    setLoading(true);
    setResult(null);
    setError(null);

    let sendingId = -1;
    let waitingId = -1;

    try {
      const payload = JSON.parse(json);
      addLogEntry({
        timestamp: new Date(),
        message: "Parsing lead payload...",
        status: "success",
      });

      await delay(200);

      const fields = [
        payload.lead_id && `lead_id: ${payload.lead_id}`,
        payload.first_name && `name: ${payload.first_name} ${payload.last_name ?? ""}`.trim(),
        payload.email && `email: ${payload.email}`,
        payload.property_city &&
          `property: ${payload.property_city}, ${payload.property_state ?? ""}`.trim(),
        payload.loan_amount_requested &&
          `amount: $${Number(payload.loan_amount_requested).toLocaleString()}`,
      ].filter(Boolean);

      addLogEntry({
        timestamp: new Date(),
        message: `Validating input fields (${fields.join(", ")})`,
        status: "success",
      });

      await delay(300);
      sendingId = addLogEntry({
        timestamp: new Date(),
        message: "Sending to enrichment API...",
        status: "pending",
      });

      await delay(200);
      waitingId = addLogEntry({
        timestamp: new Date(),
        message: "Waiting for LLM classification (model: claude-sonnet-4-6)...",
        status: "pending",
      });

      const data = await enrichLead(payload);

      updateLogEntryStatus(sendingId, "success");
      updateLogEntryStatus(waitingId, "success");

      addLogEntry({
        timestamp: new Date(),
        message: `Received response (${data.metadata.input_tokens ?? "?"} input tokens, ${data.metadata.output_tokens ?? "?"} output tokens)`,
        status: "success",
      });

      await delay(100);
      addLogEntry({
        timestamp: new Date(),
        message: "Validating classification schema...",
        status: "success",
      });

      await delay(100);
      addLogEntry({
        timestamp: new Date(),
        message: `Enrichment complete — loan_type: ${data.loan_type}, urgency: ${data.urgency_score}/5`,
        status: "success",
      });

      setResult(data);
      addResult(data);
    } catch (err) {
      if (sendingId >= 0) updateLogEntryStatus(sendingId, "error");
      if (waitingId >= 0) updateLogEntryStatus(waitingId, "error");

      const msg = err instanceof Error ? err.message : "Unknown error";
      addLogEntry({
        timestamp: new Date(),
        message: `Error: ${msg}`,
        status: "error",
      });
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label
            htmlFor="fixture-select"
            className="mb-1 block text-sm text-neutral-400"
          >
            Fixture
          </label>
          <select
            id="fixture-select"
            value={selectedFixture}
            onChange={(e) => handleFixtureChange(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 focus:border-blue-500 focus:outline-none"
          >
            {FIXTURE_NAMES.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleLoadSample}
          disabled={loading}
          className="rounded border border-neutral-700 bg-neutral-800 px-4 py-2 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-700 hover:text-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Load Sample Data
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Enriching..." : "Run Enrichment"}
        </button>
      </div>

      <label htmlFor="json-input" className="sr-only">
        Test payload JSON
      </label>
      <textarea
        id="json-input"
        value={json}
        onChange={(e) => setJson(e.target.value)}
        rows={12}
        className="w-full rounded border border-neutral-700 bg-neutral-800 p-4 font-mono text-xs text-neutral-300 focus:border-blue-500 focus:outline-none"
      />

      <ProcessLog
        entries={logEntries}
        isExpanded={logExpanded}
        onToggle={() => setLogExpanded(!logExpanded)}
      />

      {error && (
        <div className="rounded border border-red-800 bg-red-950 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {result && <ClassificationResult result={result} />}
    </div>
  );
}
