"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "../theme.js";

const NAV = [
  { href: "/", label: "Console" },
  { href: "/docs", label: "Docs" },
  { href: "/about", label: "About" },
];

export const STAGES = ["Guardrail", "Classify", "Generate", "Validate", "Execute", "Format"];

export function Header() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path d="M3 8.5 12 3l9 5.5-9 5.5-9-5.5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M3 8.5V16l9 5 9-5V8.5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M12 13.5V21" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </span>
        <span className="brand-word">
          DataPilot
        </span>
      </Link>

      <nav className="nav" aria-label="Primary">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} className="nav-link" data-active={active}>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        className="theme-toggle"
        onClick={toggle}
        role="switch"
        aria-checked={isDark}
        aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
      >
        <span className="theme-toggle-track">
          <span className="theme-toggle-thumb" data-pos={isDark ? "right" : "left"}>
            {isDark ? <MoonIcon /> : <SunIcon />}
          </span>
        </span>
      </button>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer">
      <span className="footer-trace" aria-hidden="true" />
      <p>
        A natural-language query pipeline over structured data. Every question is guarded, classified,
        generated, validated, executed, and formatted — in that order, every time.
      </p>
    </footer>
  );
}

/**
 * The signature element: a literal trace of the six pipeline stages,
 * reused (in different densities) on every page — as a live animated
 * loop in the hero, as a static legend in the console rail, and as a
 * vertical spine down the About page.
 */
export function PipelineTrace({ orientation = "horizontal", animated = false, activeIndex = -1, failedIndex = -1, dense = false }) {
  return (
    <div
      className="trace"
      data-orientation={orientation}
      data-animated={animated ? "true" : "false"}
      data-dense={dense ? "true" : "false"}
      aria-hidden="true"
    >
      {STAGES.map((stage, i) => {
        const isFailed = failedIndex === i;
        const isDone = activeIndex >= 0 && !isFailed && i <= activeIndex;
        const state = isFailed ? "failed" : isDone ? "done" : "pending";
        return (
          <div className="trace-node" data-state={state} key={stage} style={{ "--i": i }}>
            <span className="trace-dot" />
            <span className="trace-label">{stage}</span>
            {i < STAGES.length - 1 && <span className="trace-connector" data-state={state} />}
          </div>
        );
      })}
    </div>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 16 16" width="10" height="10" fill="none">
      <circle cx="8" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8 1.2v1.4M8 13.4v1.4M14.8 8h-1.4M2.6 8H1.2M12.7 3.3l-1 1M4.3 11.7l-1 1M12.7 12.7l-1-1M4.3 4.3l-1-1" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 16 16" width="10" height="10" fill="none">
      <path d="M13.5 9.8A6 6 0 1 1 6.2 2.5a4.7 4.7 0 0 0 7.3 7.3Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  );
}