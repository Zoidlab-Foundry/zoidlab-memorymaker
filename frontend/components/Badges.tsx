import { BADGE_STYLE, RISK_STYLE, STATUS_STYLE, SENS_STYLE, label } from "../lib/ui";

export function Badge({ label: l, className = "" }: { label: string; className?: string }) {
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${className}`}>{l}</span>;
}
export function GovBadges({ badges, max }: { badges?: string[]; max?: number }) {
  if (!badges?.length) return null;
  const shown = max ? badges.slice(0, max) : badges;
  return <div className="flex flex-wrap gap-1.5">{shown.map((b) => <Badge key={b} label={b} className={BADGE_STYLE[b] || "text-dim border-line bg-white/5"} />)}</div>;
}
export function RiskBadge({ risk }: { risk: string }) {
  const r = (risk || "low").toLowerCase();
  return <Badge label={`${label(r)} Risk`} className={RISK_STYLE[r] || RISK_STYLE.low} />;
}
export function StatusBadge({ status }: { status: string }) {
  return <Badge label={label(status)} className={STATUS_STYLE[status] || STATUS_STYLE.draft} />;
}
export function SensBadge({ sensitivity }: { sensitivity: string }) {
  const s = (sensitivity || "low").toLowerCase();
  return <Badge label={`${label(s)}`} className={SENS_STYLE[s] || SENS_STYLE.low} />;
}
