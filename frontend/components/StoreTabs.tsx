"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  ["", "Overview"], ["/memories", "Memories"], ["/ingest", "Ingestion"], ["/recall", "Recall Test"],
  ["/rules", "Rules"], ["/governance", "Governance"], ["/analytics", "Analytics"], ["/deploy", "Deploy"],
];

export default function StoreTabs({ storeId }: { storeId: string }) {
  const pathname = usePathname();
  const base = `/stores/${storeId}`;
  return (
    <div className="mt-5 flex flex-wrap gap-1 border-b border-line">
      {TABS.map(([suffix, label]) => {
        const href = base + suffix;
        const active = suffix === "" ? pathname === base : pathname === href;
        return (
          <Link key={label} href={href} className={`px-3 py-2 text-[13px] ${active ? "border-b-2 border-vi text-ink" : "text-dim hover:text-ink"}`}>{label}</Link>
        );
      })}
    </div>
  );
}
