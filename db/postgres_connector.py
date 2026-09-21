"""
PostgreSQL connection + introspection layer.

This is the second data source alongside the existing demo SQLite
database (db/sample.db) — see db/connection_manager.py for how a
session picks between the two. Nothing in here ever touches the demo
database or its code path.

Security model (defense in depth, matching the standard "don't expose
your database directly" advice):

  1. The connection is forced read-only at the SQLAlchemy/psycopg2
     level (`postgresql_readonly=True` execution option) — even if
     every other layer failed, the driver itself rejects writes.
  2. A short statement_timeout is set so a runaway/expensive query
     can't hang the connection indefinitely.
  3. sql_validator.py's SELECT-only AST check still runs before any
     SQL from here ever reaches execute_query_postgres() — this file
     doesn't skip that, it's an additional layer underneath it.

STRONGLY RECOMMENDED for real use: also create an actual read-only
role in the target database itself, so even a compromised app server
can't write:

    CREATE USER datapilot_readonly WITH PASSWORD '...';
    GRANT CONNECT ON DATABASE your_db TO datapilot_readonly;
    GRANT USAGE ON SCHEMA public TO datapilot_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO datapilot_readonly;

That's a DB-level guarantee this code can't override even if it tried.
The three layers above are what this app controls; that role is what
you (or the interviewer) control on the database side.
"""
import re
import time
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

MAX_TABLES = 300          # soft cap so a 5000-table warehouse doesn't hang introspection
SAMPLE_ROWS_PER_TABLE = 2  # matches the demo sqlite path's sample-row count
STATEMENT_TIMEOUT_MS = 8000

# Whether introspection includes a couple of sample rows per table in the
# schema text sent to the LLM (helps grounding — same thing the demo path
# already does). This is NEVER sent to the frontend/SchemaPanel regardless
# of this setting (see api.py's /schema endpoint) — this only controls
# what the LLM itself sees for query generation. Flip to False if you'd
# rather the LLM never sees any real row content from a connected DB.
INCLUDE_SAMPLE_ROWS_IN_LLM_CONTEXT = True


class ConnectionError_(Exception):
    """Raised for any connect/introspect failure, with a user-safe message."""
    pass


def build_connection_url(host: str, port, database: str, username: str,
                          password: str, sslmode: str = "require") -> str:
    """
    Builds a postgresql:// URL from individual fields — used by the
    "advanced" connection form. Neon/managed providers generally give
    you a ready-made connection string instead; use that directly with
    connect_with_url() rather than this, if you have one.
    """
    user_enc = quote_plus(username)
    pass_enc = quote_plus(password)
    port = port or 5432
    url = f"postgresql+psycopg2://{user_enc}:{pass_enc}@{host}:{port}/{database}"
    if sslmode:
        url += f"?sslmode={sslmode}"
    return url


def _redact(url: str) -> str:
    """For error messages/logs — never let a raw password reach a log line."""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


def _make_engine(url: str) -> Engine:
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={"options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"},
    )
    # Forces every connection from this engine to be read-only at the
    # driver level — this is layer 1 of defense-in-depth, independent
    # of the SQL validator and independent of whatever role the DB user
    # actually has (a belt-and-suspenders backstop, not a replacement
    # for a real read-only DB role).
    return engine.execution_options(postgresql_readonly=True)


def test_connection(url: str) -> tuple[bool, str]:
    """Returns (ok, error_message). error_message is empty on success."""
    try:
        engine = _make_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, ""
    except SQLAlchemyError as e:
        # str(e) from psycopg2/SQLAlchemy can be verbose but doesn't
        # normally contain the password (that's in the DSN, not the
        # error text) — still redact defensively in case a driver ever
        # echoes the DSN back in an error.
        return False, _redact(str(e)).split("\n")[0][:300]
    except Exception as e:
        return False, str(e)[:300]


