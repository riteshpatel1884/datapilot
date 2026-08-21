# """
# Step 3: Intent + Ambiguity Classifier (RAG + LangChain version)

# Stage A: cheap heuristic pre-filter (always runs, no LLM/API cost).
# Stage B: LangChain chain, informed by RAG-retrieved schema context,
# so the LLM knows what columns/metrics actually exist when deciding
# if a term like "best" is genuinely ambiguous for THIS schema.

# In mock mode, Stage A's decision is used directly.
# """
# import sys
# import os

# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# from llm_client import get_llm, MOCK_MODE
# from schema.schema_rag import retrieve_context

# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser

# VAGUE_SUPERLATIVES = ["best", "top", "worst", "most important", "significant", "biggest"]
# METRIC_HINTS = ["revenue", "amount", "orders", "purchases", "sales", "count", "spend", "spent"]


# class ClassifierResult:
#     def __init__(self, status: str, resolved_intent: str = "", clarify_question: str = "",
#                  options: list = None, reasoning: str = ""):
#         self.status = status  # "clarify" or "resolved"
#         self.resolved_intent = resolved_intent
#         self.clarify_question = clarify_question
#         self.options = options or []
#         self.reasoning = reasoning

#     def __repr__(self):
#         return f"ClassifierResult(status='{self.status}', resolved_intent='{self.resolved_intent}')"


# def heuristic_check(query: str) -> ClassifierResult:
#     """Stage A: cheap regex/keyword pass. Flags likely-ambiguous queries."""
#     lowered = query.lower()
#     has_superlative = any(word in lowered for word in VAGUE_SUPERLATIVES)
#     has_metric = any(word in lowered for word in METRIC_HINTS)

#     if has_superlative and not has_metric:
#         return ClassifierResult(
#             status="clarify",
#             clarify_question="By which metric do you mean 'best'?",
#             options=["Total revenue", "Number of orders", "Most recent purchase"],
#             reasoning="Superlative term found without an explicit metric.",
#         )

#     return ClassifierResult(status="resolved", resolved_intent=query,
#                              reasoning="No ambiguity markers found.")


# SYSTEM_PROMPT = """You are an ambiguity classifier for a text-to-SQL system.
# You are given the RAG-retrieved schema context relevant to this question,
# plus a heuristic pre-check flag. Decide if the question has ONE clear,
# well-defined interpretation given THIS schema, or if it's ambiguous and
# needs clarification before generating SQL.

# Only flag it as ambiguous if the schema genuinely supports multiple valid
# interpretations (e.g. multiple candidate metric columns). If the schema
# only has one sensible way to answer it, mark it resolved.

# Respond ONLY with strict JSON, no markdown:
# {{
#   "status": "clarify" or "resolved",
#   "reasoning": "short internal note",
#   "clarify_question": "question to ask user, empty string if resolved",
#   "options": ["option1", "option2", "option3"],
#   "resolved_intent": "a clear restated version of the query, empty string if clarify"
# }}
# """

# HUMAN_PROMPT = """Retrieved schema context:
# {schema_text}

# User question: "{query}"
# Heuristic pre-check result: {heuristic_status} ({heuristic_reasoning})

# Classify this question."""


# def _build_chain():
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", SYSTEM_PROMPT),
#         ("human", HUMAN_PROMPT),
#     ])
#     llm = get_llm(temperature=0)
#     return prompt | llm | JsonOutputParser()


# def classify(query: str, selected_option: str = None) -> ClassifierResult:
#     """
#     If selected_option is provided, the user already answered a
#     clarification question — merge it into the intent directly instead
#     of re-running the classifier.
#     """
#     if selected_option:
#         resolved = f"{query} (clarified: {selected_option})"
#         return ClassifierResult(status="resolved", resolved_intent=resolved,
#                                  reasoning="User resolved via clarification answer.")

#     heuristic_result = heuristic_check(query)

