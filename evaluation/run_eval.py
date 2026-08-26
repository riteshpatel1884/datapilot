# # """
# # Runs eval_dataset.py's cases through the real pipeline and reports
# # pass/fail per case, using evaluators.py's deterministic checks.

# # Run: python evaluation/run_eval.py                 (1 pass each, quick)
# #      python evaluation/run_eval.py --repeats 5      (measures CONSISTENCY)

# # The --repeats flag exists specifically because this pipeline's LLM
# # calls aren't fully deterministic even at temperature=0 (documented in
# # README.md's Known Limitations). Instead of guessing at how often a
# # case flips outcome, this measures it directly: each case is run N
# # times and reports a pass rate, so "who is my best customer?" showing
# # 5/5 pass and "show month-over-month growth" showing 3/5 pass is an
# # actual number you can act on, not an anecdote from a screenshot.

# # Optional LangSmith tracing: if LANGSMITH_TRACING=true and
# # LANGSMITH_API_KEY are set in the environment, every LLM call inside
# # sql_generator.py / ambiguity_classifier.py is automatically traced —
# # no code changes needed, since both already build their chains with
# # LangChain LCEL (prompt | llm | parser). Traces show up at
# # smith.langchain.com under the project named by LANGSMITH_PROJECT.
# # This is genuinely useful here: when a case fails inconsistently, the
# # trace shows you the EXACT prompt and raw model output for that specific
# # run, instead of re-deriving it from the final pipeline result.
# # """
# # import argparse
# # import sys
# # import os
# # import time
# # from collections import defaultdict

# # sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# # from pipeline import run_pipeline
# # from eval_dataset import EVAL_CASES
# # from evaluators import evaluate_case


# # def run_once(case: dict) -> dict:
# #     result = run_pipeline(case["query"], selected_option=case.get("selected_option"))
# #     return evaluate_case(case, result)


# # def run_eval(repeats: int = 1):
# #     summary = []
# #     per_case_passes = defaultdict(int)

# #     for case in EVAL_CASES:
# #         case_id = case["id"]
# #         outcomes = []
# #         for _ in range(repeats):
# #             outcome = run_once(case)
# #             outcomes.append(outcome)
# #             if outcome["passed"]:
# #                 per_case_passes[case_id] += 1

# #         pass_count = per_case_passes[case_id]
# #         consistent = pass_count in (0, repeats)  # all-pass or all-fail = consistent
# #         summary.append({
# #             "id": case_id,
# #             "query": case["query"],
# #             "expected_type": case["expected_type"],
# #             "pass_rate": f"{pass_count}/{repeats}",
# #             "consistent": consistent,
# #             "last_detail": outcomes[-1]["detail"],
# #         })

# #     return summary


# # def print_report(summary: list, repeats: int):
# #     total = len(summary)
# #     fully_passing = sum(1 for s in summary if s["pass_rate"] == f"{repeats}/{repeats}")
# #     flaky = sum(1 for s in summary if not s["consistent"])
# #     fully_failing = total - fully_passing - flaky

# #     print(f"\n{'=' * 70}")
# #     print(f"EVAL REPORT — {total} cases × {repeats} run(s) each")
# #     print(f"{'=' * 70}\n")

# #     for s in summary:
# #         if s["pass_rate"] == f"{repeats}/{repeats}":
# #             marker = "✅"
# #         elif not s["consistent"]:
# #             marker = "⚠️ FLAKY"
# #         else:
# #             marker = "❌"
# #         print(f"{marker}  [{s['pass_rate']}]  {s['id']}  ({s['expected_type']})")
# #         print(f"       query: {s['query']!r}")
# #         print(f"       last run: {s['last_detail']}\n")

# #     print(f"{'=' * 70}")
# #     print(f"Fully passing : {fully_passing}/{total}")
# #     print(f"Flaky (inconsistent across repeats) : {flaky}/{total}")
# #     print(f"Fully failing : {fully_failing}/{total}")
# #     print(f"{'=' * 70}\n")

# #     if flaky > 0 and repeats > 1:
# #         print(
# #             f"{flaky} case(s) didn't produce the same outcome every run. "
# #             "This is the pipeline's LLM non-determinism showing up as a "
# #             "measured number instead of an anecdote — see README's Known "
# #             "Limitations. If LANGSMITH_TRACING is enabled, check the traces "
# #             "for these specific case IDs to see what varied between runs.\n"
# #         )


# # if __name__ == "__main__":
# #     parser = argparse.ArgumentParser(description="Run the DataPilot eval suite.")
# #     parser.add_argument(
# #         "--repeats", type=int, default=1,
# #         help="How many times to run each case (>1 measures consistency, not just pass/fail).",
# #     )
# #     args = parser.parse_args()

