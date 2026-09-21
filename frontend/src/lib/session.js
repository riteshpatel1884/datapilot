"use client";

/**
 * A per-browser-tab-group session id, generated once and kept in
 * localStorage. This is what lets the backend know which frontend
 * "session" a /query, /db/connect, /db/status, /schema call belongs
 * to — see db/connection_manager.py. Two different browsers (or two
 * people) never share one, so connecting a database in one tab never
 * affects what another tab/person is querying.
 */
const STORAGE_KEY = "datapilot-session-id";

export function getSessionId() {
  if (typeof window === "undefined") return null; // SSR guard
  let id = window.localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}