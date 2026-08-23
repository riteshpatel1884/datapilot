/**
 * Schema metadata shown to the user in the "View database schema" popup.
 *
 * Deliberately contains ONLY table/column names and types — no actual
 * row data. Even though this demo's data is synthetic, the app is built
 * to never surface raw records to an unauthenticated user; this file
 * keeps that boundary explicit rather than accidentally leaking real
 * rows if a "helpful" sample was added here later.
 *
 * Keep this in sync with db/setup_db.py's CREATE TABLE statements by
 * hand for now. If the schema changes often, replace this with a fetch
 * from a backend GET /schema endpoint (see note in SchemaPanel.jsx).
 */

export const SCHEMA_TABLES = [
  {
    name: "customers",
    description: "One row per shopper.",
    columns: [
      { name: "customer_id", type: "INTEGER", note: "Primary key" },
      { name: "name", type: "TEXT", note: "" },
      { name: "city", type: "TEXT", note: "" },
      { name: "signup_date", type: "TEXT", note: "ISO date" },
    ],
  },
  {
    name: "orders",
    description: "One row per item purchased.",
    columns: [
      { name: "order_id", type: "INTEGER", note: "Primary key" },
      { name: "customer_id", type: "INTEGER", note: "References customers.customer_id" },
      { name: "item_name", type: "TEXT", note: "" },
      { name: "category", type: "TEXT", note: "" },
      { name: "amount", type: "REAL", note: "Order value" },
      { name: "order_date", type: "TEXT", note: "ISO date" },
    ],
  },
];