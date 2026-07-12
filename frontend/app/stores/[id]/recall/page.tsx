"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import type { RecallResult } from "../../../../lib/types";
import StoreTabs from "../../../../components/StoreTabs";
import { SensBadge } from "../../../../components/Badges";
import { RETRIEVAL_MODES } from "../../../../lib/ui";

export default function RecallLab() {
  const { id } = useParams<{ id: string }>();
  const [storeName, setStoreName] = useState("");
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.3);
  const [incExpired, setIncExpired] = useState(false);
  const [incArchived, setIncArchived] = useState(false);
  const [res, setRes] = useState<RecallResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    api.store(id).then((s) => { setStoreName(s.name); if (s.recall_tests?.[0]) setQ(s.recall_tests[0].query); }).catch(() => {});
    api.recallTests(id).then(setHistory).catch(() => {});
  }, [id]);

  async function run() {
    if (!q.trim()) return;
    setBusy(true); setRes(null);
    try {
      setRes(await api.recall(id, { query: q, retrieval_mode: mode, top_k: topK, threshold, include_expired: incExpired, include_archived: incArchived, save: true }));
      api.recallTests(id).then(setHistory);
    } finally { setBusy(false); }
  }

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Recall Test Lab</h1>
      <StoreTabs storeId={id} />
      <p className="mt-4 text-[13px] text-dim">Enter a query and see exactly what the AI would remember — which memories are retrieved, why, and what's excluded.</p>
      <p className="mt-2 inline-block rounded-md border border-ok/40 bg-ok/10 px-2.5 py-1 text-[11.5px] text-ok">Real semantic recall — local <b>bge-small</b> embeddings + cosine similarity in <b>semantic</b> / <b>hybrid</b> modes (blended with recency + tags); <b>keyword</b> mode is pure lexical. Falls back to keyword if the model is unavailable.</p>

      <div className="mt-5 grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="space-y-3">
          <div className="rounded-xl border border-line bg-panel p-4">
            <label className="block"><span className="mb-1 block text-[11px] text-faint">Query</span>
              <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={2} placeholder="Does this customer prefer outdoor seating?" className={inp} onKeyDown={(e) => { if (e.key === "Enter" && e.metaKey) run(); }} /></label>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <label><span className="mb-1 block text-[11px] text-faint">Mode</span><select value={mode} onChange={(e) => setMode(e.target.value)} className={inp}>{RETRIEVAL_MODES.map((m) => <option key={m} value={m}>{m}</option>)}</select></label>
              <label><span className="mb-1 block text-[11px] text-faint">Top K</span><input type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(+e.target.value)} className={inp} /></label>
            </div>
            <label className="mt-2 block"><span className="mb-1 block text-[11px] text-faint">Similarity threshold · {threshold.toFixed(2)}</span>
              <input type="range" min={0} max={1} step={0.05} value={threshold} onChange={(e) => setThreshold(+e.target.value)} className="w-full" /></label>
            <div className="mt-2 flex flex-col gap-1.5">
              <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={incExpired} onChange={(e) => setIncExpired(e.target.checked)} /> include expired</label>
              <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={incArchived} onChange={(e) => setIncArchived(e.target.checked)} /> include archived</label>
            </div>
            <button onClick={run} disabled={busy || !q.trim()} className="mt-3 w-full rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Retrieving…" : "Run recall"}</button>
          </div>
          {history.length > 0 && (
            <div className="rounded-xl border border-line bg-panel p-4">
              <div className="mb-2 text-[11px] uppercase tracking-wider text-faint">Recent tests</div>
              {history.slice(0, 6).map((h) => <button key={h.id} onClick={() => setQ(h.query)} className="block w-full truncate py-1 text-left text-[12px] text-dim hover:text-ink">"{h.query}" <span className="text-faint">· {h.score}</span></button>)}
            </div>
          )}
        </div>

        <div>
          {!res ? <div className="rounded-2xl border border-dashed border-line py-20 text-center text-[13px] text-faint">Run a recall test to see what's retrieved and why.</div> : (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-panel p-4">
                <div><div className="text-[22px] font-bold text-ink">{Math.round(res.recall_quality_score * 100)}%</div><div className="text-[10px] uppercase tracking-wider text-faint">recall quality</div></div>
                <div className="text-[12px] text-dim"><div>{res.retrieved.length} retrieved · {res.excluded.length} excluded</div><div className="text-faint">{res.mode} · {res.latency_ms}ms</div></div>
              </div>

              {res.suggestions.length > 0 && (
                <div className="rounded-xl border border-ind/40 bg-ind/10 p-3 text-[12.5px] text-ind">
                  <div className="mb-1 font-medium">Suggested tuning</div>
                  {res.suggestions.map((s, i) => <div key={i}>• {s}</div>)}
                </div>
              )}

              <div className="space-y-2">
                {res.retrieved.map((r) => (
                  <div key={r.id} className={`rounded-xl border p-3 ${r.expired ? "border-warn/40 bg-warn/5" : "border-line bg-panel"}`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[13.5px] font-medium text-ink">{r.title}</span>
                      <span className="flex items-center gap-2"><SensBadge sensitivity={r.sensitivity || "low"} /><span className="rounded-full bg-ok/10 px-2 py-0.5 text-[11px] text-ok">{r.score.toFixed(2)}</span></span>
                    </div>
                    <p className="mt-1 text-[12.5px] leading-relaxed text-dim">{r.content}</p>
                    <div className="mt-1 text-[11px] text-faint">{r.reason}{r.expired && " · ⚠ expired"} · {r.source}{r.expires_at ? ` · expires ${r.expires_at.slice(0, 10)}` : ""}</div>
                  </div>
                ))}
                {!res.retrieved.length && <div className="rounded-xl border border-dashed border-line py-8 text-center text-[13px] text-faint">No memory passed the threshold. Try lowering it.</div>}
              </div>

              {res.assembled_context && (
                <div className="rounded-xl border border-line bg-panel2 p-3">
                  <div className="mb-1 text-[10px] uppercase tracking-wider text-cy">Assembled context</div>
                  <pre className="whitespace-pre-wrap text-[12px] leading-relaxed text-ink">{res.assembled_context}</pre>
                </div>
              )}
              {res.excluded.length > 0 && (
                <details className="rounded-xl border border-line bg-panel2 p-3">
                  <summary className="cursor-pointer text-[12px] text-dim">Excluded memories ({res.excluded.length})</summary>
                  {res.excluded.map((e, i) => <div key={i} className="mt-1 text-[12px] text-faint">• {e.title} — {e.reason}</div>)}
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
const inp = "w-full rounded-lg border border-line bg-panel2 px-2.5 py-2 text-[12.5px] text-ink outline-none focus:border-vi/60";
