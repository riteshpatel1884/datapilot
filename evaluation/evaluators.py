"""
Evaluators for the DataPilot pipeline eval harness.

Deliberately NOT using LLM-as-judge here. Almost every stage of this
pipeline has an objectively correct answer (did the guardrail block it?
does the generated SQL execute and match the real database?) — using a
second LLM to "judge" something with a ground truth just adds cost and
its own non-determinism on top of the thing you're trying to measure.
LLM-as-judge earns its place when there's genuinely no ground truth
(e.g. "is this summary well-phrased") — that's not the bottleneck here.
"""
import math
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from executor.db_executor import execute_query


def _rows_equal(actual_rows, expected_rows, float_tol=0.01) -> bool:
    """
    Order-insensitive comparison of row tuples, with float tolerance
    (SQL float aggregates can differ in the last decimal place between
    equivalent queries written slightly differently).
    """
    if len(actual_rows) != len(expected_rows):
        return False

    def _normalize(row):
        return tuple(round(v, 2) if isinstance(v, float) else v for v in row)

    actual_norm = sorted(_normalize(r) for r in actual_rows)
    expected_norm = sorted(_normalize(r) for r in expected_rows)

    if actual_norm == expected_norm:
        return True

    # fall back to per-value float tolerance for edge cases sorted()
    # comparison misses (e.g. -0.001 vs 0.0)
    if len(actual_norm) != len(expected_norm):
        return False
    for a_row, e_row in zip(actual_norm, expected_norm):
        if len(a_row) != len(e_row):
            return False
        for a_val, e_val in zip(a_row, e_row):
            if isinstance(a_val, float) and isinstance(e_val, float):
                if not math.isclose(a_val, e_val, abs_tol=float_tol):
                    return False
            elif a_val != e_val:
                return False
    return True


def evaluate_case(case: dict, result: dict) -> dict:
    """
    Returns {"passed": bool, "detail": str} for one (case, pipeline
    result) pair. `result` is whatever run_pipeline() returned.
    """
    expected = case["expected_type"]
    actual_type = result.get("type")

    if expected == "result":
        if actual_type != "result":
            return {
                "passed": False,
                "detail": f"expected a result, got type='{actual_type}': {result.get('message', '')}",
            }

        ground_truth_sql = case.get("ground_truth_sql")
        if not ground_truth_sql:
            # No ground truth given — just confirm it actually returned rows.
            row_count = result.get("row_count", len(result.get("table", [])))
            if row_count == 0:
                return {"passed": False, "detail": "returned a result but with zero rows"}
            return {"passed": True, "detail": f"returned {row_count} row(s) (no ground truth to check exactness)"}

        gt = execute_query(ground_truth_sql)
        if not gt.success:
            return {"passed": False, "detail": f"ground_truth_sql itself failed: {gt.error}"}

        actual_rows = [tuple(row.values()) for row in result.get("table", [])]
        if _rows_equal(actual_rows, gt.rows):
            return {"passed": True, "detail": "matches ground truth"}
        return {
            "passed": False,
            "detail": f"mismatch — got {actual_rows[:3]}..., expected {gt.rows[:3]}...",
        }

    if expected == "clarify":
        if actual_type != "clarify":
            return {"passed": False, "detail": f"expected clarify, got type='{actual_type}'"}
        # Guard against the "vague clarification" bug class: options
        # shouldn't be empty AND phrased as an open schema question the
        # user can't answer without knowing table/column names.
        options = result.get("options", [])
        question = (result.get("question") or "").lower()
        leaks_schema_terms = any(term in question for term in ["column", "table name", "which table"])
        if leaks_schema_terms:
            return {"passed": False, "detail": f"clarify_question leaks schema internals: '{result.get('question')}'"}
        return {"passed": True, "detail": f"clarified correctly ({len(options)} option(s) offered)"}

    if expected == "blocked":
        if actual_type != "error":
            return {"passed": False, "detail": f"expected to be blocked, got type='{actual_type}'"}
        msg = (result.get("message") or "").lower()
        # Must be blocked at the GUARDRAIL stage specifically, not just
        # fail somewhere downstream — a destructive query that merely
        # fails at generate() got lucky, it wasn't actually caught.
        guardrail_signals = ["blocked", "doesn't look like a data question",
                              "doesn't look like a question about the mall purchase data",
                              "too long", "empty query",
                              "modify or delete data"]
        if any(sig in msg for sig in guardrail_signals):
            return {"passed": True, "detail": f"blocked at guardrail: '{result.get('message')}'"}
        return {"passed": False, "detail": f"blocked, but NOT at guardrail stage: '{result.get('message')}'"}

    if expected == "no_execution_error":
        if actual_type == "error":
            msg = (result.get("message") or "").lower()
            if "something went wrong running that query" in msg:
                return {"passed": False, "detail": "FAILED AT EXECUTION — validator missed a bad column"}
            return {"passed": True, "detail": f"rejected upstream of execution: '{result.get('message')}'"}
        if actual_type == "result":
            return {"passed": True, "detail": f"generator avoided the bad column, returned a real result: {result.get('summary', '')[:100]}"}
        if actual_type == "clarify":
            return {"passed": True, "detail": "classifier asked for clarification instead of guessing"}
        return {"passed": False, "detail": f"unexpected type='{actual_type}'"}

    return {"passed": False, "detail": f"unknown expected_type in dataset: '{expected}'"}