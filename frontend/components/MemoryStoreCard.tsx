import Link from "next/link";
import type { Store } from "../lib/types";
import { RiskBadge, StatusBadge } from "./Badges";
import { label } from "../lib/ui";

export default function MemoryStoreCard({ store }: { store: Store }) {
  return (
    <Link href={`/stores/${store.id}`}
      className="group flex flex-col rounded-2xl border border-line bg-panel p-4 transition hover:border-vi/50 hover:shadow-glow">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-[14px] font-semibold text-ink">{store.name}</h3>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-faint">
            <span className="rounded bg-white/5 px-1.5 py-0.5 text-dim">{label(store.memory_type)}</span>
            <span>· {store.storage_backend === "postgres_pgvector" ? "pgvector" : store.storage_backend}</span>
          </div>
        </div>
        <StatusBadge status={store.status} />
      </div>
      <p className="mb-3 line-clamp-2 text-[12.5px] leading-relaxed text-dim">{store.description}</p>
      <div className="mt-auto flex items-center justify-between border-t border-line pt-3 text-[11px] text-faint">
        <span>{store.memory_count ?? 0} memories</span>
        <RiskBadge risk={store.risk_level} />
        <span>{store.recall_score != null ? `recall ${Math.round(store.recall_score * 100)}%` : "untested"}</span>
      </div>
    </Link>
  );
}
