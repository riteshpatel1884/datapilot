"""
Per-session connection state: which data source (the built-in demo
SQLite database, or a user-connected PostgreSQL database) a given
frontend session is currently using.

Why sessions at all, not a single global toggle: if this is deployed
and two people use it at once (you demoing to one interviewer while
someone else tests it), a global "current database" would mean one
person's connection silently switches what the other person is
querying. Each browser tab gets a session_id (generated client-side,
kept in localStorage) and its own independent connection state here.

Sessions are in-memory only — they don't survive a backend restart,
and there's no persistence layer for them by design: a connection
holds a live DB engine + credentials-derived state that shouldn't be
serialized to disk anyway. A restarted backend just means "connect
again", same as any dev server losing in-memory state.
"""
import time
import threading

from db.postgres_connector import connect_and_introspect, ConnectionError_
from schema.embeddings import get_embeddings

DEMO_MODE = "demo"
POSTGRES_MODE = "postgres"

SESSION_TTL_SECONDS = 60 * 60 * 4  # 4 hours of inactivity -> auto-cleaned


class ConnectionSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.mode = DEMO_MODE
        self.engine = None
        self.schema_cache = {}
        self.schema_store = None  # in-memory Qdrant store, postgres mode only
        self.db_label = ""
        self.table_count = 0
        self.column_count = 0
        self.connected_at = None
        self.last_seen = time.time()
        self.last_error = ""


_sessions: dict[str, ConnectionSession] = {}
# RLock, not Lock: connect()/disconnect() acquire the lock and then call
# get_session() internally, which also acquires it — a plain Lock would
# deadlock on that nested acquisition from the same thread.
_lock = threading.RLock()


def _cleanup_stale():
    cutoff = time.time() - SESSION_TTL_SECONDS
    stale = [sid for sid, s in _sessions.items() if s.last_seen < cutoff]
    for sid in stale:
        _teardown(_sessions.pop(sid))


def _teardown(session: ConnectionSession):
    if session.engine is not None:
        try:
            session.engine.dispose()
        except Exception:
            pass


def get_session(session_id: str) -> ConnectionSession:
    """Always returns a session (creates a fresh demo-mode one if unseen)."""
    if not session_id:
        return ConnectionSession("__anonymous__")  # transient, defaults to demo behavior

    with _lock:
        _cleanup_stale()
        session = _sessions.get(session_id)
        if session is None:
            session = ConnectionSession(session_id)
            _sessions[session_id] = session
        session.last_seen = time.time()
        return session


def _build_schema_index(schema: dict):
    """
    Ephemeral, in-memory (not persisted to disk) Qdrant index over this
    ONE session's schema — separate from the demo path's persisted
    schema collection, and separate per-session so two people connected
    to two different databases never see each other's schema in
    retrieval results. Few-shot SQL-style examples are NOT duplicated
    here — retrieve_context() falls back to the single shared demo
    examples collection for those, since they're generic SQL patterns
    ("count of X", "top N by Y"), not schema-specific facts.
    """
    from langchain_core.documents import Document
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams

    embeddings = get_embeddings()
    vector_size = len(embeddings.embed_query("dimension probe"))

    client = QdrantClient(location=":memory:")
    collection = "session_schema"
    client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    docs = []
    for table, info in schema.items():
        col_str = ", ".join(f"{name} ({dtype})" for name, dtype in info["columns"])
        fk_str = ""
        if info.get("foreign_keys"):
            fk_str = "\nForeign keys: " + ", ".join(
                f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}"
                for fk in info["foreign_keys"]
            )
        content = f"Table: {table}\nColumns: {col_str}{fk_str}"
        if info.get("sample_rows"):
            content += f"\nSample rows: {info['sample_rows']}"
        docs.append(Document(page_content=content, metadata={"table": table}))

    store = QdrantVectorStore(client=client, collection_name=collection, embedding=embeddings)
    store.add_documents(docs)
    return store


def connect(session_id: str, connection_url: str) -> dict:
    """
    Connects this session to a PostgreSQL database, replacing whatever
    it was previously connected to (demo or a different Postgres DB).
    Returns a status dict — same shape as status(session_id) below.
    Raises ConnectionError_ on failure (caller/api.py turns this into
    a 400 response); the session is left unchanged if this fails, so a
    failed reconnect attempt doesn't kick someone back to demo mode.
    """
    result = connect_and_introspect(connection_url)  # raises ConnectionError_ on failure

    schema_store = _build_schema_index(result["schema"])

    with _lock:
        session = get_session(session_id)
        _teardown(session)  # dispose any previous engine this session held
        session.mode = POSTGRES_MODE
        session.engine = result["engine"]
        session.schema_cache = result["schema"]
        session.schema_store = schema_store
        session.table_count = result["table_count"]
        session.column_count = result["column_count"]
        session.connected_at = time.time()
        session.last_error = ""

    return status(session_id)


def disconnect(session_id: str) -> dict:
    """Reverts a session back to the demo database. Never errors — safe to call anytime."""
    with _lock:
        session = get_session(session_id)
        _teardown(session)
        session.mode = DEMO_MODE
        session.engine = None
        session.schema_cache = {}
        session.schema_store = None
        session.db_label = ""
        session.table_count = 0
        session.column_count = 0
        session.connected_at = None
        session.last_error = ""
    return status(session_id)


def status(session_id: str) -> dict:
    session = get_session(session_id)
    if session.mode == POSTGRES_MODE:
        return {
            "mode": "postgres",
            "connected": True,
            "table_count": session.table_count,
            "column_count": session.column_count,
            "connected_at": session.connected_at,
        }
    return {"mode": "demo", "connected": True, "table_count": None, "column_count": None, "connected_at": None}


def get_dialect(session_id: str) -> str:
    """'postgres' or 'sqlite' — used by the validator and generator prompt."""
    session = get_session(session_id)
    return "postgres" if session.mode == POSTGRES_MODE else "sqlite"