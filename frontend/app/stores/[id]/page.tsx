"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "../../../lib/api";
import type { Store } from "../../../lib/types";
import { GovBadges, RiskBadge, StatusBadge } from "../../../components/Badges";
import StoreTabs from "../../../components/StoreTabs";
import { label } from "../../../lib/ui";

export default function StoreDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [s, setS] = useState<Store | null>(null);
  const [busy, setBusy] = useState("");
  const load = () => api.store(id).then(setS).catch(() => setS(null));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);
  if (s === null) return <div className="py-24 text-center text-faint">Loading store…</div>;
  const gov = s.governance || {}; const ret = s.retention_policy || {};

  async function clone() {
    setBusy("clone");
    try { const r = await api.cloneStore(s!.id); router.push(`/stores/${r.store.id}`); }
    catch { setBusy(""); }
  }

  return (
    <div className="py-8">
      <Link href="/stores" className="text-[12px] text-faint hover:text-dim">← Stores</Link>
      <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[24px] font-bold">{s.name}</h1>
            <StatusBadge status={s.status} /><RiskBadge risk={s.risk_level} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-dim">
            <span className="rounded bg-white/5 px-1.5 py-0.5">{label(s.memory_type)}</span>
            <span className="text-line">·</span><span>{s.storage_backend}</span>
            <span className="text-line">·</span><span>{s.memory_count} memories</span>
            {s.recall_score != null && <><span className="text-line">·</span><span>recall {Math.round(s.recall_score * 100)}%</span></>}
            {s.project && <><span className="text-line">·</span><Link href={`/projects/${s.project.id}`} className="text-cy hover:underline">{s.project.name}</Link></>}
          </div>
          <p className="mt-3 max-w-2xl text-[13.5px] leading-relaxed text-dim">{s.description}</p>
          <div className="mt-3"><GovBadges badges={s.badges} /></div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link href={`/stores/${s.id}/memories`} className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">Create memory</Link>
          <Link href={`/stores/${s.id}/ingest`} className="rounded-lg border border-line px-4 py-2 text-[13px] text-ink hover:bg-white/5">Import</Link>
          <Link href={`/stores/${s.id}/recall`} className="rounded-lg border border-line px-4 py-2 text-[13px] text-ink hover:bg-white/5">Recall test</Link>
          <button onClick={clone} disabled={!!busy} className="rounded-lg border border-line px-4 py-2 text-[13px] text-dim hover:text-ink disabled:opacity-50">Clone</button>
        </div>
      </div>

      <StoreTabs storeId={s.id} />

      <div className="grid gap-4 py-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-3">
          <Card title="Configuration">
            <dl className="grid grid-cols-2 gap-y-2 text-[12.5px]">
              <Row k="Memory type" v={label(s.memory_type)} /><Row k="Backend" v={s.storage_backend} />
              <Row k="Embedding" v={`${s.embedding_provider} · ${s.embedding_model}`} /><Row k="Retrieval" v={s.retrieval_strategy} />
              <Row k="Chunking" v={`${(s.chunking_strategy || {}).strategy || "semantic"} · ${(s.chunking_strategy || {}).chunk_size || 800}`} />
              <Row k="TTL (days)" v={ret.default_ttl_days ?? "—"} />
            </dl>
          </Card>
          {s.recall_tests && s.recall_tests.length > 0 && (
            <Card title="Recent recall tests">
              {s.recall_tests.slice(0, 5).map((r: any) => (
                <div key={r.id} className="flex items-center justify-between border-b border-line py-1.5 text-[12px] last:border-0">
                  <span className="truncate text-dim">"{r.query}"</span><span className="text-faint">score {r.score} · {r.latency_ms}ms</span>
                </div>
              ))}
            </Card>
          )}
        </div>
        <div className="space-y-3">
          <Card title="Governance">
            <dl className="space-y-1.5 text-[12px]">
              <Row k="Risk level" v={gov.risk_level} /><Row k="PII risk" v={gov.pii_risk} />
              <Row k="Auto-expire" v={ret.auto_expire ? "yes" : "no"} /><Row k="Redaction" v={gov.redaction ? "on" : "off"} />
              <Row k="Human approval" v={gov.requires_human_approval ? "required" : "no"} />
              <Row k="Tenant isolation" v={gov.tenant_isolation ? "yes" : "no"} /><Row k="Right to forget" v={gov.right_to_be_forgotten ? "yes" : "no"} />
            </dl>
            <Link href={`/stores/${s.id}/governance`} className="mt-3 inline-block text-[12px] text-cy hover:underline">Edit governance →</Link>
          </Card>
          <Card title="Deploy"><Link href={`/stores/${s.id}/deploy`} className="text-[13px] text-cy hover:underline">Export memory package →</Link></Card>
        </div>
      </div>
    </div>
  );
}
function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="rounded-xl border border-line bg-panel p-4"><div className="mb-2 text-[11px] uppercase tracking-wider text-faint">{title}</div>{children}</div>;
}
function Row({ k, v }: { k: string; v: any }) { return <div className="flex items-center justify-between gap-3"><dt className="text-faint">{k}</dt><dd className="truncate text-right text-dim">{String(v)}</dd></div>; }
