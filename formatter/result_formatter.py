"""
Step 7: Result Formatter
Converts raw DB rows into a natural-language summary + table for the user.
"""


def format_result(columns: list, rows: list, sql: str, assumptions: str = "") -> dict:
    if not rows:
        summary = "No results found for that query."
    else:
        summary = f"Found {len(rows)} result(s)."
        if len(rows) == 1 and len(columns) <= 3:
            row_str = ", ".join(f"{col}: {val}" for col, val in zip(columns, rows[0]))
            summary = f"Result — {row_str}"
        elif len(rows) > 1:
            top_row = ", ".join(f"{col}: {val}" for col, val in zip(columns, rows[0]))
            summary = f"Found {len(rows)} result(s). Top result — {top_row}"

    if assumptions:
        summary += f"  (Note: {assumptions})"

    table = [dict(zip(columns, row)) for row in rows]

    return {
        "summary": summary,
        "table": table,
        "sql_used": sql,
        "row_count": len(rows),
    }


if __name__ == "__main__":
    cols = ["name", "total_revenue"]
    rows = [("Gamma Retail", 72000), ("Acme Corp", 57000)]
    result = format_result(cols, rows, "SELECT ...", assumptions="Interpreted 'best' as highest revenue.")
    print(result["summary"])
    print(result["table"])