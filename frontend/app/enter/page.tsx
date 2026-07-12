"use client";
import { useEffect, useState } from "react";

// Handoff landing: an opener (Nyquest app / Foundry) opens this page, then sets
// our URL fragment to #c=<code>. A fragment change doesn't reload, so we exchange
// on load AND on hashchange, staying in "working" until a code arrives.
export default function Enter() {
  const [state, setState] = useState<"working" | "failed">("working");

  useEffect(() => {
    let done = false;
    const exchange = (): boolean => {
      if (done) return true;
      const hash = new URLSearchParams(location.hash.replace(/^#/, ""));
      const search = new URLSearchParams(location.search);
      const code = hash.get("c") || search.get("c");
      const token = hash.get("t") || search.get("t");
      const body = code ? { code } : token ? { token } : null;
      if (!body) return false;
      done = true;
      fetch("/sso/session", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      })
        .then((r) => {
          if (r.ok) { history.replaceState(null, "", "/"); location.href = "/"; }
          else setState("failed");
        })
        .catch(() => setState("failed"));
      return true;
    };
    if (exchange()) return;
    const onHash = () => exchange();
    window.addEventListener("hashchange", onHash);
    const timer = setTimeout(() => { if (!done) setState("failed"); }, 20000);
    return () => { window.removeEventListener("hashchange", onHash); clearTimeout(timer); };
  }, []);

  return (
    <div className="flex h-[70vh] w-full items-center justify-center text-center">
      <div className="max-w-sm px-6">
        {state === "working" ? (
          <>
            <div className="mx-auto mb-4 h-6 w-6 animate-spin rounded-full border-2 border-line border-t-vi" />
            <p className="text-[13px] text-dim">Signing you in with Nyquest…</p>
          </>
        ) : (
          <>
            <p className="mb-2 text-[15px] font-semibold text-ink">Couldn’t sign you in</p>
            <p className="text-[13px] leading-relaxed text-dim">
              Open ZoidLab from your Nyquest app to get a fresh link, or <a className="text-cy" href="https://app.nyquest.ai">sign in to Nyquest</a> first.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
