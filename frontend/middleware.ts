import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

// Prompter is a Pro workspace: every page requires a valid shared ZoidLab session
// (zb_session) whose Nyquest tier is Pro or Teams. /api/* is proxied to the backend
// (which enforces its own auth), and the SSO bootstrap routes stay public.
const SECRET = new TextEncoder().encode(process.env.BUILDER_SESSION_SECRET || "dev-secret-change-me");
const PRO_TIERS = (process.env.PRO_TIERS || "pro,teams").split(",").map((t) => t.trim().toLowerCase());
const PUBLIC = ["/enter", "/gate", "/sso", "/api"];

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC.some((p) => pathname.startsWith(p))) return NextResponse.next();

  const cookie = req.cookies.get("zb_session")?.value;
  if (cookie) {
    try {
      const { payload } = await jwtVerify(cookie, SECRET);
      const tier = String((payload as any).tier || "free").toLowerCase();
      if (PRO_TIERS.includes(tier)) return NextResponse.next();
      const url = req.nextUrl.clone(); url.pathname = "/gate"; url.search = "?upgrade=1"; return NextResponse.redirect(url);
    } catch {
      /* invalid/expired */
    }
  }
  const url = req.nextUrl.clone(); url.pathname = "/gate"; url.search = ""; return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|logo.svg).*)"],
};
