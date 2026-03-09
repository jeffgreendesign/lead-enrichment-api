"use client";

import { useState } from "react";
import { FIXTURES, FIXTURE_NAMES } from "@/lib/fixtures";
import { enrichLead, type EnrichedLeadResponse } from "@/lib/api";
import ClassificationResult from "./ClassificationResult";

export default function LeadTester() {
  const [selectedFixture, setSelectedFixture] = useState(FIXTURE_NAMES[0]);
  const [json, setJson] = useState(
    JSON.stringify(FIXTURES[FIXTURE_NAMES[0]], null, 2),
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EnrichedLeadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFixtureChange(name: string) {
    setSelectedFixture(name);
    setJson(JSON.stringify(FIXTURES[name], null, 2));
    setResult(null);
    setError(null);
  }

  async function handleSubmit() {
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const payload = JSON.parse(json);
      const data = await enrichLead(payload);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
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
          onClick={handleSubmit}
          disabled={loading}
          className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Enriching..." : "Run Enrichment"}
        </button>
      </div>

      <textarea
        value={json}
        onChange={(e) => setJson(e.target.value)}
        rows={12}
        className="w-full rounded border border-neutral-700 bg-neutral-800 p-4 font-mono text-xs text-neutral-300 focus:border-blue-500 focus:outline-none"
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
