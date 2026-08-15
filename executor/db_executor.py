"""
Step 6: Execution Engine
Executes VALIDATED SQL only. Never call this directly on raw LLM output.

Note: SQLite doesn't have Postgres-style read-only roles, so this opens
the connection in read-only mode via URI (immutable=0, mode=ro) as the
closest equivalent. For Postgres/Neon in production, use a dedicated
read-only DB role instead — see README.
"""
import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "sample.db")
QUERY_TIMEOUT_SECONDS = 5


class ExecutionResult:
    def __init__(self, success: bool, rows=None, columns=None, error: str = "", execution_time_ms: float = 0):
        self.success = success
        self.rows = rows or []
        self.columns = columns or []
        self.error = error
        self.execution_time_ms = execution_time_ms

    def __repr__(self):
        return f"ExecutionResult(success={self.success}, rows={len(self.rows)}, error='{self.error}')"


def execute_query(sql: str, db_path: str = DB_PATH) -> ExecutionResult:
    start = time.time()
    try:
        # read-only URI connection — app-level enforcement of the "no writes" guarantee
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=QUERY_TIMEOUT_SECONDS)
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        conn.close()

        elapsed = (time.time() - start) * 1000
        return ExecutionResult(True, rows=rows, columns=columns, execution_time_ms=round(elapsed, 2))

    except sqlite3.Error as e:
        elapsed = (time.time() - start) * 1000
        # sanitize — never leak raw DB internals to the end user
        return ExecutionResult(False, error="Query execution failed", execution_time_ms=round(elapsed, 2))


if __name__ == "__main__":
    result = execute_query("SELECT name, city FROM customers LIMIT 5")
    print(result)
    print(result.columns)
    print(result.rows)