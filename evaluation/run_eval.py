"""
Runs eval_dataset.py's cases through the real pipeline and reports
pass/fail per case, using evaluators.py's deterministic checks.

Run: python evaluation/run_eval.py                 (1 pass each, quick)
     python evaluation/run_eval.py --repeats 5      (measures CONSISTENCY)

The --repeats flag exists specifically because this pipeline's LLM
calls aren't fully deterministic even at temperature=0 (documented in
README.md's Known Limitations). Instead of guessing at how often a
case flips outcome, this measures it directly: each case is run N
times and reports a pass rate, so "who is my best customer?" showing
5/5 pass and "show month-over-month growth" showing 3/5 pass is an
actual number you can act on, not an anecdote from a screenshot.

Optional LangSmith tracing: if LANGSMITH_TRACING=true and
LANGSMITH_API_KEY are set in the environment, every LLM call inside
sql_generator.py / ambiguity_classifier.py is automatically traced —
no code changes needed, since both already build their chains with
LangChain LCEL (prompt | llm | parser). Traces show up at
smith.langchain.com under the project named by LANGSMITH_PROJECT.
This is genuinely useful here: when a case fails inconsistently, the
trace shows you the EXACT prompt and raw model output for that specific
run, instead of re-deriving it from the final pipeline result.
"""
import argparse
import sys
import os
import time
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pipeline import run_pipeline
from eval_dataset import EVAL_CASES
from evaluators import evaluate_case


def run_once(case: dict) -> dict:
    result = run_pipeline(case["query"], selected_option=case.get("selected_option"))
    return evaluate_case(case, result)


def run_eval(repeats: int = 1):
    summary = []
    per_case_passes = defaultdict(int)

    for case in EVAL_CASES:
        case_id = case["id"]
        outcomes = []
        for _ in range(repeats):
            outcome = run_once(case)
            outcomes.append(outcome)
            if outcome["passed"]:
                per_case_passes[case_id] += 1

        pass_count = per_case_passes[case_id]
        consistent = pass_count in (0, repeats)  # all-pass or all-fail = consistent
        summary.append({
            "id": case_id,
            "query": case["query"],
            "expected_type": case["expected_type"],
            "pass_rate": f"{pass_count}/{repeats}",
            "consistent": consistent,
            "last_detail": outcomes[-1]["detail"],
        })

    return summary


def print_report(summary: list, repeats: int):
    total = len(summary)
    fully_passing = sum(1 for s in summary if s["pass_rate"] == f"{repeats}/{repeats}")
    flaky = sum(1 for s in summary if not s["consistent"])
    fully_failing = total - fully_passing - flaky

    print(f"\n{'=' * 70}")
    print(f"EVAL REPORT — {total} cases × {repeats} run(s) each")
    print(f"{'=' * 70}\n")

    for s in summary:
        if s["pass_rate"] == f"{repeats}/{repeats}":
            marker = "✅"
        elif not s["consistent"]:
            marker = "⚠️ FLAKY"
        else:
            marker = "❌"
        print(f"{marker}  [{s['pass_rate']}]  {s['id']}  ({s['expected_type']})")
        print(f"       query: {s['query']!r}")
        print(f"       last run: {s['last_detail']}\n")

    print(f"{'=' * 70}")
    print(f"Fully passing : {fully_passing}/{total}")
    print(f"Flaky (inconsistent across repeats) : {flaky}/{total}")
    print(f"Fully failing : {fully_failing}/{total}")
    print(f"{'=' * 70}\n")

    if flaky > 0 and repeats > 1:
        print(
            f"{flaky} case(s) didn't produce the same outcome every run. "
            "This is the pipeline's LLM non-determinism showing up as a "
            "measured number instead of an anecdote — see README's Known "
            "Limitations. If LANGSMITH_TRACING is enabled, check the traces "
            "for these specific case IDs to see what varied between runs.\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DataPilot eval suite.")
    parser.add_argument(
        "--repeats", type=int, default=1,
        help="How many times to run each case (>1 measures consistency, not just pass/fail).",
    )
    args = parser.parse_args()

    start = time.time()
    summary = run_eval(repeats=args.repeats)
    elapsed = round(time.time() - start, 1)

    print_report(summary, args.repeats)
    print(f"Total time: {elapsed}s\n")