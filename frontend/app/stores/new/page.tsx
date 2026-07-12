"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "../../../lib/api";
import type { Project } from "../../../lib/types";
import { MEMORY_TYPES, BACKENDS, RETRIEVAL_MODES, label } from "../../../lib/ui";

function NewStore() {
  const router = useRouter();
  const params = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [f, setF] = useState({
    name: "", description: "", project_id: params.get("project") || "", memory_type: "long_term",
    storage_backend: "postgres_pgvector", retrieval_strategy: "hybrid", risk_level: "low",
  });
  const [gov, setGov] = useState({ pii_risk: "low", requires_human_approval: false, redaction: true, tenant_isolation: true, right_to_be_forgotten: true });
  const [ttl, setTtl] = useState(365);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  useEffect(() => { api.projects().then(setProjects).catch(() => {}); }, []);
  const set = (k: string, v: any) => setF((s) => ({ ...s, [k]: v }));

  async function create() {
    if (!f.name.trim()) { setErr("Name is required."); return; }
    setBusy(true); setErr("");
    try {
      const r = await api.createStore({
        ...f, project_id: f.project_id || undefined,
        governance: { ...gov, risk_level: f.risk_level, sensitive_data: f.risk_level !== "low" },
        retention_policy: { default_ttl_days: ttl, auto_expire: true, allow_manual_forget: true, prefer_recent: true, top_k: 5, similarity_threshold: 0.72 },
      });
      router.push(`/stores/${r.store.id}`);
    } catch (e: any) { setErr(e.status === 401 ? "Sign in with your Nyquest account to create a store." : e.message); setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="text-[22px] font-semibold">Create memory store</h1>
      <p className="mt-1 text-[13px] text-dim">Define what kind of memory is stored, how it's retrieved, and how it's governed.</p>
      <div className="mt-6 space-y-4">
        <Field label="Name"><input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="Customer Preference Memory" className={inp} /></Field>
        <Field label="Description"><textarea value={f.description} onChange={(e) => set("description", e.target.value)} rows={2} className={inp} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Project"><select value={f.project_id} onChange={(e) => set("project_id", e.target.value)} className={inp}><option value="">None</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
          <Field label="Memory type"><select value={f.memory_type} onChange={(e) => set("memory_type", e.target.value)} className={inp}>{MEMORY_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select></Field>
          <Field label="Storage backend"><select value={f.storage_backend} onChange={(e) => set("storage_backend", e.target.value)} className={inp}>{BACKENDS.map((b) => <option key={b} value={b}>{b}</option>)}</select></Field>
          <Field label="Retrieval strategy"><select value={f.retrieval_strategy} onChange={(e) => set("retrieval_strategy", e.target.value)} className={inp}>{RETRIEVAL_MODES.map((m) => <option key={m} value={m}>{m}</option>)}</select></Field>
          <Field label="Risk level"><select value={f.risk_level} onChange={(e) => set("risk_level", e.target.value)} className={inp}>{["low", "medium", "high"].map((r) => <option key={r}>{r}</option>)}</select></Field>
          <Field label="Retention (TTL days)"><input type="number" value={ttl} onChange={(e) => setTtl(+e.target.value)} className={inp} /></Field>
        </div>
        <div className="rounded-xl border border-line bg-panel2 p-4">
          <div className="mb-2 text-[11px] uppercase tracking-wider text-faint">Governance</div>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={gov.redaction} onChange={(e) => setGov({ ...gov, redaction: e.target.checked })} /> Redact secrets on ingest</label>
            <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={gov.requires_human_approval} onChange={(e) => setGov({ ...gov, requires_human_approval: e.target.checked })} /> Require approval for high-risk</label>
            <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={gov.tenant_isolation} onChange={(e) => setGov({ ...gov, tenant_isolation: e.target.checked })} /> Tenant isolation</label>
            <label className="flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={gov.right_to_be_forgotten} onChange={(e) => setGov({ ...gov, right_to_be_forgotten: e.target.checked })} /> Right to be forgotten</label>
          </div>
        </div>
        {err && <p className="text-[12px] text-bad">{err}</p>}
        <div className="flex gap-3">
          <button onClick={() => history.back()} className="rounded-lg border border-line px-5 py-2.5 text-[13px] text-dim hover:text-ink">Cancel</button>
          <button onClick={create} disabled={busy} className="rounded-lg bg-vi px-5 py-2.5 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Creating…" : "Create store"}</button>
        </div>
      </div>
    </div>
  );
}
const inp = "w-full rounded-xl border border-line bg-panel px-3 py-2.5 text-[13px] text-ink outline-none focus:border-vi/60";
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-[12px] text-faint">{label}</span>{children}</label>; }
export default function NewStorePage() { return <Suspense fallback={<div className="py-16 text-center text-faint">Loading…</div>}><NewStore /></Suspense>; }
