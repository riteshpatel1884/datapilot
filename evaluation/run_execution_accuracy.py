"""
Runs execution_accuracy_cases.py through the real pipeline and reports
real SQL execution accuracy, computed live against the actual database.

Run:
  python evaluation/run_execution_accuracy.py --mode strict  --label v1_strict
  python evaluation/run_execution_accuracy.py --mode lenient --label v2_lenient
  python evaluation/run_execution_accuracy.py --repeats 3    (consistency)
  python evaluation/run_execution_accuracy.py --verbose      (every case, not just failures)

TWO SCORING MODES, both kept on purpose so the before/after is
reproducible on demand instead of just remembered:

  strict  (v1) — the returned rows must match the ground-truth rows
                  EXACTLY, including column count. Any extra column the
                  pipeline adds (e.g. customer_id alongside name) fails
                  the case even though the answer is correct.
                  See v1_baseline.md — this scored 75.9% (85/112).

  lenient (v2, default) — must still return the SAME NUMBER of rows with
                  the correct underlying VALUES, but tolerates additional
                  correct columns. It does NOT forgive wrong values,
                  wrong row counts, duplicates, or a differently-shaped
                  answer (e.g. one pivoted row instead of one row per
                  group) — those still fail. Verified against real
                  failure examples before use.

IMPORTANT for honesty when quoting numbers: a v1 -> v2 jump produced by
switching modes is a SCORING-METHODOLOGY change, not a pipeline
improvement, and should be described that way. Only changes to the
pipeline itself (prompts, guardrails, classifier, generator) that raise
the score under the SAME mode are genuine accuracy improvements. This
script labels every saved report with its mode so the two never get
conflated.

Every mismatch failure prints the pipeline's actual generated SQL, so a
failure is diagnosable from evidence instead of guessed at. Every run
also saves a markdown report to evaluation/results/<label>.md.
"""
import argparse
import os
import sys
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from pipeline import run_pipeline
from execution_accuracy_cases import EXECUTION_ACCURACY_CASES
from evaluators import evaluate_case

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run_once(case: dict, lenient: bool):
    result = run_pipeline(case["query"], selected_option=case.get("selected_option"))
    outcome = evaluate_case(case, result, lenient=lenient)
    return outcome, result.get("sql_used")


def run_experiment(repeats: int, lenient: bool, verbose: bool):
    total_runs = 0
    total_passes = 0
    failures = []  # dicts: id, query, detail, sql, rate

    for case in EXECUTION_ACCURACY_CASES:
        case_passes = 0
        last_detail, last_sql = "", None
        for _ in range(repeats):
            outcome, sql_used = run_once(case, lenient)
            total_runs += 1
            if outcome["passed"]:
                total_passes += 1
                case_passes += 1
            else:
                last_detail, last_sql = outcome["detail"], sql_used
            if verbose:
                marker = "PASS" if outcome["passed"] else "FAIL"
                print(f"  [{marker}] {case['id']}: {case['query']!r} -> {outcome['detail']}")

        if case_passes < repeats:
            failures.append({
                "id": case["id"],
                "query": case["query"],
                "detail": last_detail,
                "sql": last_sql,
                "rate": f"{case_passes}/{repeats}",
            })

    return total_runs, total_passes, failures, len(EXECUTION_ACCURACY_CASES)


def build_report_text(mode, label, total_runs, total_passes, failures, num_cases, repeats, elapsed):
    accuracy = round((total_passes / total_runs) * 100, 1) if total_runs else 0.0
    lines = []
    lines.append(f"# Execution Accuracy — {label}\n")
    lines.append(f"- **Run at:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"- **Scoring mode:** {mode}")
    lines.append(f"- **Cases:** {num_cases} · **Repeats per case:** {repeats} · **Total runs:** {total_runs}")
    lines.append(f"- **Passed:** {total_passes} · **Failed:** {total_runs - total_passes}")
    lines.append(f"- **Time:** {elapsed}s\n")
    lines.append(f"## >>> EXECUTION ACCURACY: {accuracy}% ({total_passes}/{total_runs}) <<<\n")
    if failures:
        lines.append(f"## {len(failures)} case(s) with at least one failing run\n")
        for f in failures:
            lines.append(f"### [{f['rate']}] `{f['id']}`")
            lines.append(f"- **query:** {f['query']}")
            lines.append(f"- **reason:** {f['detail']}")
            if f["sql"]:
                lines.append(f"- **pipeline's SQL:**\n\n```sql\n{f['sql']}\n```")
            lines.append("")
    else:
        lines.append("No failures — every case passed on every run.")
    return "\n".join(lines)


def print_report(mode, total_runs, total_passes, failures, num_cases, repeats, elapsed):
    accuracy = round((total_passes / total_runs) * 100, 1) if total_runs else 0.0
    print(f"\n{'=' * 72}")
    print(f"EXECUTION ACCURACY EXPERIMENT  (scoring mode: {mode})")
    print(f"{'=' * 72}")
    print(f"Cases              : {num_cases}")
    print(f"Repeats per case   : {repeats}")
    print(f"Total runs         : {total_runs}")
    print(f"Passed             : {total_passes}")
    print(f"Failed             : {total_runs - total_passes}")
    print(f"\n>>> EXECUTION ACCURACY: {accuracy}% ({total_passes}/{total_runs}) <<<\n")

    if failures:
        print(f"{'-' * 72}")
        print(f"{len(failures)} case(s) had at least one failing run:\n")
        for f in failures:
            print(f"  [{f['rate']}] {f['id']}")
            print(f"        query : {f['query']!r}")
            print(f"        reason: {f['detail']}")
            if f["sql"]:
                print(f"        SQL   : {f['sql']}")
            print()
    else:
        print("No failures — every case passed on every run.")

    print(f"{'=' * 72}")
    print(f"Total time: {elapsed}s")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DataPilot execution-accuracy experiment.")
    parser.add_argument("--mode", choices=["strict", "lenient"], default="lenient",
                        help="strict = v1 exact match; lenient = v2 subset match (default).")
    parser.add_argument("--repeats", type=int, default=1, help="Runs per case (>1 also measures consistency).")
    parser.add_argument("--verbose", action="store_true", help="Print every case's outcome, not just failures.")
    parser.add_argument("--label", default=None,
                        help="Name for the saved report, e.g. v2_lenient. Defaults to <mode>_<timestamp>.")
    args = parser.parse_args()

    lenient = args.mode == "lenient"
    label = args.label or f"{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    start = time.time()
    total_runs, total_passes, failures, num_cases = run_experiment(
        repeats=args.repeats, lenient=lenient, verbose=args.verbose
    )
    elapsed = round(time.time() - start, 1)

    print_report(args.mode, total_runs, total_passes, failures, num_cases, args.repeats, elapsed)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    report_path = os.path.join(RESULTS_DIR, f"{label}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(build_report_text(args.mode, label, total_runs, total_passes, failures, num_cases, args.repeats, elapsed))
    print(f"Report saved to: {report_path}\n")