"use client";
import { useEffect, useState } from "react";

/* In-app guide: what MemoryMaker is and how to ship your first memory store.
   Auto-opens once per browser (localStorage) and lives behind the Guide nav button. */

const STORAGE_KEY = "mm_guide_v1";

const STEPS: { title: string; body: string }[] = [
  {
    title: "Create a memory store",
    body: "A store is a governed pool of AI memory. On Stores, click New Store — pick the memory type, storage backend, retrieval strategy, risk level, and retention TTL, plus governance toggles like redaction and right-to-be-forgotten.",
  },
  {
    title: "Ingest memories",
    body: "On the Ingestion tab, add knowledge as pasted text, JSON, uploaded TXT/MD/CSV files, or a website URL. Every entry runs through the store's rules — secrets are redacted, sensitivity is scored, and retention is applied.",
  },
  {
    title: "Test recall",
    body: "The Recall Test Lab shows exactly what an AI would remember. Type a query and get real semantic recall (local bge-small embeddings + cosine similarity) — tune mode, top-K, and threshold, and see why each memory was retrieved or excluded.",
  },
  {
    title: "Set memory rules",
    body: "On Rules, define what gets remembered, forgotten, expired, redacted, or gated. Redaction and retention/expiry rules are enforced on ingest today; toggle rules on and off per store.",
  },
  {
    title: "Review governance",
    body: "The Governance tab controls risk level, PII risk, audit logging, tenant isolation, and deletion rights — and can run a risk scan over the store's contents to surface flags before anything ships.",
  },
  {
    title: "Deploy as a recall API",
    body: "Export & Deploy serves the store as a live token-authed endpoint: POST a query, get semantically-recalled memories back. Or export a portable Nyquest Memory Package and use it in Builder, Marketplace, or Prompter.",
  },
];

export default function HelpGuide() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) setOpen(true);
    } catch {}
  }, []);

  const dismiss = () => {
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch {}
    setOpen(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") dismiss(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
        aria-label="Open the MemoryMaker guide"
      >
        Guide
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={dismiss} role="dialog" aria-modal="true" aria-label="MemoryMaker guide">
          <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-1 flex items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-vi/15 text-[13px] text-vi">◈</span>
              <h2 className="text-[16px] font-semibold">How MemoryMaker works</h2>
            </div>
            <p className="mb-5 text-[13px] text-dim">
              Design, test, and govern what your AI remembers — then serve it as a real recall API. Six steps from zero to deployed memory:
            </p>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-vi/15 text-[12px] font-semibold text-vi">{i + 1}</span>
                  <div>
                    <div className="text-[13.5px] font-medium">{s.title}</div>
                    <div className="text-[12.5px] leading-relaxed text-dim">{s.body}</div>
                  </div>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
              <a href="https://foundry.zoidlab.ai" className="text-[12px] text-dim hover:text-ink">◈ All Foundry apps</a>
              <button onClick={dismiss} className="rounded-lg bg-vi px-4 py-1.5 text-[12.5px] font-semibold text-white hover:opacity-90">
                Got it
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
