"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "../lib/useUser";
import HelpGuide from "./HelpGuide";

const LINKS = [
  { href: "/", label: "MemoryMaker" },
  { href: "/projects", label: "Projects" },
  { href: "/stores", label: "Stores" },
];

export default function MemoryMakerNav() {
  const pathname = usePathname();
  const { user, authed } = useUser();
  const is = (h: string) => (h === "/" ? pathname === "/" : pathname.startsWith(h));
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-[1280px] items-center gap-5 px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <img src="/logo.svg" alt="" className="h-6 w-6" />
          <span className="text-[14px] font-semibold tracking-tight">ZoidLab <span className="text-dim font-normal">MemoryMaker</span></span>
          <span className="hidden rounded-full border border-vi/40 bg-vi/10 px-2 py-0.5 text-[9px] font-medium text-vi sm:inline">Foundry 04</span>
        </Link>
        <nav className="hidden items-center gap-1 sm:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href}
              className={`rounded-md px-3 py-1.5 text-[13px] transition ${is(l.href) ? "bg-white/10 text-ink" : "text-dim hover:text-ink hover:bg-white/5"}`}>{l.label}</Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <a
            href="https://foundry.zoidlab.ai"
            className="flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[12px] text-dim transition hover:text-ink hover:bg-white/5"
            title="Back to the Foundry hub"
          >
            <span className="text-vi">◈</span> Foundry
          </a>
          <HelpGuide />
          {authed ? (
            <span className="flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1 text-[12px]">
              <span className="h-1.5 w-1.5 rounded-full bg-ok" />
              {user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "Signed in"}
            </span>
          ) : (
            <a href="https://app.nyquest.ai" className="rounded-lg bg-vi px-3.5 py-1.5 text-[12px] font-semibold text-white hover:opacity-90">Sign in</a>
          )}
        </div>
      </div>
    </header>
  );
}
