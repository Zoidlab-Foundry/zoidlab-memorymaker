"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "../../../../lib/api";
import type { Store } from "../../../../lib/types";
import StoreTabs from "../../../../components/StoreTabs";
import { GovBadges } from "../../../../components/Badges";

const TARGETS = [
  { name: "ZoidLab Workflow Builder", desc: "Use this memory store inside a workflow node.", href: "https://builder.zoidlab.ai", live: true },
  { name: "ZoidLab Marketplace Agent", desc: "Declare this store as an agent's required memory.", href: "https://marketplace.zoidlab.ai", live: true },
  { name: "ZoidLab Prompter", desc: "Pull prompt variables from this memory.", href: "https://prompter.zoidlab.ai", live: true },
  { name: "Nyquest AI Concierge", desc: "Persist customer preferences on a concierge.", href: "#", live: false },
  { name: "Nyquest API", desc: "Serve recall via the Nyquest API.", href: "#", live: false },
];

export default function Deploy() {
  const { id } = useParams<{ id: string }>();
  const [s, setS] = useState<Store | null>(null);
  const [pkg, setPkg] = useState<any>(null);
  const [includeEntries, setIncludeEntries] = useState(false);
  useEffect(() => { api.store(id).then(setS).catch(() => {}); }, [id]);
  useEffect(() => { fetch(api.exportJsonUrl(id, includeEntries), { credentials: "include" }).then((r) => r.json()).then(setPkg).catch(() => {}); }, [id, includeEntries]);
  if (!s) return <div className="py-24 text-center text-faint">Loading…</div>;

  return (
    <div className="py-8">
      <Link href={`/stores/${id}`} className="text-[12px] text-faint hover:text-dim">← {s.name}</Link>
      <h1 className="mt-2 text-[22px] font-semibold">Export & Deploy</h1>
      <StoreTabs storeId={id} />
      <p className="mt-4 text-[13px] text-dim">Package this store as a portable <b>Nyquest Memory Package</b> and prepare it for a deployment target.</p>
      <div className="mt-3"><GovBadges badges={s.badges} /></div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_380px]">
        <div>
          <h2 className="mb-3 text-[15px] font-semibold">Deployment targets</h2>
          <div className="space-y-2">
            {TARGETS.map((t) => (
              <div key={t.name} className="flex items-center justify-between rounded-xl border border-line bg-panel p-3">
                <div><div className="text-[13px] font-medium text-ink">{t.name}</div><div className="text-[12px] text-dim">{t.desc}</div></div>
                {t.live ? <a href={t.href} target="_blank" rel="noopener" className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-cy hover:bg-white/5">Open</a> : <span className="rounded-lg border border-line px-3 py-1.5 text-[12px] text-faint">Soon</span>}
              </div>
            ))}
          </div>
          <h2 className="mb-3 mt-6 text-[15px] font-semibold">Export</h2>
          <label className="mb-3 flex items-center gap-2 text-[12px] text-dim"><input type="checkbox" checked={includeEntries} onChange={(e) => setIncludeEntries(e.target.checked)} /> Include full memory entries</label>
          <div className="flex flex-wrap gap-2">
            <a href={api.exportJsonUrl(id, includeEntries)} target="_blank" rel="noopener" className="rounded-lg bg-vi px-4 py-2 text-[13px] font-semibold text-white hover:opacity-90">Download JSON package</a>
            <a href={api.exportYamlUrl(id)} target="_blank" rel="noopener" className="rounded-lg border border-line px-4 py-2 text-[13px] text-ink hover:bg-white/5">Download YAML</a>
          </div>
        </div>
        <div>
          <div className="mb-2 text-[11px] uppercase tracking-wider text-faint">memory.package.json</div>
          <pre className="max-h-[540px] overflow-auto rounded-xl border border-line bg-panel2 p-3 text-[11px] leading-relaxed text-dim">{pkg ? JSON.stringify(pkg, null, 2) : "…"}</pre>
        </div>
      </div>
    </div>
  );
}
