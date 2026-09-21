"use client";

import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Lets someone connect DataPilot to their own PostgreSQL database as
 * a second data source, alongside (never replacing) the built-in demo
 * database. Two ways in: paste a ready-made connection string (what
 * Neon/Supabase/RDS give you directly — the recommended path), or
 * fill individual host/port/db/user/pass fields.
 *
 * On success, the parent (page.js) is told via onConnected so it can
 * refresh status/schema; this panel doesn't touch query state itself.
 */
export default function DbConnectPanel({ open, onClose, sessionId, status, onStatusChange }) {
  const dialogRef = useRef(null);
  const [mode, setMode] = useState("string"); // "string" | "fields"
  const [connectionString, setConnectionString] = useState("");
  const [fields, setFields] = useState({
    host: "", port: "5432", database: "", username: "", password: "", sslmode: "require",
  });
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState("");

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

  function updateField(key, value) {
    setFields((f) => ({ ...f, [key]: value }));
  }

  async function handleConnect() {
    setError("");
    setConnecting(true);
    try {
      const body =
        mode === "string"
          ? { session_id: sessionId, connection_string: connectionString.trim() }
          : {
              session_id: sessionId,
              host: fields.host.trim(),
              port: Number(fields.port) || 5432,
              database: fields.database.trim(),
              username: fields.username.trim(),
              password: fields.password,
              sslmode: fields.sslmode,
            };

      const res = await fetch(`${API_URL}/db/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Connection failed (${res.status})`);
      }

      const data = await res.json();
      onStatusChange(data);
      onClose();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setConnecting(false);
    }
  }

  async function handleUseDemo() {
    setError("");
    setConnecting(true);
    try {
      const res = await fetch(`${API_URL}/db/disconnect?session_id=${encodeURIComponent(sessionId)}`, {
        method: "POST",
      });
      const data = await res.json();
      onStatusChange(data);
      onClose();
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setConnecting(false);
    }
  }

  const isConnected = status?.mode === "postgres";

  return (
    <div className="db-popup-backdrop" role="presentation">
      <div className="db-popup" role="dialog" aria-modal="true" aria-labelledby="db-popup-title" ref={dialogRef}>
        <div className="db-popup-header">
          <h2 id="db-popup-title" className="db-popup-title">Database</h2>
          <button className="db-popup-close" onClick={onClose} aria-label="Close" type="button">×</button>
        </div>

        <div className="db-current">
          <span className="db-current-dot" data-state={isConnected ? "postgres" : "demo"} />
          {isConnected ? (
            <span>
              Connected to <strong>PostgreSQL</strong> — {status.table_count} table
              {status.table_count === 1 ? "" : "s"}, {status.column_count} columns
            </span>
          ) : (
            <span>Using the built-in <strong>demo database</strong> — mall purchase data</span>
          )}
        </div>

        {isConnected && (
          <button className="db-use-demo-button" onClick={handleUseDemo} disabled={connecting} type="button">
            ← Switch back to demo database
          </button>
        )}

        <div className="db-divider">
          <span>{isConnected ? "or connect a different database" : "or connect your own PostgreSQL database"}</span>
        </div>

        <div className="db-mode-tabs">
          <button
            className="db-mode-tab"
            data-active={mode === "string"}
            onClick={() => setMode("string")}
            type="button"
          >
            Connection string
          </button>
          <button
            className="db-mode-tab"
            data-active={mode === "fields"}
            onClick={() => setMode("fields")}
            type="button"
          >
            Fill in fields
          </button>
        </div>

        {mode === "string" ? (
          <div className="db-form-group">
            <label className="db-label" htmlFor="db-conn-string">
              Connection string
            </label>
            <textarea
              id="db-conn-string"
              className="db-textarea"
              placeholder="postgresql://user:password@host:5432/database?sslmode=require"
              value={connectionString}
              onChange={(e) => setConnectionString(e.target.value)}
              rows={3}
            />
            <p className="db-hint">
              This is what Neon, Supabase, or RDS give you directly on your database&apos;s
              connection page — paste it as-is.
            </p>
          </div>
        ) : (
          <div className="db-fields-grid">
            <div className="db-form-group">
              <label className="db-label" htmlFor="db-host">Host</label>
              <input id="db-host" className="db-input" value={fields.host}
                     onChange={(e) => updateField("host", e.target.value)}
                     placeholder="ep-example.neon.tech" />
            </div>
            <div className="db-form-group db-form-group-narrow">
              <label className="db-label" htmlFor="db-port">Port</label>
              <input id="db-port" className="db-input" value={fields.port}
                     onChange={(e) => updateField("port", e.target.value)} placeholder="5432" />
            </div>
            <div className="db-form-group">
              <label className="db-label" htmlFor="db-database">Database</label>
              <input id="db-database" className="db-input" value={fields.database}
                     onChange={(e) => updateField("database", e.target.value)} placeholder="mydb" />
            </div>
            <div className="db-form-group">
              <label className="db-label" htmlFor="db-username">Username</label>
              <input id="db-username" className="db-input" value={fields.username}
                     onChange={(e) => updateField("username", e.target.value)}
                     placeholder="datapilot_readonly" />
            </div>
            <div className="db-form-group">
              <label className="db-label" htmlFor="db-password">Password</label>
              <input id="db-password" className="db-input" type="password" value={fields.password}
                     onChange={(e) => updateField("password", e.target.value)} />
            </div>
            <div className="db-form-group db-form-group-narrow">
              <label className="db-label" htmlFor="db-sslmode">SSL mode</label>
              <select id="db-sslmode" className="db-input" value={fields.sslmode}
                      onChange={(e) => updateField("sslmode", e.target.value)}>
                <option value="require">require</option>
                <option value="prefer">prefer</option>
                <option value="disable">disable</option>
              </select>
            </div>
          </div>
        )}

        <div className="db-security-note">
          <ShieldIcon />
          <span>
            The connection is forced read-only at the driver level, on top of DataPilot&apos;s
            existing SQL validator — but for real use, connect with a database role that only has
            SELECT privileges. That way even a bug here can&apos;t write to your data.
          </span>
        </div>

        {error && <div className="db-error">{error}</div>}

        <div className="db-actions">
          <button className="db-connect-button" onClick={handleConnect} disabled={connecting} type="button">
            {connecting ? "Connecting…" : "Test & Connect"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" style={{ flexShrink: 0, marginTop: 2 }}>
      <path d="M8 1.5l5.5 2v4c0 3.5-2.3 5.9-5.5 7-3.2-1.1-5.5-3.5-5.5-7v-4l5.5-2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
      <path d="M5.7 8.1l1.6 1.6 3-3.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}