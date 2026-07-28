import type { Metadata } from "next";
import "./globals.css";
import { AssistantPanel } from "@foundry/ui";
import MemoryMakerNav from "../components/MemoryMakerNav";

export const metadata: Metadata = {
  title: "ZoidLab MemoryMaker",
  description: "Design, govern, and deploy AI memory systems.",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-bg text-ink">
        <MemoryMakerNav />
        <AssistantPanel app="MemoryMaker" />
        <main className="mx-auto w-full max-w-[1280px] px-5">{children}</main>
        <footer className="mx-auto mt-20 w-full max-w-[1280px] border-t border-line px-5 py-8 text-[12px] text-faint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>ZoidLab MemoryMaker · Foundry Package 04 · Where AI memory becomes manageable.</span>
            <span className="flex gap-4">
              <a href="https://foundry.zoidlab.ai" className="hover:text-dim">Foundry</a>
              <a href="https://zoidlab.ai" className="hover:text-dim">zoidlab.ai</a>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
