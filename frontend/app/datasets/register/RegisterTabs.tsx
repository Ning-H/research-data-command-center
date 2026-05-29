"use client";

import { useState, type ReactNode } from "react";

export function RegisterTabs({ structured, raw }: { structured: ReactNode; raw: ReactNode }) {
  const [mode, setMode] = useState<"structured" | "raw">("structured");

  return (
    <div className="register-tabs">
      <div className="tab-row" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "structured"}
          className={`btn ${mode === "structured" ? "btn--primary" : "btn--ghost"}`}
          onClick={() => setMode("structured")}
        >
          Structured records
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "raw"}
          className={`btn ${mode === "raw" ? "btn--primary" : "btn--ghost"}`}
          onClick={() => setMode("raw")}
        >
          Raw file upload
        </button>
      </div>
      <div hidden={mode !== "structured"}>{structured}</div>
      <div hidden={mode !== "raw"}>{raw}</div>
    </div>
  );
}
