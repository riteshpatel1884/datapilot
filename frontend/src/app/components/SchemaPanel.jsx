"use client";

import { useEffect, useRef } from "react";
import { SCHEMA_TABLES } from "./schema-data";

export default function SchemaPanel({ open, onClose }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    function handleClickOutside(e) {
      if (dialogRef.current && !dialogRef.current.contains(e.target)) {
        onClose();
      }
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
          Table and column names only — no records shown. Use these to phrase your question.
        </p>

        <div className="schema-popup-body">
          {SCHEMA_TABLES.map((table) => (
            <div key={table.name} className="schema-table-block">
              <div className="schema-table-name">{table.name}</div>
              {table.description && <p className="schema-table-description">{table.description}</p>}
              <table className="schema-column-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {table.columns.map((col) => (
                    <tr key={col.name}>
                      <td className="schema-col-name">{col.name}</td>
                      <td className="schema-col-type">{col.type}</td>
                      <td className="schema-col-note">{col.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}