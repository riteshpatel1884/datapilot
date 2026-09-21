// "use client";

// import { useEffect, useRef } from "react";
// import { SCHEMA_TABLES } from "./schema-data";

// export default function SchemaPanel({ open, onClose }) {
//   const dialogRef = useRef(null);

//   useEffect(() => {
//     if (!open) return;

//     function handleKeyDown(e) {
//       if (e.key === "Escape") onClose();
//     }
//     function handleClickOutside(e) {
//       if (dialogRef.current && !dialogRef.current.contains(e.target)) {
//         onClose();
//       }
//     }

//     document.addEventListener("keydown", handleKeyDown);
//     document.addEventListener("mousedown", handleClickOutside);
//     return () => {
//       document.removeEventListener("keydown", handleKeyDown);
//       document.removeEventListener("mousedown", handleClickOutside);
//     };
//   }, [open, onClose]);

//   if (!open) return null;

//   return (
//     <div className="schema-popup-backdrop" role="presentation">
//       <div
//         className="schema-popup"
//         role="dialog"
//         aria-modal="true"
//         aria-labelledby="schema-popup-title"
//         ref={dialogRef}
//       >
//         <div className="schema-popup-header">
//           <h2 id="schema-popup-title" className="schema-popup-title">
//             Database schema
//           </h2>
//           <button className="schema-popup-close" onClick={onClose} aria-label="Close schema panel" type="button">
//             ×
//           </button>
//         </div>

//         <p className="schema-popup-subtitle">
//           Table and column names only — no records shown. Use these to phrase your question.
//         </p>

//         <div className="schema-popup-body">
//           {SCHEMA_TABLES.map((table) => (
//             <div key={table.name} className="schema-table-block">
//               <div className="schema-table-name">{table.name}</div>
//               {table.description && <p className="schema-table-description">{table.description}</p>}
//               <table className="schema-column-table">
//                 <thead>
//                   <tr>
//                     <th>Column</th>
//                     <th>Type</th>
//                     <th>Note</th>
//                   </tr>
//                 </thead>
//                 <tbody>
//                   {table.columns.map((col) => (
//                     <tr key={col.name}>
//                       <td className="schema-col-name">{col.name}</td>
//                       <td className="schema-col-type">{col.type}</td>
//                       <td className="schema-col-note">{col.note}</td>
//                     </tr>
//                   ))}
//                 </tbody>
//               </table>
//             </div>
//           ))}
//         </div>
//       </div>
//     </div>
//   );
// }


"use client";

import { useEffect, useRef, useState } from "react";
import { SCHEMA_TABLES as STATIC_DEMO_SCHEMA } from "./schema-data";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Read-only schema reference popup. Shows table + column names/types
 * (and, when connected to a real database, primary/foreign keys) —
 * deliberately no row-level data ever, so the person gets exactly
 * what they need to phrase good questions without exposing records.
 *
 * Fetches from GET /schema?session_id=... — works identically for the
 * demo database and a connected PostgreSQL one, since the backend's
 * schema.schema_rag.get_full_schema() already abstracts that (see
 * db/connection_manager.py). Falls back to the bundled static demo
 * schema if the fetch fails, so this never leaves someone looking at
 * a blank panel just because the backend was briefly unreachable.
 */
export default function SchemaPanel({ open, onClose, sessionId, dbMode }) {
  const dialogRef = useRef(null);
  const [tables, setTables] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);

    const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    fetch(`${API_URL}/schema${qs}`)
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        setTables(data.tables || []);
      })
      .catch(() => {
        if (cancelled) return;
        // fall back to the bundled static demo schema shape
        setTables(
          STATIC_DEMO_SCHEMA.map((t) => ({
            name: t.name,
            columns: t.columns.map((c) => ({ name: c.name, type: c.type })),
            primary_key: [],
            foreign_keys: [],
          }))
        );
      })
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [open, sessionId]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    function handleClickOutside(e) {
      if (dialogRef.current && !dialogRef.current.contains(e.target)) onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="schema-popup-backdrop" role="presentation">
      <div
        className="schema-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="schema-popup-title"
        ref={dialogRef}
      >
        <div className="schema-popup-header">
          <h2 id="schema-popup-title" className="schema-popup-title">
            Database schema
          </h2>
          <button className="schema-popup-close" onClick={onClose} aria-label="Close schema panel" type="button">
            ×
          </button>
        </div>

        <p className="schema-popup-subtitle">
          {dbMode === "postgres" ? "Your connected database. " : "The demo database. "}
          Table and column names only — no records shown. Use these to phrase your question.
        </p>

        <div className="schema-popup-body">
          {loading && <p className="schema-loading">Loading schema…</p>}
          {!loading && tables && tables.map((table) => (
            <div key={table.name} className="schema-table-block">
              <div className="schema-table-name">{table.name}</div>
              <table className="schema-column-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {table.columns.map((col) => {
                    const isPk = table.primary_key?.includes(col.name);
                    const fk = table.foreign_keys?.find((f) => f.column === col.name);
                    const note = isPk
                      ? "Primary key"
                      : fk
                      ? `References ${fk.references_table}.${fk.references_column}`
                      : "";
                    return (
                      <tr key={col.name}>
                        <td className="schema-col-name">{col.name}</td>
                        <td className="schema-col-type">{col.type}</td>
                        <td className="schema-col-note">{note}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}