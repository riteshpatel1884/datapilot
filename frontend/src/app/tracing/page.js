"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL_MS = 5000;

/**
 * Standalone route: /tracing
 *
 * Live view over the backend's existing GET /logs endpoint — no new
 * backend storage, no LangSmith dependency. Every real /query call
 * writes TWO log lines sharing the same request_id: pipeline.py's own
 * per-stage entry (guardrail/classifier/validator/executor outcome,
 * generated_sql) and api.py's separate cost entry (llm_calls, tokens,
 * estimated_cost_usd). This page merges the two by request_id into one
 * row per actual request, so you see the full picture in one place
 * instead of two disjointed log lines.
 */
export default function TracingPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastFetched, setLastFetched] = useState(null);
  const intervalRef = useRef(null);

  const fetchLogs = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/logs?limit=50`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const raw = await res.json();
      setEntries(mergeByRequestId(raw));
      setError(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
      setLastFetched(new Date());
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchLogs, POLL_INTERVAL_MS);
      return () => clearInterval(intervalRef.current);
    }
  }, [autoRefresh, fetchLogs]);

  return (
    <main className="tracing-page">
      <header className="tracing-header">
        <Link href="/" className="tracing-back-link">
          ← Back to the app
        </Link>
        <p className="eyebrow">Live administration</p>
        <h1 className="title">Tracing</h1>
        <p className="subtitle">
          Every real query hitting the production pipeline, in real time — pulled directly from
          the backend's own request log, no LangSmith login required.
        </p>

        <div className="tracing-controls">
          <button className="tracing-refresh-btn" onClick={fetchLogs} type="button">
            Refresh now
          </button>
          <label className="tracing-autorefresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh every {POLL_INTERVAL_MS / 1000}s
          </label>
          {lastFetched && (
            <span className="tracing-last-fetched">
              Last updated {lastFetched.toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      {error && <div className="tracing-error">Couldn&apos;t reach the backend: {error}</div>}

      {loading && entries.length === 0 && <p className="tracing-loading">Loading recent queries…</p>}

      {!loading && entries.length === 0 && !error && (
        <p className="tracing-empty">No queries logged yet — ask something on the main page.</p>
      )}

      <div className="tracing-list">
        {entries.map((entry) => (
          <TraceRow key={entry.request_id} entry={entry} />
        ))}
      </div>
    </main>
  );
}

/**
 * pipeline.py writes one entry per request with stage/outcome info.
 * api.py writes a second entry (event: "production_query_cost") with
 * the same request_id carrying token/cost data. This merges the two
 * into a single object per request_id, most-recent first.
 */
function mergeByRequestId(rawEntries) {
  const byId = new Map();
  for (const e of rawEntries) {
    if (!e.request_id) continue;
    const existing = byId.get(e.request_id) || {};
    byId.set(e.request_id, { ...existing, ...e });
  }
  return Array.from(byId.values()).sort(
    (a, b) => (b.timestamp || 0) - (a.timestamp || 0)
  );
}

function statusOf(entry) {
  if (entry.stage_failed) return { label: entry.stage_failed.toUpperCase(), tone: "fail" };
  if (entry.outcome === "clarify_requested") return { label: "CLARIFY", tone: "neutral" };
  if (entry.outcome === "result_returned") return { label: "SUCCESS", tone: "pass" };
  return { label: "UNKNOWN", tone: "neutral" };
}

function TraceRow({ entry }) {
  const status = statusOf(entry);
  const hasCost = typeof entry.estimated_cost_usd === "number";

  return (
    <article className="trace-row" data-tone={status.tone}>
      <div className="trace-row-top">
        <span className="trace-status-badge" data-tone={status.tone}>
          {status.label}
        </span>
        {entry.timestamp && (
          <span className="trace-time">{new Date(entry.timestamp * 1000).toLocaleTimeString()}</span>
        )}
      </div>

      <p className="trace-query">{entry.raw_query}</p>

      {entry.error_type && <p className="trace-error-detail">{entry.error_type}</p>}

      {entry.generated_sql && (
        <details className="trace-sql-details">
          <summary>SQL generated</summary>
          <pre className="trace-sql-block">{entry.generated_sql}</pre>
        </details>
      )}

      <div className="trace-metrics">
        {typeof entry.total_pipeline_time_ms === "number" && (
          <MetricChip label="Time" value={`${Math.round(entry.total_pipeline_time_ms)}ms`} />
        )}
        {hasCost && (
          <>
            <MetricChip label="LLM calls" value={entry.llm_calls ?? 0} />
            <MetricChip
              label="Tokens"
              value={((entry.input_tokens || 0) + (entry.output_tokens || 0)).toLocaleString()}
            />
            <MetricChip label="Cost" value={`$${entry.estimated_cost_usd.toFixed(6)}`} />
          </>
        )}
        {!hasCost && <MetricChip label="LLM calls" value={0} note="rejected before any LLM call" />}
      </div>
    </article>
  );
}

function MetricChip({ label, value, note }) {
  return (
    <span className="trace-metric-chip" title={note}>
      <span className="trace-metric-label">{label}</span>
      <span className="trace-metric-value">{value}</span>
    </span>
  );
}