#     if MOCK_MODE:
#         return heuristic_result

#     # RAG: pull relevant schema so the LLM judges ambiguity against the real DB
#     context = retrieve_context(query, k_schema=3, k_examples=0)

#     chain = _build_chain()
#     try:
#         result = chain.invoke({
#             "schema_text": context["schema_text"],
#             "query": query,
#             "heuristic_status": heuristic_result.status,
#             "heuristic_reasoning": heuristic_result.reasoning,
#         })
#         return ClassifierResult(
#             status=result.get("status", "resolved"),
#             resolved_intent=result.get("resolved_intent", query),
#             clarify_question=result.get("clarify_question", ""),
#             options=result.get("options", []),
#             reasoning=result.get("reasoning", ""),
#         )
#     except Exception as e:
#         heuristic_result.reasoning += f" (LLM fallback due to error: {e})"
#         return heuristic_result


# if __name__ == "__main__":
#     tests = [
#         "who is my best customer?",
#         "who is my best customer by revenue?",
#         "show me all orders from Acme Corp",
#     ]
#     for t in tests:
#         print(t, "->", classify(t))




"""
Step 3: Intent + Ambiguity Classifier (RAG + LangChain version)

Stage A: cheap heuristic pre-filter (always runs, no LLM/API cost).
Stage B: LangChain chain, informed by RAG-retrieved schema context,
so the LLM knows what columns/metrics actually exist when deciding
if a term like "best" is genuinely ambiguous for THIS schema.

In mock mode, Stage A's decision is used directly.

FIX (2026-08-20): same root cause as sql_generator.py — Groq's llama
model doesn't reliably return bare JSON even when told to, which broke
JsonOutputParser here too. Added the same fence-stripping step, and the
except block now logs the real exception instead of only stuffing it
into a `reasoning` string nobody surfaces to the user or the logs.
"""
import re
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from llm_client import get_llm, MOCK_MODE
from schema.schema_rag import retrieve_context
from logger import log_run

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda

VAGUE_SUPERLATIVES = ["best", "top", "worst", "most important", "significant", "biggest"]
METRIC_HINTS = ["revenue", "amount", "orders", "purchases", "sales", "count", "spend", "spent"]


class ClassifierResult:
    def __init__(self, status: str, resolved_intent: str = "", clarify_question: str = "",
                 options: list = None, reasoning: str = ""):
        self.status = status  # "clarify" or "resolved"
        self.resolved_intent = resolved_intent
        self.clarify_question = clarify_question
        self.options = options or []
        self.reasoning = reasoning

    def __repr__(self):
        return f"ClassifierResult(status='{self.status}', resolved_intent='{self.resolved_intent}')"


def heuristic_check(query: str) -> ClassifierResult:
    """Stage A: cheap regex/keyword pass. Flags likely-ambiguous queries."""
    lowered = query.lower()
    has_superlative = any(word in lowered for word in VAGUE_SUPERLATIVES)
    has_metric = any(word in lowered for word in METRIC_HINTS)

    if has_superlative and not has_metric:
        return ClassifierResult(
            status="clarify",
            clarify_question="By which metric do you mean 'best'?",
            options=["Total revenue", "Number of orders", "Most recent purchase"],
            reasoning="Superlative term found without an explicit metric.",
        )

    return ClassifierResult(status="resolved", resolved_intent=query,
                             reasoning="No ambiguity markers found.")


