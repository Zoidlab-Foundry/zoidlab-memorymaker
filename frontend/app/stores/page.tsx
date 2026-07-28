"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";
import type { Store, Project } from "../../lib/types";
import MemoryStoreCard from "../../components/MemoryStoreCard";
import { MEMORY_TYPES, BACKENDS, label } from "../../lib/ui";

const STATUSES = ["all", "draft", "active", "testing", "approved", "deployed", "archived"];
const RISKS = ["all", "low", "medium", "high"];
const SORTS = [["updated", "Recently updated"], ["newest", "Newest"], ["largest", "Largest"], ["recall", "Highest recall"], ["name", "A–Z"]];

function Stores() {
  const [stores, setStores] = useState<Store[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ search: "", project_id: "", memory_type: "all", risk_level: "all", status: "all", storage_backend: "all", sort: "updated" });
  useEffect(() => { api.projects().then(setProjects).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true);
    const t = setTimeout(() => {
      api.stores({ search: f.search, project_id: f.project_id, memory_type: f.memory_type, risk_level: f.risk_level, status: f.status, storage_backend: f.storage_backend, sort: f.sort })
        .then((d) => setStores(d.stores)).catch(() => setStores([])).finally(() => setLoading(false));
    }, 160);
    return () => clearTimeout(t);
  }, [f]);
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));
  return (
    <div className="py-8">
      <div className="mb-6 flex items-end justify-between">
        <div><h1 className="text-[22px] font-semibold">Memory Stores</h1><p className="mt-1 text-[13px] text-dim">The memory library — configured, governed, inspectable.</p></div>
        <Link data-assist="new-store" href="/stores/new" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">Create Store</Link>
      </div>
      <div className="mb-5 flex flex-col gap-3">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input value={f.search} onChange={(e) => set("search", e.target.value)} placeholder="Search stores…" className="flex-1 rounded-xl border border-line bg-panel px-3 py-2.5 text-[13px] text-ink placeholder-faint outline-none focus:border-vi/60" />
          <select value={f.project_id} onChange={(e) => set("project_id", e.target.value)} className={sel}><option value="">All projects</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>
          <select value={f.sort} onChange={(e) => set("sort", e.target.value)} className={sel}>{SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </div>
        <div className="flex flex-wrap gap-2">
          <select value={f.memory_type} onChange={(e) => set("memory_type", e.target.value)} className={sel}><option value="all">All types</option>{MEMORY_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
          <select value={f.storage_backend} onChange={(e) => set("storage_backend", e.target.value)} className={sel}><option value="all">All backends</option>{BACKENDS.map((b) => <option key={b} value={b}>{b}</option>)}</select>
          <select value={f.status} onChange={(e) => set("status", e.target.value)} className={sel}>{STATUSES.map((s) => <option key={s} value={s}>{s === "all" ? "All statuses" : label(s)}</option>)}</select>
          <select value={f.risk_level} onChange={(e) => set("risk_level", e.target.value)} className={sel}>{RISKS.map((r) => <option key={r} value={r}>{r === "all" ? "All risk" : label(r) + " risk"}</option>)}</select>
        </div>
      </div>
      <div className="mb-3 text-[12px] text-faint">{loading ? "Loading…" : `${stores.length} store${stores.length === 1 ? "" : "s"}`}</div>
      {!stores.length && !loading ? <div className="rounded-2xl border border-dashed border-line py-16 text-center text-[13px] text-faint">No stores match. Create one to get started.</div> : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{stores.map((s) => <MemoryStoreCard key={s.id} store={s} />)}</div>
      )}
    </div>
  );
}
const sel = "rounded-xl border border-line bg-panel px-3 py-2.5 text-[13px] text-dim outline-none focus:border-vi/60";
export default function StoresPage() { return <Suspense fallback={<div className="py-16 text-center text-faint">Loading…</div>}><Stores /></Suspense>; }
