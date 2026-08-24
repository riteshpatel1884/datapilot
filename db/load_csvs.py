"""
Generic CSV loader — drop ANY CSV file(s) into db/data/ and this script
builds a matching SQLite table for each, inferring column types
directly from the data (via pandas), no hand-written schema needed.

Run: python db/load_csvs.py   (or: uv run python db/load_csvs.py)

Rules:
  - Table name = CSV filename (without extension), lowercased,
    non-alphanumeric characters replaced with underscores.
    e.g. "Customer List.csv" -> table "customer_list"
  - Column names are sanitized the same way.
  - Column type is inferred from pandas' dtype for that column:
    int64 -> INTEGER, float64 -> REAL, everything else -> TEXT.
  - If a column is named "id", "<table>_id", or "<table minus
    trailing s>_id" and all its values are unique integers, it's
    made the INTEGER PRIMARY KEY for that table.

THIS REPLACES setup_db.py — delete/stop using that file. It was a
fixed-schema loader for exactly one customers.csv + orders.csv shape;
this one works for any CSVs you drop in, since the whole rest of the
pipeline is already schema-agnostic.

ARCHITECTURE NOTE — why this doesn't touch the RAG/embedding layer:
schema/schema_rag.py already reads schema dynamically at runtime via
get_full_schema() (SELECT name FROM sqlite_master + PRAGMA
table_info), so it automatically picks up whatever tables/columns this
script creates. validator/sql_validator.py is the same — it validates
generated SQL against whatever get_full_schema() returns, not a
hardcoded list. Neither file needs to change for a new schema shape.

WHAT DOES NOT AUTO-ADAPT: schema/few_shot_examples.py is hand-written
SQL patterns using customers/orders column names (e.g. "SELECT c.name,
SUM(o.amount)..."). If your CSVs describe a totally different domain,
the generator will still work — RAG schema retrieval is fully dynamic
— but it'll have zero relevant style examples to draw on for your new
tables, so expect lower-confidence SQL until you add a few examples
matching your actual schema to that file.
"""
import os
import sqlite3

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")


def _sanitize_identifier(name: str) -> str:
    clean = str(name).strip().lower()
    clean = "".join(ch if ch.isalnum() else "_" for ch in clean)
    clean = clean.strip("_") or "unnamed"
    if clean[0].isdigit():
        clean = f"t_{clean}"
    return clean


def _sanitize_table_name(filename: str) -> str:
    return _sanitize_identifier(os.path.splitext(filename)[0])


def _sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: _sanitize_identifier(c) for c in df.columns})


def _sql_type(series: "pd.Series") -> str:
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"


def _detect_primary_key(df: pd.DataFrame, table_name: str) -> str | None:
    singular = table_name[:-1] if table_name.endswith("s") else table_name
    candidates = [c for c in df.columns if c in {"id", f"{table_name}_id", f"{singular}_id"}]
    for col in candidates:
        if pd.api.types.is_integer_dtype(df[col]) and df[col].is_unique:
            return col
    return None


def load_csvs(data_dir: str = DATA_DIR, db_path: str = DB_PATH):
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(
            f"No such directory: {data_dir}\n"
            f"Create it and drop your CSV file(s) inside, e.g. {data_dir}/customers.csv"
        )

    csv_files = sorted(f for f in os.listdir(data_dir) if f.lower().endswith(".csv"))
    if not csv_files:
        raise FileNotFoundError(f"No .csv files found in {data_dir}")

    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    loaded = []

    for filename in csv_files:
        path = os.path.join(data_dir, filename)
        table_name = _sanitize_table_name(filename)

        df = pd.read_csv(path)
        df = _sanitize_columns(df)

        pk_col = _detect_primary_key(df, table_name)

        cols_def = ", ".join(
            f'"{c}" {"INTEGER PRIMARY KEY" if c == pk_col else _sql_type(df[c])}'
            for c in df.columns
        )
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.execute(f'CREATE TABLE "{table_name}" ({cols_def})')
        df.to_sql(table_name, conn, index=False, if_exists="append")

        loaded.append((table_name, len(df), list(df.columns), pk_col))

    conn.commit()
    conn.close()

    print(f"Built {db_path} from {len(csv_files)} CSV file(s):\n")
    for table_name, row_count, columns, pk_col in loaded:
        pk_note = f" (PK: {pk_col})" if pk_col else " (no PK detected)"
        print(f"  {table_name}: {row_count} rows, columns = {columns}{pk_note}")

    print(
        "\nNOTE: schema/few_shot_examples.py is still hand-written for a "
        "customers/orders-shaped schema. If your CSVs describe something "
        "different, the SQL generator will still work (schema retrieval is "
        "fully dynamic) but with no matching style examples to draw on for "
        "your new tables — consider adding 2-3 examples for your actual "
        "schema to that file for higher-confidence SQL.\n\n"
        "Next: rebuild the RAG embeddings so retrieval reflects this schema:\n"
        "  uv run python -m schema.schema_rag"
    )


if __name__ == "__main__":
    load_csvs()