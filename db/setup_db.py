"""
Builds sample.db (SQLite) by loading it from db/customers.csv and
db/orders.csv.

This is now a pure LOADER — it no longer generates random data itself.
The actual data lives in the two CSV files (source of truth, versioned
in git, human-readable). If those CSVs don't exist yet, run
db/generate_data.py first to create them.

Run: python db/setup_db.py   (or: uv run python db/setup_db.py)

Why this split: the old version generated random data inline with no
seed, so re-running it (e.g. on every fresh deploy) produced DIFFERENT
customers/orders each time — silently drifting production data away
from whatever you'd tested locally. Now the CSVs are the fixed,
deterministic source; this script just loads them, so sample.db is
always built from the exact same data regardless of when/where it runs.

After changing the data (edit the CSVs directly, or regenerate them via
generate_data.py), re-run this script AND rebuild the RAG embeddings:
    uv run python -m schema.schema_rag
(only strictly necessary if table/column structure changed — the
embeddings mostly capture schema shape, not row content — but cheap
enough to just always do after a data refresh.)
"""
import csv
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")
CUSTOMERS_CSV = os.path.join(os.path.dirname(__file__), "customers.csv")
ORDERS_CSV = os.path.join(os.path.dirname(__file__), "orders.csv")


def _read_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def setup():
    if not os.path.exists(CUSTOMERS_CSV) or not os.path.exists(ORDERS_CSV):
        raise FileNotFoundError(
            f"Missing {CUSTOMERS_CSV} and/or {ORDERS_CSV}. "
            "Run 'python db/generate_data.py' first to create them."
        )

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT,
            signup_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            order_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    customers_rows = _read_csv(CUSTOMERS_CSV)
    customers = [
        (
            int(row["customer_id"]),
            row["name"],
            row["city"],
            row["signup_date"],
        )
        for row in customers_rows
    ]
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)

    orders_rows = _read_csv(ORDERS_CSV)
    orders = [
        (
            int(row["order_id"]),
            int(row["customer_id"]),
            row["item_name"],
            row["category"],
            float(row["amount"]),
            row["order_date"],
        )
        for row in orders_rows
    ]
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)

    conn.commit()
    conn.close()

    categories = {row["category"] for row in orders_rows}
    print(f"Sample DB created at {DB_PATH}")
    print(f"  {len(customers)} customers (from {CUSTOMERS_CSV})")
    print(f"  {len(orders)} orders across {len(categories)} categories (from {ORDERS_CSV})")


if __name__ == "__main__":
    setup()