import { SignJWT } from "jose";

// SSO shared across *.zoidlab.ai: verify a Nyquest token, mint the user's own
// relay key, exchange for a short-lived single-use code. Same claim shape as
// Foundry/Builder so the .zoidlab.ai cookie is interchangeable across apps.
const SECRET = new TextEncoder().encode(process.env.BUILDER_SESSION_SECRET || "dev-secret-change-me");
const NYQUEST = (process.env.NYQUEST_API || "https://api.nyquest.ai").replace(/\/$/, "");
const PRO_TIERS = (process.env.PRO_TIERS || "pro,teams").split(",").map((t) => t.trim().toLowerCase());
const KEY_NAME = "ZoidLab Builder";

export type Claims = { sub: string; email: string; name: string; tier: string; rk: string };

async function mintRelayKey(token: string): Promise<string> {
  try {
    const listRes = await fetch(`${NYQUEST}/user/api-keys`, { headers: { Authorization: `Bearer ${token}` } });
    if (listRes.ok) {
      const raw = await listRes.json();
      const keys = Array.isArray(raw) ? raw : raw.keys || raw.data || [];
      for (const k of keys) {
        if (String(k.name || "").startsWith(KEY_NAME)) {
          await fetch(`${NYQUEST}/user/api-keys/${k.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
        }
      }
    }
  } catch {
    /* best-effort */
  }
  const mint = await fetch(`${NYQUEST}/user/api-keys`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ name: KEY_NAME }),
  });
  if (!mint.ok) return "";
  return (await mint.json()).key || "";
}

export async function verifyAndMint(token: string): Promise<{ claims?: Claims; error?: string; status: number }> {
  if (!token) return { error: "missing token", status: 400 };
  let user: any;
  try {
    const r = await fetch(`${NYQUEST}/user/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) return { error: "invalid_nyquest_session", status: 401 };
    user = await r.json();
  } catch {
    return { error: "nyquest_unreachable", status: 502 };
  }
  // Prompter is a Pro workspace — gate at sign-in.
  const tier = String(user.tier || "free").toLowerCase();
  if (!PRO_TIERS.includes(tier)) return { error: "pro_required", status: 403 };
  const rk = await mintRelayKey(token);
  return { claims: { sub: user.id, email: user.email, name: user.name, tier, rk }, status: 200 };
}

export async function issueSession(claims: Claims): Promise<string> {
  return new SignJWT({ ...claims })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(SECRET);
}

const codes = new Map<string, { claims: Claims; exp: number }>();
const TTL_MS = 90_000;

export function putCode(claims: Claims): string {
  const code = (crypto.randomUUID() + crypto.randomUUID()).replace(/-/g, "");
  const now = Date.now();
  for (const [k, v] of codes) if (v.exp < now) codes.delete(k);
  codes.set(code, { claims, exp: now + TTL_MS });
  return code;
}

export function takeCode(code: string): Claims | null {
  const e = codes.get(code);
  if (!e) return null;
  codes.delete(code);
  return e.exp < Date.now() ? null : e.claims;
}
