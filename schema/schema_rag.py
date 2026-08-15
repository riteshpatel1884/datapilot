"""
RAG Layer (replaces the old keyword-match schema_retriever.py)

Two things get embedded and stored in Chroma:
  1. Schema docs — one doc per table (name + columns + sample rows)
  2. Few-shot NL->SQL examples — from few_shot_examples.py

At query time we retrieve top-k of each via similarity search and
stuff only the relevant pieces into the LLM prompt, instead of
dumping the whole schema + every example every time.
"""
import os
import sqlite3
from langchain_chroma import Chroma
from langchain_core.documents import Document

from schema.embeddings import get_embeddings
from schema.few_shot_examples import FEW_SHOT_EXAMPLES

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "sample.db")
PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_store")

_schema_store = None
_examples_store = None


def get_full_schema(db_path: str = DB_PATH) -> dict:
    """Ground-truth schema read directly from the DB — used by the validator too."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    schema = {}
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        columns = [(col[1], col[2]) for col in cur.fetchall()]
        cur.execute(f"SELECT * FROM {table} LIMIT 2")
        sample_rows = cur.fetchall()
        schema[table] = {"columns": columns, "sample_rows": sample_rows}
    conn.close()
    return schema


def _schema_to_documents(schema: dict) -> list:
    docs = []
    for table, info in schema.items():
        col_str = ", ".join(f"{name} ({dtype})" for name, dtype in info["columns"])
        content = (
            f"Table: {table}\n"
            f"Columns: {col_str}\n"
            f"Sample rows: {info['sample_rows']}"
        )
        docs.append(Document(page_content=content, metadata={"table": table}))
    return docs


def _examples_to_documents(examples: list) -> list:
    docs = []
    for ex in examples:
        # embed on the natural-language question; keep SQL in metadata for retrieval
        docs.append(Document(page_content=ex["question"], metadata={"sql": ex["sql"]}))
    return docs


def build_stores(force_rebuild: bool = False):
    """Builds (or loads persisted) Chroma vectorstores for schema + examples."""
    global _schema_store, _examples_store

    embeddings = get_embeddings()

    if force_rebuild and os.path.exists(PERSIST_DIR):
        import shutil
        shutil.rmtree(PERSIST_DIR)

    schema = get_full_schema()
    schema_docs = _schema_to_documents(schema)
    example_docs = _examples_to_documents(FEW_SHOT_EXAMPLES)

    _schema_store = Chroma.from_documents(
        schema_docs, embeddings,
        collection_name="schema_docs",
        persist_directory=os.path.join(PERSIST_DIR, "schema"),
    )
    _examples_store = Chroma.from_documents(
        example_docs, embeddings,
        collection_name="example_docs",
        persist_directory=os.path.join(PERSIST_DIR, "examples"),
    )
    return _schema_store, _examples_store


def get_stores():
    global _schema_store, _examples_store
    if _schema_store is None or _examples_store is None:
        build_stores()
    return _schema_store, _examples_store


def retrieve_context(query: str, k_schema: int = 3, k_examples: int = 3) -> dict:
    """
    Returns:
      {
        "schema_text": "...",       # relevant table docs, joined
        "examples": [{"question": ..., "sql": ...}, ...],  # relevant few-shot examples
      }

    k_schema / k_examples of 0 skip that retrieval entirely (Chroma
    itself rejects k=0, so we short-circuit before calling it).
    """
    schema_store, examples_store = get_stores()

    schema_text = ""
    if k_schema > 0:
        schema_hits = schema_store.similarity_search(query, k=k_schema)
        schema_text = "\n\n".join(doc.page_content for doc in schema_hits)

    examples = []
    if k_examples > 0:
        example_hits = examples_store.similarity_search(query, k=k_examples)
        examples = [
            {"question": doc.page_content, "sql": doc.metadata.get("sql", "")}
            for doc in example_hits
        ]

    return {"schema_text": schema_text, "examples": examples}


if __name__ == "__main__":
    build_stores(force_rebuild=True)
    ctx = retrieve_context("who is my best customer by revenue?")
    print("--- Retrieved schema ---")
    print(ctx["schema_text"])
    print("\n--- Retrieved examples ---")
    for ex in ctx["examples"]:
        print(ex["question"], "->", ex["sql"])