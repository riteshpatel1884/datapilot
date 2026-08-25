"use client";

import Link from "next/link";
import { EVAL_META, EVAL_CASES } from "./eval-data";

const TYPE_LABELS = {
  result: "Should resolve",
  clarify: "Should ask",
  blocked: "Should block",
  no_execution_error: "Should never error at execution",
};

export default function EvalPage() {
  return (
    <main className="eval-page">
      <header className="eval-header">
        <p className="eyebrow">Automated evaluation</p>
        <h1 className="title">Does the pipeline actually hold up?</h1>
        <p className="subtitle">
          {EVAL_META.totalCases} cases, each run {EVAL_META.repeats}× to measure consistency —
          not just whether it passes once, but whether it passes the <em>same way</em> every time.
        </p>
      </header>

      <section className="eval-summary">
        <SummaryCard
          value={`${EVAL_META.fullyPassing}/${EVAL_META.totalCases}`}
          label="Fully passing"
          tone="good"
        />
        <SummaryCard
          value={EVAL_META.flaky}
          label="Flaky (inconsistent across repeats)"
          tone={EVAL_META.flaky > 0 ? "warn" : "good"}
        />
        <SummaryCard
          value={EVAL_META.fullyFailing}
          label="Fully failing"
          tone={EVAL_META.fullyFailing > 0 ? "bad" : "good"}
        />
        <SummaryCard
          value={`${EVAL_META.totalRuns} runs`}
          label={`in ${EVAL_META.totalTimeSeconds}s`}
          tone="neutral"
        />
      </section>

     

      <section className="eval-case-list">
        {EVAL_CASES.map((c) => (
          <EvalCaseCard key={c.id} caseData={c} />
        ))}
      </section>
    </main>
  );
}

function SummaryCard({ value, label, tone }) {
  return (
    <div className="eval-summary-card" data-tone={tone}>
      <div className="eval-summary-value">{value}</div>
      <div className="eval-summary-label">{label}</div>
    </div>
  );
}

function EvalCaseCard({ caseData }) {
  const [passed, total] = caseData.passRate.split("/").map(Number);
  const allPass = passed === total;

  return (
    <article className="eval-case-card" data-state={allPass ? "pass" : "fail"}>
      <div className="eval-case-top">
        <span className="eval-case-badge" data-state={allPass ? "pass" : "fail"}>
          {allPass ? <CheckIcon /> : <CrossIcon />}
          {caseData.passRate}
        </span>
        <span className="eval-case-type">{TYPE_LABELS[caseData.expectedType] || caseData.expectedType}</span>
      </div>
      <p className="eval-case-query">{caseData.query}</p>
      <p className="eval-case-detail">{caseData.detail}</p>
    </article>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none">
      <circle cx="8" cy="8" r="6.4" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5.2 8.2l1.8 1.8 3.8-3.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none">
      <circle cx="8" cy="8" r="6.4" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}