# #     start = time.time()
# #     summary = run_eval(repeats=args.repeats)
# #     elapsed = round(time.time() - start, 1)

# #     print_report(summary, args.repeats)
# #     print(f"Total time: {elapsed}s\n")

# """
# Runs eval_dataset.py's cases through the real pipeline and reports
# pass/fail per case, using evaluators.py's deterministic checks.

# Run: python evaluation/run_eval.py                 (1 pass each, quick)
#      python evaluation/run_eval.py --repeats 5      (measures CONSISTENCY)

# FIX (2026-08-24) — LangSmith tracing + token/cost tracking:

# Every classifier/generator call made during an eval run is now tagged
# with the eval case id and repeat index (via `run_config`, threaded
# through pipeline.py -> classify()/generate_sql() -> chain.invoke()).
# Two things fall out of this:

# 1. If LANGSMITH_TRACING=true and LANGSMITH_API_KEY are set, every call
#    shows up at smith.langchain.com tagged with "eval", the case id, and
#    the expected_type — so you can filter to exactly "all classifier
#    calls for case best_customer_ambiguous across every run" and see the
#    raw prompt/response for each, instead of re-deriving it from the
#    final pipeline result.

# 2. A local TokenUsageCallback aggregates input/output tokens across
#    every LLM call in the run, independent of whether LangSmith tracing
#    is even enabled — so you get a total token count and an estimated
#    cost even with LangSmith off. Cost is estimated using Groq's own
#    published rate for openai/gpt-oss-120b: $0.15 / 1M input tokens,
#    $0.60 / 1M output tokens (checked at https://groq.com/pricing —
#    verify there if this has changed since).

# Both classifier and generator calls are covered. The guardrail stage is
# pure regex (zero LLM cost) and isn't counted. If MOCK_MODE is on (no
# GROQ_API_KEY), no real LLM calls happen at all and totals will show 0 —
# that's expected, not a bug in the tracking.
# """
# import argparse
# import os
# import sys
# import time
# from collections import defaultdict

# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# from dotenv import load_dotenv
# load_dotenv()

# from langchain_core.callbacks import BaseCallbackHandler

# from pipeline import run_pipeline
# from eval_dataset import EVAL_CASES
# from evaluators import evaluate_case

# # Groq's published rate for openai/gpt-oss-120b — update if pricing changes.
# INPUT_COST_PER_1M = 0.15
# OUTPUT_COST_PER_1M = 0.60


# class TokenUsageCallback(BaseCallbackHandler):
#     """
#     Provider-agnostic token counter: reads `usage_metadata` off each
#     AIMessage a chain produces. Works for any LangChain chat model that
#     populates it (ChatGroq does, mirroring the underlying API's usage
#     field) — no per-provider special-casing needed.
#     """

#     def __init__(self):
#         self.input_tokens = 0
#         self.output_tokens = 0
#         self.llm_calls = 0

#     def on_llm_end(self, response, **kwargs):
#         for generation_list in response.generations:
#             for generation in generation_list:
#                 message = getattr(generation, "message", None)
#                 usage = getattr(message, "usage_metadata", None) if message else None
#                 if usage:
#                     self.input_tokens += usage.get("input_tokens", 0) or 0
#                     self.output_tokens += usage.get("output_tokens", 0) or 0
#                     self.llm_calls += 1

#     def estimated_cost_usd(self) -> float:
#         return (
#             (self.input_tokens / 1_000_000) * INPUT_COST_PER_1M
#             + (self.output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
#         )


# def _langsmith_status() -> str:
#     tracing_on = os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
#     has_key = bool(os.environ.get("LANGSMITH_API_KEY"))
#     project = os.environ.get("LANGSMITH_PROJECT", "default")
#     if tracing_on and has_key:
#         return f"ON — traces will appear in LangSmith project '{project}'"
#     if tracing_on and not has_key:
#         return "MISCONFIGURED — LANGSMITH_TRACING=true but LANGSMITH_API_KEY is not set"
#     return "OFF — set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to enable"


# def run_once(case: dict, repeat_index: int, token_callback: TokenUsageCallback) -> dict:
#     run_config = {
#         "run_name": f"eval::{case['id']}",
#         "tags": ["eval", case["id"], case["expected_type"]],
#         "metadata": {
#             "eval_case_id": case["id"],
#             "expected_type": case["expected_type"],
#             "repeat_index": repeat_index,
#         },
#         "callbacks": [token_callback],
#     }
#     result = run_pipeline(
#         case["query"],
#         selected_option=case.get("selected_option"),
#         run_config=run_config,
#     )
#     return evaluate_case(case, result)


