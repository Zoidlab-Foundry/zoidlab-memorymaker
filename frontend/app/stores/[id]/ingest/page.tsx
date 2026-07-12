"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import StoreTabs from "../../../../components/StoreTabs";

export default function Ingest() {
  const { id } = useParams<{ id: string }>();
  const [storeName, setStoreName] = useState("");
  const [tab, setTab] = useState<"text" | "json" | "file" | "url">("text");
  const [text, setText] = useState(""); const [title, setTitle] = useState(""); const [tags, setTags] = useState("");
  const [url, setUrl] = useState("");
  const [jsonText, setJsonText] = useState('[\n  { "title": "Example", "content": "Customer prefers window seats.", "tags": ["preference"] }\n]');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState("");
  const [jobs, setJobs] = useState<any[]>([]);

  const loadJobs = () => api.ingestionJobs(id).then(setJobs).catch(() => {});
  useEffect(() => { api.store(id).then((s) => setStoreName(s.name)).catch(() => {}); loadJobs(); }, [id]);

  async function go(fn: () => Promise<any>) {
    setBusy(true); setErr(""); setResult(null);
    try { const r = await fn(); setResult(r); loadJobs(); }
    catch (e: any) { setErr(e.status === 401 ? "Sign in with your Nyquest account to ingest." : e.message); }
    finally { setBusy(false); }
  }
  const runText = () => go(() => api.ingestText(id, { text, title: title || undefined, tags: tags.split(",").map((t) => t.trim()).filter(Boolean) }));
  const runJson = () => go(() => api.ingestJson(id, JSON.parse(jsonText)));
  const runFile = (file: File) => go(() => api.ingestFile(id, file));
  const runUrl = () => go(() => api.ingestUrl(id, { url: url.trim() }));

  const SOURCES = [["text", "Manual / Text"], ["json", "Paste JSON"], ["file", "Upload TXT / MD / CSV"], ["url", "Website / URL"]] as const;
  const PLACEHOLDERS = ["PDF (soon)", "API source (soon)", "Workflow output (soon)", "Agent conversation (soon)"];

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Ingestion</h1>
      <StoreTabs storeId={id} />
      <p className="mt-4 text-[13px] text-dim">Add knowledge. Every entry runs through the store's rules — secrets are redacted, sensitivity is scored, and retention is applied.</p>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_300px]">
        <div>
          <div className="mb-4 flex gap-1 border-b border-line">
            {SOURCES.map(([k, l]) => <button key={k} onClick={() => { setTab(k); setResult(null); }} className={`px-3 py-2 text-[13px] ${tab === k ? "border-b-2 border-vi text-ink" : "text-dim hover:text-ink"}`}>{l}</button>)}
          </div>
          {tab === "text" && (
            <div className="space-y-2">
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (optional)" className={inp} />
              <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="tags, comma-separated" className={inp} />
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={8} placeholder="Paste text. Blank lines split into separate memories." className={inp} />
              <button onClick={runText} disabled={busy || !text.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Ingesting…" : "Ingest text"}</button>
            </div>
          )}
          {tab === "json" && (
            <div className="space-y-2">
              <textarea value={jsonText} onChange={(e) => setJsonText(e.target.value)} rows={10} className={inp + " font-mono text-[12px]"} />
              <button onClick={runJson} disabled={busy} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Ingesting…" : "Ingest JSON"}</button>
            </div>
          )}
          {tab === "url" && (
            <div className="space-y-2">
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/page" className={inp} />
              <p className="text-[11px] text-faint">The page is fetched, stripped to text, split into paragraphs, and each becomes a memory (through the store's rules). Only public URLs are allowed.</p>
              <button onClick={runUrl} disabled={busy || !url.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Fetching…" : "Ingest URL"}</button>
            </div>
          )}
          {tab === "file" && (
            <label className="flex cursor-pointer flex-col items-center rounded-2xl border border-dashed border-line py-12 text-center text-[13px] text-dim hover:border-vi/50">
              <span className="text-[24px]">📄</span><span className="mt-2">Upload a .txt, .md, or .csv file</span>
              <span className="mt-1 text-[11px] text-faint">Markdown splits on headings · CSV maps title/content/tags columns</span>
              <input type="file" accept=".txt,.md,.markdown,.csv" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) runFile(f); }} />
            </label>
          )}
          {err && <div className="mt-3 rounded-lg border border-bad/40 bg-bad/10 px-4 py-2 text-[13px] text-bad">{err}</div>}
          {result && (
            <div className="mt-3 rounded-lg border border-ok/40 bg-ok/10 px-4 py-3 text-[13px] text-ok">
              Ingested {result.created} memor{result.created === 1 ? "y" : "ies"}{result.failed ? `, ${result.failed} skipped` : ""}.
              {(result.logs || []).length > 0 && <div className="mt-1 text-[11px] text-warn">{result.logs.map((l: any, i: number) => <div key={i}>⚠ {l.skipped}: {Array.isArray(l.reason) ? l.reason.join("; ") : l.reason}</div>)}</div>}
              <Link href={`/stores/${id}/memories`} className="mt-1 block text-[12px] text-cy hover:underline">View memories →</Link>
            </div>
          )}
        </div>
        <div className="space-y-3">
          <div className="rounded-xl border border-line bg-panel p-4">
            <div className="mb-2 text-[11px] uppercase tracking-wider text-faint">More sources</div>
            <div className="flex flex-wrap gap-1.5">{PLACEHOLDERS.map((p) => <span key={p} className="rounded-full border border-line px-2 py-1 text-[11px] text-faint">{p}</span>)}</div>
          </div>
          <div className="rounded-xl border border-line bg-panel p-4">
            <div className="mb-2 text-[11px] uppercase tracking-wider text-faint">Recent jobs</div>
            {jobs.slice(0, 6).map((j) => <div key={j.id} className="flex justify-between border-b border-line py-1.5 text-[12px] last:border-0"><span className="text-dim">{j.source_type} · {j.source_name?.slice(0, 18)}</span><span className="text-faint">+{j.records_created}</span></div>)}
            {!jobs.length && <p className="text-[12px] text-faint">No ingestion jobs yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
const inp = "w-full rounded-lg border border-line bg-panel2 px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/60";
