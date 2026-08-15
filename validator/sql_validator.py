"""
Step 5: SQL Validator / Guardrails
Non-negotiable safety layer. Runs AFTER generation, BEFORE execution.
Uses sqlglot to parse the query into an AST instead of trusting regex.
"""
import sqlglot
from sqlglot import exp

MAX_ROW_LIMIT = 500
DEFAULT_LIMIT = 100

BLOCKED_STATEMENT_TYPES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
    exp.Create,
)


class ValidationResult:
    def __init__(self, is_valid: bool, sql: str = "", reason: str = ""):
        self.is_valid = is_valid
        self.sql = sql  # possibly modified (e.g. LIMIT injected)
        self.reason = reason

    def __repr__(self):
        return f"ValidationResult(is_valid={self.is_valid}, reason='{self.reason}')"


def validate_sql(sql: str, allowed_schema: dict, dialect: str = "sqlite") -> ValidationResult:
    if not sql or not sql.strip():
        return ValidationResult(False, reason="Empty SQL generated")

    try:
        parsed = sqlglot.parse_one(sql, dialect=dialect)
    except Exception as e:
        return ValidationResult(False, reason=f"SQL failed to parse: {e}")

    # 1. Statement type whitelist — SELECT only
    if not isinstance(parsed, exp.Select):
        return ValidationResult(False, reason="Only SELECT statements are allowed")

    for blocked_type in BLOCKED_STATEMENT_TYPES:
        if parsed.find(blocked_type):
            return ValidationResult(False, reason=f"Blocked statement type: {blocked_type.__name__}")

    # 2. Table existence check
    allowed_tables = {t.lower() for t in allowed_schema.keys()}
    referenced_tables = {t.name.lower() for t in parsed.find_all(exp.Table)}

    unknown_tables = referenced_tables - allowed_tables
    if unknown_tables:
        return ValidationResult(False, reason=f"Unknown table(s) referenced: {unknown_tables}")

    # 3. Column existence check (best-effort — skips computed/aggregate aliases)
    allowed_columns = set()
    for table_info in allowed_schema.values():
        for col_name, _ in table_info["columns"]:
            allowed_columns.add(col_name.lower())

    # collect aliases defined in this query (e.g. "SUM(amount) AS total_revenue")
    # so references to them later (e.g. in ORDER BY) aren't flagged as unknown columns
    defined_aliases = {alias.alias_or_name.lower() for alias in parsed.find_all(exp.Alias)}

    for col in parsed.find_all(exp.Column):
        col_name = col.name.lower()
        if col_name == "*" or col_name in allowed_columns or col_name in defined_aliases:
            continue
        return ValidationResult(False, reason=f"Unknown column referenced: '{col_name}'")

    # 4. Row limit enforcement — inject if missing, cap if excessive
    limit_node = parsed.find(exp.Limit)
    if limit_node is None:
        parsed = parsed.limit(DEFAULT_LIMIT)
    else:
        try:
            current_limit = int(limit_node.expression.this)
            if current_limit > MAX_ROW_LIMIT:
                parsed.set("limit", exp.Limit(expression=exp.Literal.number(MAX_ROW_LIMIT)))
        except (ValueError, AttributeError):
            pass  # non-numeric limit, leave as-is — sqlite will error naturally if invalid

    # 5. Basic complexity guard — reject excessive joins (cheap safeguard vs runaway queries)
    join_count = len(list(parsed.find_all(exp.Join)))
    if join_count > 5:
        return ValidationResult(False, reason=f"Query too complex: {join_count} joins exceeds limit")

    final_sql = parsed.sql(dialect=dialect)
    return ValidationResult(True, sql=final_sql, reason="Passed all checks")


if __name__ == "__main__":
    from schema.schema_rag import get_full_schema
    schema = get_full_schema()

    tests = [
        "SELECT name FROM customers LIMIT 10",
        "DROP TABLE customers",
        "SELECT * FROM fake_table",
        "SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id",
    ]
    for t in tests:
        print(t, "->", validate_sql(t, schema))