# def run_eval(repeats: int = 1):
#     summary = []
#     per_case_passes = defaultdict(int)
#     token_callback = TokenUsageCallback()

#     for case in EVAL_CASES:
#         case_id = case["id"]
#         outcomes = []
#         for repeat_index in range(repeats):
#             outcome = run_once(case, repeat_index, token_callback)
#             outcomes.append(outcome)
#             if outcome["passed"]:
#                 per_case_passes[case_id] += 1

#         pass_count = per_case_passes[case_id]
#         consistent = pass_count in (0, repeats)
#         summary.append({
#             "id": case_id,
#             "query": case["query"],
#             "expected_type": case["expected_type"],
#             "pass_rate": f"{pass_count}/{repeats}",
#             "consistent": consistent,
#             "last_detail": outcomes[-1]["detail"],
#         })

#     return summary, token_callback


# def print_report(summary: list, repeats: int, token_callback: TokenUsageCallback):
#     total = len(summary)
#     fully_passing = sum(1 for s in summary if s["pass_rate"] == f"{repeats}/{repeats}")
#     flaky = sum(1 for s in summary if not s["consistent"])
#     fully_failing = total - fully_passing - flaky

#     print(f"\n{'=' * 70}")
#     print(f"EVAL REPORT — {total} cases × {repeats} run(s) each")
#     print(f"LangSmith tracing: {_langsmith_status()}")
#     print(f"{'=' * 70}\n")

#     for s in summary:
#         if s["pass_rate"] == f"{repeats}/{repeats}":
#             marker = "✅"
#         elif not s["consistent"]:
#             marker = "⚠️ FLAKY"
#         else:
#             marker = "❌"
#         print(f"{marker}  [{s['pass_rate']}]  {s['id']}  ({s['expected_type']})")
#         print(f"       query: {s['query']!r}")
#         print(f"       last run: {s['last_detail']}\n")

#     print(f"{'=' * 70}")
#     print(f"Fully passing : {fully_passing}/{total}")
#     print(f"Flaky (inconsistent across repeats) : {flaky}/{total}")
#     print(f"Fully failing : {fully_failing}/{total}")
#     print(f"{'-' * 70}")
#     print(f"LLM calls (classifier + generator combined) : {token_callback.llm_calls}")
#     print(f"Input tokens  : {token_callback.input_tokens:,}")
#     print(f"Output tokens : {token_callback.output_tokens:,}")
#     print(f"Estimated cost: ${token_callback.estimated_cost_usd():.5f}  "
#           f"(Groq openai/gpt-oss-120b @ ${INPUT_COST_PER_1M}/1M in, ${OUTPUT_COST_PER_1M}/1M out)")
#     if token_callback.llm_calls == 0:
#         print("  (0 calls — check MOCK_MODE isn't on, i.e. GROQ_API_KEY is actually set)")
#     print(f"{'=' * 70}\n")

#     if flaky > 0 and repeats > 1:
#         print(
#             f"{flaky} case(s) didn't produce the same outcome every run. "
#             "If LangSmith tracing is on, filter by tag = the case id to see "
#             "exactly what varied between runs for that specific question.\n"
#         )


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Run the DataPilot eval suite.")
#     parser.add_argument(
#         "--repeats", type=int, default=1,
#         help="How many times to run each case (>1 measures consistency, not just pass/fail).",
#     )
#     args = parser.parse_args()

#     start = time.time()
#     summary, token_callback = run_eval(repeats=args.repeats)
#     elapsed = round(time.time() - start, 1)

#     print_report(summary, args.repeats, token_callback)
#     print(f"Total time: {elapsed}s\n")


"""
Runs eval_dataset.py's cases through the real pipeline and reports
pass/fail per case, using evaluators.py's deterministic checks.

Run: python evaluation/run_eval.py                 (1 pass each, quick)
     python evaluation/run_eval.py --repeats 5      (measures CONSISTENCY)

FIX (2026-08-24) — LangSmith tracing + token/cost tracking:

Every classifier/generator call made during an eval run is now tagged
with the eval case id and repeat index (via `run_config`, threaded
through pipeline.py -> classify()/generate_sql() -> chain.invoke()).
Two things fall out of this:

1. If LANGSMITH_TRACING=true and LANGSMITH_API_KEY are set, every call
   shows up at smith.langchain.com tagged with "eval", the case id, and
   the expected_type — so you can filter to exactly "all classifier
   calls for case best_customer_ambiguous across every run" and see the
   raw prompt/response for each, instead of re-deriving it from the
   final pipeline result.

2. A local TokenUsageCallback aggregates input/output tokens across
   every LLM call in the run, independent of whether LangSmith tracing
   is even enabled — so you get a total token count and an estimated
   cost even with LangSmith off. Cost is estimated using Groq's own
   published rate for openai/gpt-oss-120b: $0.15 / 1M input tokens,
   $0.60 / 1M output tokens (checked at https://groq.com/pricing —
   verify there if this has changed since).

Both classifier and generator calls are covered. The guardrail stage is
pure regex (zero LLM cost) and isn't counted. If MOCK_MODE is on (no
GROQ_API_KEY), no real LLM calls happen at all and totals will show 0 —
that's expected, not a bug in the tracking.
"""
import argparse
import os
import sys
import time
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.callbacks import BaseCallbackHandler

