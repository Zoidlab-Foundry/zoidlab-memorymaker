"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import type { MemoryEntry } from "../../../../lib/types";
import StoreTabs from "../../../../components/StoreTabs";
import { GovBadges, SensBadge } from "../../../../components/Badges";
import { MEMORY_TYPES, label } from "../../../../lib/ui";

export default function Memories() {
  const { id } = useParams<{ id: string }>();
  const [items, setItems] = useState<MemoryEntry[]>([]);
  const [storeName, setStoreName] = useState("");
  const [f, setF] = useState({ search: "", source: "all", memory_type: "all", sensitivity: "all", sort: "newest", include_archived: "", include_expired: "true" });
  const [drawer, setDrawer] = useState<MemoryEntry | null>(null);
  const [creating, setCreating] = useState(false);

  const load = () => api.memories(id, { search: f.search, source: f.source, memory_type: f.memory_type, sensitivity: f.sensitivity, sort: f.sort, include_archived: f.include_archived, include_expired: f.include_expired }).then((d) => setItems(d.memories)).catch(() => {});
  useEffect(() => { api.store(id).then((s) => setStoreName(s.name)).catch(() => {}); }, [id]);
  useEffect(() => { const t = setTimeout(load, 150); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [f, id]);
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));

  async function act(m: MemoryEntry, action: "archive" | "restore" | "forget") {
    if (action === "forget" && !confirm(`Forget "${m.title}"? This permanently deletes the memory.`)) return;
    await api.memoryAction(m.id, action); setDrawer(null); load();
  }

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Memory Explorer</h1>
      <StoreTabs storeId={id} />

      <div className="mt-5 mb-4 flex flex-wrap items-center gap-2">
        <input value={f.search} onChange={(e) => set("search", e.target.value)} placeholder="Search memories…" className="flex-1 rounded-lg border border-line bg-panel px-3 py-2 text-[13px] text-ink placeholder-faint outline-none focus:border-vi/60" />
        <select value={f.memory_type} onChange={(e) => set("memory_type", e.target.value)} className={sel}><option value="all">All types</option>{MEMORY_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
        <select value={f.sensitivity} onChange={(e) => set("sensitivity", e.target.value)} className={sel}>{["all", "low", "medium", "high"].map((s) => <option key={s} value={s}>{s === "all" ? "All sensitivity" : label(s)}</option>)}</select>
        <select value={f.sort} onChange={(e) => set("sort", e.target.value)} className={sel}>{[["newest", "Newest"], ["oldest", "Oldest"], ["expiring", "Expiring soon"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        <label className="flex items-center gap-1.5 text-[11px] text-dim"><input type="checkbox" checked={!!f.include_archived} onChange={(e) => set("include_archived", e.target.checked ? "true" : "")} /> archived</label>
        <button onClick={() => setCreating(true)} className="rounded-lg bg-vi px-3.5 py-2 text-[12px] font-semibold text-white hover:opacity-90">+ Memory</button>
      </div>

      <div className="text-[12px] text-faint">{items.length} memories</div>
      <div className="mt-2 space-y-2">
        {items.map((m) => (
          <button key={m.id} onClick={() => setDrawer(m)} className="flex w-full items-start gap-3 rounded-xl border border-line bg-panel p-3 text-left hover:border-vi/40">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><span className="truncate text-[13.5px] font-medium text-ink">{m.title}</span>{m.archived_at && <span className="text-[10px] text-faint">archived</span>}</div>
              <p className="mt-0.5 line-clamp-1 text-[12px] text-dim">{m.content}</p>
              <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-faint">
                <span className="rounded bg-white/5 px-1.5 py-0.5 text-dim">{label(m.memory_type)}</span>
                <span>· {m.source}</span>{(m.tags || []).slice(0, 3).map((t) => <span key={t} className="rounded bg-white/5 px-1 py-0.5">{t}</span>)}
                {m.expires_at && <span>· expires {m.expires_at.slice(0, 10)}</span>}
              </div>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1"><SensBadge sensitivity={m.sensitivity} /><span className="text-[10px] text-faint">conf {m.confidence}</span></div>
          </button>
        ))}
        {!items.length && <div className="rounded-2xl border border-dashed border-line py-14 text-center text-[13px] text-faint">No memories. Add one, or import knowledge in Ingestion.</div>}
      </div>

      {drawer && <Drawer m={drawer} onClose={() => setDrawer(null)} onAction={act} />}
      {creating && <CreateMemory storeId={id} onClose={() => setCreating(false)} onCreated={() => { setCreating(false); load(); }} />}
    </div>
  );
}

function Drawer({ m, onClose, onAction }: { m: MemoryEntry; onClose: () => void; onAction: (m: MemoryEntry, a: any) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50" onClick={onClose}>
      <div className="h-full w-full max-w-md overflow-y-auto border-l border-line bg-panel2 p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between"><h2 className="text-[16px] font-semibold text-ink">{m.title}</h2><button onClick={onClose} className="text-faint hover:text-ink">✕</button></div>
        <div className="mt-3"><GovBadges badges={m.badges} /></div>
        <div className="mt-4 rounded-xl border border-line bg-panel p-3 text-[13px] leading-relaxed text-ink">{m.content}</div>
        <dl className="mt-4 space-y-1.5 text-[12px]">
          <D k="Type" v={label(m.memory_type)} /><D k="Source" v={m.source} /><D k="Sensitivity" v={m.sensitivity} />
          <D k="Confidence" v={m.confidence} /><D k="Embedding" v={m.embedding_status} /><D k="Tokens" v={m.token_count} />
          <D k="Created" v={m.created_at?.slice(0, 16).replace("T", " ")} /><D k="Expires" v={m.expires_at?.slice(0, 10) || "never"} />
          <D k="Last accessed" v={m.last_accessed_at?.slice(0, 16).replace("T", " ") || "—"} />
        </dl>
        {(m.tags || []).length > 0 && <div className="mt-3 flex flex-wrap gap-1.5">{m.tags.map((t) => <span key={t} className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-dim">{t}</span>)}</div>}
        <div className="mt-5 flex gap-2">
          {m.archived_at
            ? <button onClick={() => onAction(m, "restore")} className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-cy hover:bg-white/5">Restore</button>
            : <button onClick={() => onAction(m, "archive")} className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim hover:text-ink">Archive</button>}
          <button onClick={() => onAction(m, "forget")} className="rounded-lg border border-bad/40 px-3 py-1.5 text-[12px] text-bad hover:bg-bad/10">Forget (delete)</button>
        </div>
      </div>
    </div>
  );
}
function D({ k, v }: { k: string; v: any }) { return <div className="flex justify-between"><dt className="text-faint">{k}</dt><dd className="text-dim">{String(v)}</dd></div>; }

function CreateMemory({ storeId, onClose, onCreated }: { storeId: string; onClose: () => void; onCreated: () => void }) {
  const [f, setF] = useState({ title: "", content: "", tags: "", sensitivity: "low", source: "manual", confidence: "0.85" });
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState<{ k: "ok" | "err"; t: string } | null>(null);
  async function create() {
    if (!f.content.trim()) return; setBusy(true); setMsg(null);
    try {
      const r = await api.createMemory(storeId, { ...f, confidence: parseFloat(f.confidence), tags: f.tags.split(",").map((t) => t.trim()).filter(Boolean) });
      if (r.governance?.length) setMsg({ k: "ok", t: "Stored. " + r.governance.join(" ") });
      setTimeout(onCreated, r.governance?.length ? 900 : 0);
    } catch (e: any) { setMsg({ k: "err", t: e.status === 401 ? "Sign in to add memory." : e.message }); setBusy(false); }
  }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-line bg-panel2 p-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-3 text-[16px] font-semibold">Add memory</h2>
        <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} placeholder="Title (optional)" className={ci + " mb-2"} />
        <textarea value={f.content} onChange={(e) => setF({ ...f, content: e.target.value })} rows={4} placeholder="What should be remembered?" className={ci + " mb-2"} />
        <div className="mb-2 grid grid-cols-2 gap-2">
          <input value={f.tags} onChange={(e) => setF({ ...f, tags: e.target.value })} placeholder="tags, comma-separated" className={ci} />
          <select value={f.sensitivity} onChange={(e) => setF({ ...f, sensitivity: e.target.value })} className={ci}>{["low", "medium", "high"].map((s) => <option key={s} value={s}>{s} sensitivity</option>)}</select>
        </div>
        {msg && <p className={`mb-2 text-[12px] ${msg.k === "ok" ? "text-ok" : "text-bad"}`}>{msg.t}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
          <button onClick={create} disabled={busy || !f.content.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Saving…" : "Store memory"}</button>
        </div>
      </div>
    </div>
  );
}
const sel = "rounded-lg border border-line bg-panel px-2.5 py-2 text-[12px] text-dim outline-none focus:border-vi/60";
const ci = "w-full rounded-lg border border-line bg-panel px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/60";
