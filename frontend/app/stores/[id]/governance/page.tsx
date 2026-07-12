"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import StoreTabs from "../../../../components/StoreTabs";
import { GovBadges } from "../../../../components/Badges";

const TOGGLES: [string, string][] = [
  ["sensitive_data", "Sensitive data allowed"], ["auto_expire", "Auto-expiration enabled"],
  ["redaction", "Redaction enabled"], ["requires_human_approval", "Human approval required"],
  ["tenant_isolation", "Tenant isolation enabled"], ["audit_logging", "Audit logging enabled"],
  ["logs_access", "Log memory access"], ["user_deletion", "User deletion support"],
  ["right_to_be_forgotten", "Right-to-be-forgotten support"],
];

export default function Governance() {
  const { id } = useParams<{ id: string }>();
  const [storeName, setStoreName] = useState("");
  const [gov, setGov] = useState<any>(null);
  const [ret, setRet] = useState<any>({});
  const [badges, setBadges] = useState<string[]>([]);
  const [scan, setScan] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.governance(id).then((d) => { setGov(d.governance || {}); setRet(d.retention_policy || {}); setBadges(d.badges); }).catch(() => {});
  useEffect(() => { api.store(id).then((s) => setStoreName(s.name)).catch(() => {}); load(); }, [id]);
  if (!gov) return <div className="py-24 text-center text-faint">Loading…</div>;

  async function save() {
    setBusy(true); setMsg("");
    try { const d = await api.updateGovernance(id, { governance: gov, retention_policy: ret }); setBadges(d.store.badges || []); setMsg("Saved."); }
    catch (e: any) { setMsg(e.status === 401 ? "Sign in to edit governance." : e.message); } finally { setBusy(false); }
  }
  async function runScan() { setScan(await api.scanRisk(id)); }

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Governance</h1>
      <StoreTabs storeId={id} />
      <div className="mt-4"><GovBadges badges={badges} /></div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-panel p-4">
          <div className="mb-3 text-[11px] uppercase tracking-wider text-faint">Risk & PII</div>
          <div className="grid grid-cols-2 gap-3">
            <label><span className="mb-1 block text-[11px] text-faint">Risk level</span><select value={gov.risk_level || "low"} onChange={(e) => setGov({ ...gov, risk_level: e.target.value })} className={inp}>{["low", "medium", "high"].map((r) => <option key={r}>{r}</option>)}</select></label>
            <label><span className="mb-1 block text-[11px] text-faint">PII risk</span><select value={gov.pii_risk || "low"} onChange={(e) => setGov({ ...gov, pii_risk: e.target.value })} className={inp}>{["low", "medium", "high"].map((r) => <option key={r}>{r}</option>)}</select></label>
            <label><span className="mb-1 block text-[11px] text-faint">Retention (TTL days)</span><input type="number" value={ret.default_ttl_days ?? 365} onChange={(e) => setRet({ ...ret, default_ttl_days: +e.target.value })} className={inp} /></label>
          </div>
        </div>
        <div className="rounded-xl border border-line bg-panel p-4">
          <div className="mb-3 text-[11px] uppercase tracking-wider text-faint">Controls</div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {TOGGLES.map(([k, l]) => (
              <label key={k} className="flex items-center gap-2 text-[12.5px] text-dim">
                <input type="checkbox" checked={!!(k === "auto_expire" ? ret.auto_expire : gov[k])} onChange={(e) => k === "auto_expire" ? setRet({ ...ret, auto_expire: e.target.checked }) : setGov({ ...gov, [k]: e.target.checked })} /> {l}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button onClick={save} disabled={busy} className="rounded-lg bg-vi px-5 py-2.5 text-[13px] font-semibold text-white hover:opacity-90 disabled:opacity-50">{busy ? "Saving…" : "Save governance"}</button>
        <button onClick={runScan} className="rounded-lg border border-line px-5 py-2.5 text-[13px] text-ink hover:bg-white/5">Run risk scan</button>
        {msg && <span className="text-[12px] text-dim">{msg}</span>}
      </div>

      {scan && (
        <div className={`mt-4 rounded-xl border p-4 ${scan.secrets_found ? "border-bad/40 bg-bad/10" : "border-ok/40 bg-ok/10"}`}>
          <div className="text-[13px] font-medium">{scan.secrets_found ? "⚠ Risk scan flagged content" : "✓ Risk scan clean"}</div>
          <div className="mt-1 text-[12px] text-dim">{scan.high_risk_count} high-risk memories · {scan.secrets_found} with detected secrets</div>
          {scan.flagged?.map((fl: any) => <div key={fl.id} className="mt-1 text-[11px] text-bad">• {fl.title} — found: {fl.found.join(", ")}</div>)}
        </div>
      )}
    </div>
  );
}
const inp = "w-full rounded-lg border border-line bg-panel2 px-2.5 py-2 text-[12.5px] text-ink outline-none focus:border-vi/60";