SYSTEM_PROMPT = """You are an ambiguity classifier for a text-to-SQL system.
You are given the RAG-retrieved schema context relevant to this question,
plus a heuristic pre-check flag. Decide if the question has ONE clear,
well-defined interpretation given THIS schema, or if it's ambiguous and
needs clarification before generating SQL.

Only flag it as ambiguous if the schema genuinely supports multiple valid
interpretations (e.g. multiple candidate metric columns). If the schema
only has one sensible way to answer it, mark it resolved.

CRITICAL — clarification questions are shown to an end user who does NOT
know the database schema and has never seen a table or column name. You
already have the schema in front of you; that's what it's for.
- NEVER ask the user to name a table, a column, or any database-internal
  term (e.g. don't ask "which column represents X" or "which table
  contains Y"). If you're unsure which column/table applies, that's YOUR
  job to figure out from the retrieved schema — pick the most reasonable
  one and mark the question resolved, rather than punting it to the user.
- Only ask the user to clarify genuine BUSINESS ambiguity — cases where
  the schema truly supports more than one valid real-world meaning (e.g.
  "best" could mean highest revenue OR most orders OR most recent). Phrase
  both the question and every option in plain, everyday language a
  non-technical shopper would use. Never mention columns, tables, joins,
  or SQL.
- If the question refers to data that genuinely doesn't exist anywhere in
  the retrieved schema (e.g. asking about a field that was never
  collected), don't ask the user to locate it for you — mark it resolved
  with resolved_intent unchanged and let the SQL generator/validator
  surface that limitation naturally.
- `options` must always be 2-4 concrete, plain-language choices when
  status is "clarify" — never leave options empty, and never phrase an
  option as a raw column or table name.

Respond ONLY with strict JSON, no markdown:
{{
  "status": "clarify" or "resolved",
  "reasoning": "short internal note",
  "clarify_question": "question to ask user, empty string if resolved",
  "options": ["option1", "option2", "option3"],
  "resolved_intent": "a clear restated version of the query, empty string if clarify"
}}
"""

HUMAN_PROMPT = """Retrieved schema context:
{schema_text}

User question: "{query}"
Heuristic pre-check result: {heuristic_status} ({heuristic_reasoning})

Classify this question."""


def _strip_code_fences(text: str) -> str:
    """Strip a leading/trailing ```json ... ``` fence, if the model added one."""
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
    stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _clean_message(message):
    message.content = _strip_code_fences(message.content)
    return message


def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])
    llm = get_llm(temperature=0)
    clean = RunnableLambda(_clean_message)
    return prompt | llm | clean | JsonOutputParser()


def classify(query: str, selected_option: str = None) -> ClassifierResult:
    """
    If selected_option is provided, the user already answered a
    clarification question — merge it into the intent directly instead
    of re-running the classifier.
    """
    if selected_option:
        resolved = f"{query} (clarified: {selected_option})"
        return ClassifierResult(status="resolved", resolved_intent=resolved,
                                 reasoning="User resolved via clarification answer.")

    heuristic_result = heuristic_check(query)

    if MOCK_MODE:
        return heuristic_result

    # RAG: pull relevant schema so the LLM judges ambiguity against the real DB
    context = retrieve_context(query, k_schema=3, k_examples=0)

    chain = _build_chain()
    try:
        result = chain.invoke({
            "schema_text": context["schema_text"],
            "query": query,
            "heuristic_status": heuristic_result.status,
            "heuristic_reasoning": heuristic_result.reasoning,
        })
        return ClassifierResult(
            status=result.get("status", "resolved"),
            resolved_intent=result.get("resolved_intent", query),
            clarify_question=result.get("clarify_question", ""),
            options=result.get("options", []),
            reasoning=result.get("reasoning", ""),
        )
    except Exception as e:
        # Log the real error so classifier failures are diagnosable,
        # not just silently falling back with no trace.
        log_run({
            "stage_failed": "classifier",
            "success": False,
            "error_type": f"Classification/parse failed: {e}",
            "raw_query": query,
        })
        heuristic_result.reasoning += f" (LLM fallback due to error: {e})"
        return heuristic_result


if __name__ == "__main__":
    tests = [
        "who is my best customer?",
        "who is my best customer by revenue?",
        "show me all orders from Acme Corp",
    ]
    for t in tests:
        print(t, "->", classify(t))