"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import type { Rule } from "../../../../lib/types";
import StoreTabs from "../../../../components/StoreTabs";
import { RULE_TYPES, label } from "../../../../lib/ui";

const RULE_HINT: Record<string, string> = {
  remember: "Store items matching a condition.", forget: "Remove items matching a condition.",
  expiration: "Expire items after an age or date.", redaction: "Detect and block/redact secrets.",
  sensitivity: "Flag or gate sensitive content.", access: "Control who/what can read memory.",
  retrieval: "Bias what gets retrieved.", summarization: "Condense long content.", deduplication: "Merge duplicates.",
};

export default function Rules() {
  const { id } = useParams<{ id: string }>();
  const [storeName, setStoreName] = useState("");
  const [rules, setRules] = useState<Rule[]>([]);
  const [adding, setAdding] = useState(false);
  const load = () => api.rules(id).then(setRules).catch(() => {});
  useEffect(() => { api.store(id).then((s) => setStoreName(s.name)).catch(() => {}); load(); }, [id]);

  async function toggle(r: Rule) { await api.toggleRule(r.id, !r.enabled); load(); }
  async function del(r: Rule) { if (confirm(`Delete rule "${r.name}"?`)) { await api.deleteRule(r.id); load(); } }

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <div className="mt-2 flex items-center justify-between"><h1 className="text-[22px] font-semibold">Memory Rules</h1></div>
      <StoreTabs storeId={id} />
      <p className="mt-4 text-[13px] text-dim">Define what gets remembered, forgotten, expired, redacted, or gated. Rules run on ingest and recall.</p>

      <div className="mt-5 flex justify-end"><button onClick={() => setAdding(true)} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">+ Add rule</button></div>
      <div className="mt-3 space-y-2">
        {rules.map((r) => (
          <div key={r.id} className="flex items-start gap-3 rounded-xl border border-line bg-panel p-3">
            <button onClick={() => toggle(r)} className={`mt-0.5 h-5 w-9 shrink-0 rounded-full transition ${r.enabled ? "bg-ok/70" : "bg-line"}`}>
              <span className={`block h-4 w-4 rounded-full bg-white transition ${r.enabled ? "translate-x-4" : "translate-x-0.5"}`} />
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2"><span className="text-[13.5px] font-medium text-ink">{r.name}</span><span className="rounded-full border border-line px-1.5 py-0.5 text-[10px] text-dim">{label(r.rule_type)}</span></div>
              <p className="mt-0.5 text-[12px] text-dim">{r.description}</p>
              {(Object.keys(r.condition_json || {}).length > 0 || Object.keys(r.action_json || {}).length > 0) && (
                <div className="mt-1 font-mono text-[10px] text-faint">if {JSON.stringify(r.condition_json)} → {JSON.stringify(r.action_json)}</div>
              )}
            </div>
            <button onClick={() => del(r)} className="text-faint hover:text-bad">✕</button>
          </div>
        ))}
        {!rules.length && <div className="rounded-2xl border border-dashed border-line py-14 text-center text-[13px] text-faint">No rules yet. Add one to control remembering and forgetting.</div>}
      </div>
      {adding && <AddRule storeId={id} onClose={() => setAdding(false)} onAdded={() => { setAdding(false); load(); }} />}
    </div>
  );
}

function AddRule({ storeId, onClose, onAdded }: { storeId: string; onClose: () => void; onAdded: () => void }) {
  const [f, setF] = useState({ name: "", rule_type: "remember", description: "" });
  const [json, setJson] = useState('{ "condition": {}, "action": {} }');
  const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  async function add() {
    if (!f.name.trim()) return; setBusy(true); setErr("");
    let cond = {}, act = {};
    try { const p = JSON.parse(json); cond = p.condition || {}; act = p.action || {}; } catch { setErr("Invalid JSON in condition/action."); setBusy(false); return; }
    try { await api.createRule(storeId, { ...f, condition_json: cond, action_json: act }); onAdded(); }
    catch (e: any) { setErr(e.status === 401 ? "Sign in to add rules." : e.message); setBusy(false); }
  }
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-line bg-panel2 p-5" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-3 text-[16px] font-semibold">Add rule</h2>
        <input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Rule name" className={inp + " mb-2"} />
        <select value={f.rule_type} onChange={(e) => setF({ ...f, rule_type: e.target.value })} className={inp + " mb-2"}>{RULE_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
        <p className="mb-2 text-[11px] text-faint">{RULE_HINT[f.rule_type]}</p>
        <input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Description" className={inp + " mb-2"} />
        <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={3} className={inp + " mb-2 font-mono text-[12px]"} />
        {err && <p className="mb-2 text-[12px] text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink">Cancel</button>
          <button onClick={add} disabled={busy || !f.name.trim()} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Adding…" : "Add rule"}</button>
        </div>
      </div>
    </div>
  );
}
const inp = "w-full rounded-lg border border-line bg-panel px-3 py-2 text-[13px] text-ink outline-none focus:border-vi/60";
