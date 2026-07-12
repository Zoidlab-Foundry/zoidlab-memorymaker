"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "../../lib/api";
import type { Project } from "../../lib/types";
import { RiskBadge } from "../../components/Badges";

function Projects() {
  const params = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [open, setOpen] = useState(params.get("new") === "1");
  const load = () => api.projects().then(setProjects).catch(() => {});
  useEffect(() => { load(); }, []);
  return (
    <div className="py-8">
      <div className="mb-6 flex items-end justify-between">
        <div><h1 className="text-[22px] font-semibold">Memory Projects</h1><p className="mt-1 text-[13px] text-dim">A project groups memory stores for a business use case.</p></div>
        <button onClick={() => setOpen(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">Create Project</button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`} className="flex flex-col rounded-2xl border border-line bg-panel p-4 hover:border-vi/50 hover:shadow-glow">
            <div className="mb-2 flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-xl text-[22px]" style={{ background: `${p.accent}22` }}>{p.icon}</span>
              <div className="min-w-0"><div className="truncate text-[14px] font-semibold text-ink">{p.name}</div><div className="text-[11px] text-faint">{p.store_count} stores · {p.memory_count} memories</div></div>
            </div>
            <p className="line-clamp-2 text-[12.5px] text-dim">{p.description}</p>
            <div className="mt-auto flex items-center justify-between pt-3"><RiskBadge risk={p.risk_level} /><span className="text-[11px] text-faint">{p.owner_user_id ? "yours" : "example"}</span></div>
          </Link>
        ))}
      </div>
      {open && <NewProject onClose={() => setOpen(false)} onCreated={() => { setOpen(false); load(); }} />}
    </div>
  );
}

function NewProject({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState(""); const [description, setDesc] = useState("");
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  async function create() {
    if (!name.trim()) return; setBusy(true); setErr("");
    try { await api.createProject({ name, description }); onCreated(); }
    catch (e: any) { setErr(e.status === 401 ? "Sign in with your Nyquest account." : e.message); setBusy(false); }
  }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl border border-line bg-panel2 p-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-4 text-[16px] font-semibold">Create memory project</h2>
        <label className="mb-3 block"><span className="mb-1 block text-[12px] text-faint">Name</span><input autoFocus value={name} onChange={(e) => setName(e.target.value)} className={inp} /></label>
        <label className="mb-3 block"><span className="mb-1 block text-[12px] text-faint">Description</span><textarea value={description} onChange={(e) => setDesc(e.target.value)} rows={3} className={inp} /></label>
        {err && <p className="mb-3 text-[12px] text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
          <button onClick={create} disabled={busy || !name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Creating…" : "Create"}</button>
        </div>
      </div>
    </div>
  );
}
const inp = "w-full rounded-xl border border-line bg-panel px-3 py-2.5 text-[13px] text-ink outline-none focus:border-vi/60";
export default function ProjectsPage() { return <Suspense fallback={<div className="py-16 text-center text-faint">Loading…</div>}><Projects /></Suspense>; }
