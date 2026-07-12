"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../lib/api";
import type { Stats, Store, Project } from "../lib/types";
import MemoryStoreCard from "../components/MemoryStoreCard";

function Stat({ label, value, sub, tone }: { label: string; value: string | number; sub?: string; tone?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-4">
      <div className={`text-[22px] font-bold ${tone || "text-ink"}`}>{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-faint">{label}</div>
      {sub && <div className="mt-0.5 text-[11px] text-dim">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  useEffect(() => {
    api.stats().then(setStats).catch(() => {});
    api.stores({ sort: "updated" }).then((d) => setStores(d.stores)).catch(() => {});
    api.projects().then(setProjects).catch(() => {});
  }, []);

  return (
    <div className="relative py-10">
      <div className="hero-glow" />
      <section className="relative z-10 mb-8">
        <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 text-[11px] text-dim">
          <span className="h-1.5 w-1.5 rounded-full bg-vi" /> ZoidLab Foundry · Package 04 · AI Memory Studio
        </span>
        <h1 className="text-[34px] font-bold leading-tight sm:text-[40px]">ZoidLab <span className="prism-text">MemoryMaker</span></h1>
        <p className="mt-2 max-w-xl text-[15px] text-dim">Design, govern, and deploy AI memory systems across Nyquest.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/stores/new" className="rounded-xl bg-vi px-5 py-2.5 text-[13px] font-semibold text-white hover:opacity-90">Create Memory Store</Link>
          <Link href="/projects?new=1" className="rounded-xl border border-line px-5 py-2.5 text-[13px] text-ink hover:bg-white/5">Create Project</Link>
          <Link href="/stores" className="rounded-xl border border-line px-5 py-2.5 text-[13px] text-ink hover:bg-white/5">View Memory Library</Link>
        </div>
      </section>

      {stats && (
        <section className="relative z-10 mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
          <Stat label="Stores" value={stats.stores} />
          <Stat label="Memories" value={stats.total} />
          <Stat label="Active" value={stats.active} tone="text-ok" />
          <Stat label="Expired" value={stats.expired} tone="text-warn" />
          <Stat label="High-Risk" value={stats.high_risk} tone={stats.high_risk ? "text-bad" : "text-ink"} />
          <Stat label="Recall Tests" value={stats.recall_tests} />
          <Stat label="Avg Recall" value={stats.avg_recall != null ? `${Math.round(stats.avg_recall * 100)}%` : "—"} />
          <Stat label="Storage" value={`${stats.storage_kb}KB`} />
        </section>
      )}

      {stats && stats.high_risk > 0 && (
        <div className="relative z-10 mb-8 rounded-xl border border-bad/40 bg-bad/10 px-4 py-3 text-[13px] text-bad">
          ⚠ {stats.high_risk} high-risk / sensitive memor{stats.high_risk === 1 ? "y" : "ies"} across your stores — review governance and retention.
        </div>
      )}

      <section className="relative z-10">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-[18px] font-semibold">Active memory stores</h2>
          <Link href="/stores" className="text-[12px] text-cy hover:underline">View all →</Link>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {stores.slice(0, 6).map((s) => <MemoryStoreCard key={s.id} store={s} />)}
        </div>
      </section>

      <section className="relative z-10 mt-10">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-[18px] font-semibold">Memory projects</h2>
          <Link href="/projects" className="text-[12px] text-cy hover:underline">All projects →</Link>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {projects.slice(0, 8).map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="flex items-center gap-3 rounded-xl border border-line bg-panel p-3 hover:border-vi/50">
              <span className="grid h-9 w-9 place-items-center rounded-lg text-[18px]" style={{ background: `${p.accent}22` }}>{p.icon}</span>
              <div className="min-w-0"><div className="truncate text-[13px] font-medium text-ink">{p.name}</div><div className="text-[11px] text-faint">{p.store_count} stores · {p.memory_count} memories</div></div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