def introspect_schema(engine: Engine) -> dict:
    """
    Returns a schema dict in the SAME shape schema_rag.get_full_schema()
    already returns for the demo SQLite path:

      {table_name: {"columns": [(name, type_str), ...],
                     "sample_rows": [...],
                     "primary_key": [...],
                     "foreign_keys": [{"column", "references_table", "references_column"}]}}

    so every downstream consumer (validator, generator prompt builder,
    /schema API endpoint) works identically regardless of which data
    source produced the schema.
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema="public")

    if len(table_names) > MAX_TABLES:
        table_names = table_names[:MAX_TABLES]

    schema = {}
    with engine.connect() as conn:
        for table in table_names:
            try:
                columns_info = inspector.get_columns(table, schema="public")
                columns = [(c["name"], str(c["type"])) for c in columns_info]

                pk_info = inspector.get_pk_constraint(table, schema="public")
                primary_key = pk_info.get("constrained_columns", []) or []

                fk_info = inspector.get_foreign_keys(table, schema="public")
                foreign_keys = [
                    {
                        "column": fk["constrained_columns"][0] if fk["constrained_columns"] else "",
                        "references_table": fk["referred_table"],
                        "references_column": fk["referred_columns"][0] if fk["referred_columns"] else "",
                    }
                    for fk in fk_info
                ]

                sample_rows = []
                if INCLUDE_SAMPLE_ROWS_IN_LLM_CONTEXT:
                    try:
                        result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT {SAMPLE_ROWS_PER_TABLE}'))
                        sample_rows = [tuple(row) for row in result.fetchall()]
                    except SQLAlchemyError:
                        sample_rows = []  # a table this role can't SELECT from — skip sampling, keep the schema entry

                schema[table] = {
                    "columns": columns,
                    "sample_rows": sample_rows,
                    "primary_key": primary_key,
                    "foreign_keys": foreign_keys,
                }
            except SQLAlchemyError:
                continue  # skip a table introspection can't read metadata for, don't fail the whole connect

    return schema


def connect_and_introspect(url: str) -> dict:
    """
    High-level entry point used by connection_manager.connect().
    Raises ConnectionError_ with a user-safe message on failure.
    Returns {"engine": Engine, "schema": dict, "table_count": int, "column_count": int}.
    """
    ok, error = test_connection(url)
    if not ok:
        raise ConnectionError_(f"Could not connect: {error}")

    engine = _make_engine(url)
    try:
        schema = introspect_schema(engine)
    except Exception as e:
        engine.dispose()
        raise ConnectionError_(f"Connected, but schema introspection failed: {e}")

    if not schema:
        engine.dispose()
        raise ConnectionError_(
            "Connected, but found no readable tables in the 'public' schema. "
            "Check the connected role has SELECT + USAGE privileges."
        )

    table_count = len(schema)
    column_count = sum(len(t["columns"]) for t in schema.values())

    return {"engine": engine, "schema": schema, "table_count": table_count, "column_count": column_count}


class ExecutionResult:
    """Mirrors executor.db_executor.ExecutionResult's shape exactly, so
    callers don't need to care which data source produced a result."""

    def __init__(self, success: bool, rows=None, columns=None, error: str = "", execution_time_ms: float = 0):
        self.success = success
        self.rows = rows or []
        self.columns = columns or []
        self.error = error
        self.execution_time_ms = execution_time_ms

    def __repr__(self):
        return f"ExecutionResult(success={self.success}, rows={len(self.rows)}, error='{self.error}')"


def execute_query_postgres(engine: Engine, sql: str) -> ExecutionResult:
    """
    Executes VALIDATED, SELECT-only SQL against a Postgres engine that
    is already forced read-only (see _make_engine). Never call this
    directly on raw LLM output — sql_validator.validate_sql() must run
    first, exactly as it does for the demo SQLite path.
    """
    start = time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [tuple(row) for row in result.fetchall()]
        elapsed = (time.time() - start) * 1000
        return ExecutionResult(True, rows=rows, columns=columns, execution_time_ms=round(elapsed, 2))
    except SQLAlchemyError:
        elapsed = (time.time() - start) * 1000
        # sanitize — never leak raw DB internals (table names in error
        # text, etc.) to the end user, matching the sqlite executor's
        # same choice
        return ExecutionResult(False, error="Query execution failed", execution_time_ms=round(elapsed, 2))