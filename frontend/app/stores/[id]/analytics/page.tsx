"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import StoreTabs from "../../../../components/StoreTabs";
import { label } from "../../../../lib/ui";

export default function Analytics() {
  const { id } = useParams<{ id: string }>();
  const [storeName, setStoreName] = useState("");
  const [a, setA] = useState<any>(null);
  useEffect(() => { api.store(id).then((s) => setStoreName(s.name)).catch(() => {}); api.analytics(id).then(setA).catch(() => {}); }, [id]);
  if (!a) return <div className="py-24 text-center text-faint">Loading…</div>;
  const maxGrowth = Math.max(1, ...a.growth.map((g: any) => g.count));

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {storeName || "Store"}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Memory Analytics</h1>
      <StoreTabs storeId={id} />

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Total" value={a.total} />
        <Stat label="Active" value={a.active} tone="text-ok" />
        <Stat label="Expiring soon" value={a.expiring_soon} tone={a.expiring_soon ? "text-warn" : "text-ink"} />
        <Stat label="High-risk" value={a.high_risk} tone={a.high_risk ? "text-bad" : "text-ink"} />
        <Stat label="Recall tests" value={a.recall_tests} />
        <Stat label="Avg recall" value={a.avg_recall != null ? `${Math.round(a.avg_recall * 100)}%` : "—"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Panel title="Memory growth (last 14 days)">
          {a.growth.length ? (
            <div className="flex h-32 items-end gap-1">
              {a.growth.map((g: any) => (
                <div key={g.date} className="group flex flex-1 flex-col items-center justify-end">
                  <div className="w-full rounded-t bg-vi/60" style={{ height: `${(g.count / maxGrowth) * 100}%` }} title={`${g.date}: ${g.count}`} />
                </div>
              ))}
            </div>
          ) : <Empty />}
        </Panel>
        <Panel title="Most accessed">
          {a.most_accessed.length ? a.most_accessed.map((m: any) => <div key={m.id} className="flex justify-between border-b border-line py-1.5 text-[12px] last:border-0"><span className="truncate text-dim">{m.title}</span><span className="text-faint">{m.last_accessed?.slice(0, 10)}</span></div>) : <Empty text="No access yet — run a recall test." />}
        </Panel>
        <Bars title="By source" data={a.by_source} />
        <Bars title="By sensitivity" data={a.by_sensitivity} />
        <Bars title="By type" data={a.by_type} />
      </div>
    </div>
  );
}
function Stat({ label, value, tone }: { label: string; value: any; tone?: string }) {
  return <div className="rounded-2xl border border-line bg-panel p-4"><div className={`text-[22px] font-bold ${tone || "text-ink"}`}>{value}</div><div className="text-[11px] uppercase tracking-wider text-faint">{label}</div></div>;
}
function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="rounded-xl border border-line bg-panel p-4"><div className="mb-3 text-[11px] uppercase tracking-wider text-faint">{title}</div>{children}</div>;
}
function Bars({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <Panel title={title}>
      {entries.length ? entries.map(([k, v]) => (
        <div key={k} className="mb-1.5">
          <div className="flex justify-between text-[11px]"><span className="text-dim">{label(k)}</span><span className="text-faint">{v}</span></div>
          <div className="h-1.5 rounded bg-panel2"><div className="h-1.5 rounded bg-ind/70" style={{ width: `${(v / max) * 100}%` }} /></div>
        </div>
      )) : <Empty />}
    </Panel>
  );
}
function Empty({ text }: { text?: string }) { return <div className="py-6 text-center text-[12px] text-faint">{text || "No data."}</div>; }