from pipeline import run_pipeline
from eval_dataset import EVAL_CASES
from evaluators import evaluate_case
from token_usage import TokenUsageCallback, INPUT_COST_PER_1M, OUTPUT_COST_PER_1M


def _langsmith_status() -> str:
    tracing_on = os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
    has_key = bool(os.environ.get("LANGSMITH_API_KEY"))
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    if tracing_on and has_key:
        return f"ON — traces will appear in LangSmith project '{project}'"
    if tracing_on and not has_key:
        return "MISCONFIGURED — LANGSMITH_TRACING=true but LANGSMITH_API_KEY is not set"
    return "OFF — set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to enable"


def run_once(case: dict, repeat_index: int, token_callback: TokenUsageCallback) -> dict:
    run_config = {
        "run_name": f"eval::{case['id']}",
        "tags": ["eval", case["id"], case["expected_type"]],
        "metadata": {
            "eval_case_id": case["id"],
            "expected_type": case["expected_type"],
            "repeat_index": repeat_index,
        },
        "callbacks": [token_callback],
    }
    result = run_pipeline(
        case["query"],
        selected_option=case.get("selected_option"),
        run_config=run_config,
    )
    return evaluate_case(case, result)


def run_eval(repeats: int = 1):
    summary = []
    per_case_passes = defaultdict(int)
    token_callback = TokenUsageCallback()

    for case in EVAL_CASES:
        case_id = case["id"]
        outcomes = []
        for repeat_index in range(repeats):
            outcome = run_once(case, repeat_index, token_callback)
            outcomes.append(outcome)
            if outcome["passed"]:
                per_case_passes[case_id] += 1

        pass_count = per_case_passes[case_id]
        consistent = pass_count in (0, repeats)
        summary.append({
            "id": case_id,
            "query": case["query"],
            "expected_type": case["expected_type"],
            "pass_rate": f"{pass_count}/{repeats}",
            "consistent": consistent,
            "last_detail": outcomes[-1]["detail"],
        })

    return summary, token_callback


def print_report(summary: list, repeats: int, token_callback: TokenUsageCallback):
    total = len(summary)
    fully_passing = sum(1 for s in summary if s["pass_rate"] == f"{repeats}/{repeats}")
    flaky = sum(1 for s in summary if not s["consistent"])
    fully_failing = total - fully_passing - flaky

    print(f"\n{'=' * 70}")
    print(f"EVAL REPORT — {total} cases × {repeats} run(s) each")
    print(f"LangSmith tracing: {_langsmith_status()}")
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
    print(f"{'-' * 70}")
    print(f"LLM calls (classifier + generator combined) : {token_callback.llm_calls}")
    print(f"Input tokens  : {token_callback.input_tokens:,}")
    print(f"Output tokens : {token_callback.output_tokens:,}")
    print(f"Estimated cost: ${token_callback.estimated_cost_usd():.5f}  "
          f"(Groq openai/gpt-oss-120b @ ${INPUT_COST_PER_1M}/1M in, ${OUTPUT_COST_PER_1M}/1M out)")
    if token_callback.llm_calls == 0:
        print("  (0 calls — check MOCK_MODE isn't on, i.e. GROQ_API_KEY is actually set)")
    print(f"{'=' * 70}\n")

    if flaky > 0 and repeats > 1:
        print(
            f"{flaky} case(s) didn't produce the same outcome every run. "
            "If LangSmith tracing is on, filter by tag = the case id to see "
            "exactly what varied between runs for that specific question.\n"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the DataPilot eval suite.")
    parser.add_argument(
        "--repeats", type=int, default=1,
        help="How many times to run each case (>1 measures consistency, not just pass/fail).",
    )
    args = parser.parse_args()

    start = time.time()
    summary, token_callback = run_eval(repeats=args.repeats)
    elapsed = round(time.time() - start, 1)

    print_report(summary, args.repeats, token_callback)
    print(f"Total time: {elapsed}s\n")