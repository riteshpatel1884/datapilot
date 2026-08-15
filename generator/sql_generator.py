"""
Step 4: SQL Generator (RAG + LangChain version)

Pipeline: retrieve relevant schema + similar few-shot examples via RAG
(schema/schema_rag.py) -> build a prompt from ONLY that retrieved
context -> LangChain LCEL chain -> ChatGroq -> JSON parser.

In mock mode (no GROQ_API_KEY), falls back to template matching against
the same few-shot example corpus so the pipeline still runs end-to-end
without an API key.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from llm_client import get_llm, MOCK_MODE
from schema.schema_rag import retrieve_context
from schema.few_shot_examples import FEW_SHOT_EXAMPLES

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


SYSTEM_PROMPT = """You are a SQL generator for a SQLite database.
You will be given ONLY the schema sections and example queries that were
retrieved as relevant to this specific question (via RAG) — not the full
database schema. Use only what's given here.

Rules:
- Only generate SELECT statements. Never write/modify data.
- Use only tables/columns shown in the retrieved schema. Never invent columns.
- Use the retrieved examples as style/pattern guides, not literal answers.
- Always include a LIMIT clause (default 100 if not specified).
- Respond ONLY with strict JSON, no markdown:
{{
  "sql": "SELECT ...",
  "confidence": "high" | "medium" | "low",
  "assumptions_made": "short note on any assumptions, empty string if none"
}}
"""

HUMAN_PROMPT = """Retrieved schema (relevant tables only):
{schema_text}

Retrieved similar examples (for pattern reference):
{examples_text}

User's resolved intent: "{resolved_intent}"

Generate the SQL query."""


def _build_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])
    llm = get_llm(temperature=0)
    return prompt | llm | JsonOutputParser()


class GeneratorResult:
    def __init__(self, sql: str, confidence: str = "medium", assumptions: str = ""):
        self.sql = sql
        self.confidence = confidence
        self.assumptions = assumptions

    def __repr__(self):
        return f"GeneratorResult(sql='{self.sql}', confidence='{self.confidence}')"


def _format_examples(examples: list) -> str:
    if not examples:
        return "(none retrieved)"
    return "\n".join(f"- Q: {ex['question']}\n  SQL: {ex['sql']}" for ex in examples)


def _mock_generate(resolved_intent: str, retrieved_examples: list) -> GeneratorResult:
    """
    Mock-mode fallback: instead of calling an LLM, find the closest
    retrieved few-shot example (RAG already ranked them by similarity)
    and adapt it. This keeps the RAG step meaningful even offline.

    Count-style questions ("how many customers", "total orders") get a
    direct heuristic override first — RAG similarity search over a small
    example corpus can confidently pick the WRONG template for these
    (e.g. matching "total revenue" instead of "total customers"), and
    there's no LLM judgment call in mock mode to catch that mismatch.
    """
    lowered = resolved_intent.lower()

    count_signal = any(p in lowered for p in ["how many", "total number of", "count of", "number of"])
    total_signal = "total" in lowered and "revenue" not in lowered and "amount" not in lowered and "spend" not in lowered

    if count_signal or total_signal:
        mentions_customer = "customer" in lowered
        mentions_order = "order" in lowered

        if mentions_customer and not mentions_order:
            return GeneratorResult(
                "SELECT COUNT(*) AS customer_count FROM customers LIMIT 100",
                "high", "Interpreted as a count of all customers.",
            )
        if mentions_order and not mentions_customer:
            return GeneratorResult(
                "SELECT COUNT(*) AS order_count FROM orders LIMIT 100",
                "high", "Interpreted as a count of all orders placed.",
            )

    if not retrieved_examples:
        return GeneratorResult("SELECT * FROM customers LIMIT 100", "low",
                                "No similar examples retrieved — returned default view.")

    best = retrieved_examples[0]
    sql = best["sql"]

    # naive placeholder fill for the "orders from a specific customer" template
    if "{customer_name}" in sql:
        # try to extract a name-looking substring after "from"
        if "from" in lowered:
            name = resolved_intent.split("from")[-1].strip().rstrip("?")
            sql = sql.replace("{customer_name}", name)
        else:
            sql = sql.replace("{customer_name}", "")
    if "{city}" in sql:
        sql = sql.replace("{city}", "")

    return GeneratorResult(
        sql, "medium",
        f"Adapted from closest RAG-retrieved example: '{best['question']}'",
    )


def generate_sql(resolved_intent: str) -> GeneratorResult:
    context = retrieve_context(resolved_intent, k_schema=3, k_examples=3)

    if MOCK_MODE:
        return _mock_generate(resolved_intent, context["examples"])

    chain = _build_chain()
    try:
        result = chain.invoke({
            "schema_text": context["schema_text"],
            "examples_text": _format_examples(context["examples"]),
            "resolved_intent": resolved_intent,
        })
        return GeneratorResult(
            sql=result.get("sql", ""),
            confidence=result.get("confidence", "medium"),
            assumptions=result.get("assumptions_made", ""),
        )
    except Exception as e:
        return GeneratorResult(sql="", confidence="low", assumptions=f"Generation failed: {e}")


if __name__ == "__main__":
    intent = "who is my best customer? (clarified: Total revenue)"
    print(generate_sql(intent))