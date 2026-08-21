


"""
RAG Layer — Qdrant version (replaces the earlier Chroma implementation).

Two things get embedded and stored:
  1. Schema docs — one doc per table (name + columns + sample rows)
  2. Few-shot NL->SQL examples — from few_shot_examples.py

At query time we retrieve top-k of each via similarity search and
stuff only the relevant pieces into the LLM prompt, instead of
dumping the whole schema + every example every time.

Connection modes (chosen automatically):
  - QDRANT_URL set        -> connects to a remote/managed Qdrant instance
                              (e.g. Qdrant Cloud). Set QDRANT_API_KEY too
                              if the instance requires one. Use this for
                              any real deployment — hosting platforms
                              generally wipe local disk on redeploy, so
                              local-mode storage below won't survive.
  - QDRANT_URL not set     -> falls back to local on-disk Qdrant at
                              ../qdrant_store (embedded, no server needed).
                              Fine for local dev, same convenience Chroma
                              had via persist_directory.

Note on local mode + `uvicorn --reload`: Qdrant's local/embedded mode
holds a file lock on the storage directory, and only one QdrantClient
process-wide can hold it at a time. This file caches a single shared
client and reuses it for both collections, which fixes the "already
accessed by another instance" error you'd otherwise get from building
two clients on the same path. The remaining case where you can still
hit that error is a SEPARATE process (e.g. your uvicorn server) already
running and holding the lock while you try to run this file directly —
stop that process first, or delete the local qdrant_store/ folder if a
lock persists after a crashed run.
"""
import os
import sqlite3

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from schema.embeddings import get_embeddings
from schema.few_shot_examples import FEW_SHOT_EXAMPLES

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "sample.db")
LOCAL_QDRANT_PATH = os.path.join(os.path.dirname(__file__), "..", "qdrant_store")

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

SCHEMA_COLLECTION = "schema_docs"
EXAMPLES_COLLECTION = "example_docs"

# IMPORTANT: local/embedded Qdrant only allows ONE client to hold the
# storage folder's lock at a time. Building two separate clients on the
# same path in one process (which from_documents() does if called
# twice) throws "already accessed by another instance". So we cache and
# reuse a single client for both collections instead.
_client = None
_schema_store = None
_examples_store = None


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client
    if QDRANT_URL:
        kwargs = {"url": QDRANT_URL}
        if QDRANT_API_KEY:
            kwargs["api_key"] = QDRANT_API_KEY
        _client = QdrantClient(**kwargs)
    else:
        os.makedirs(LOCAL_QDRANT_PATH, exist_ok=True)
        _client = QdrantClient(path=LOCAL_QDRANT_PATH)
    return _client


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


def _ensure_collection(client: QdrantClient, name: str, vector_size: int, recreate: bool = False):
    exists = client.collection_exists(name)
    if recreate and exists:
        client.delete_collection(name)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def build_stores(force_rebuild: bool = False):
    """
    Builds (or recreates) the Qdrant collections for schema + examples,
    using ONE shared client for both. force_rebuild=True drops and
    repopulates both collections — use this whenever the underlying DB
    schema or the few-shot corpus changes. With force_rebuild=False,
    existing non-empty collections are left as-is (no re-embedding on
    every restart); only genuinely missing/empty collections get
    populated.
    """
    global _schema_store, _examples_store

    embeddings = get_embeddings()
    vector_size = len(embeddings.embed_query("dimension probe"))
    client = _get_client()

    schema = get_full_schema()
    schema_docs = _schema_to_documents(schema)
    example_docs = _examples_to_documents(FEW_SHOT_EXAMPLES)

    _ensure_collection(client, SCHEMA_COLLECTION, vector_size, recreate=force_rebuild)
    _ensure_collection(client, EXAMPLES_COLLECTION, vector_size, recreate=force_rebuild)

    _schema_store = QdrantVectorStore(client=client, collection_name=SCHEMA_COLLECTION, embedding=embeddings)
    _examples_store = QdrantVectorStore(client=client, collection_name=EXAMPLES_COLLECTION, embedding=embeddings)

    schema_count = client.count(SCHEMA_COLLECTION).count
    if force_rebuild or schema_count == 0:
        _schema_store.add_documents(schema_docs)

    examples_count = client.count(EXAMPLES_COLLECTION).count
    if force_rebuild or examples_count == 0:
        _examples_store.add_documents(example_docs)

    return _schema_store, _examples_store


def get_stores():
    global _schema_store, _examples_store
    if _schema_store is None or _examples_store is None:
        build_stores(force_rebuild=False)
    return _schema_store, _examples_store


def retrieve_context(query: str, k_schema: int = 3, k_examples: int = 3) -> dict:
    """
    Returns:
      {
        "schema_text": "...",       # relevant table docs, joined
        "examples": [{"question": ..., "sql": ...}, ...],  # relevant few-shot examples
      }

    k_schema / k_examples of 0 skip that retrieval entirely.
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

    # Explicit cleanup so the interpreter doesn't try to close the
    # client's file handle during shutdown (harmless but noisy
    # "Exception ignored in QdrantClient.__del__" message otherwise).
    _get_client().close()