"""Shared ZoidLab session — decode the `zb_session` cookie (jose HS256,
BUILDER_SESSION_SECRET). Same cookie every ZoidLab app uses.

The backend is authoritative for access: `require_owner` enforces a signed-in
Nyquest Pro user, so the entitlement holds even if a request reaches the API
without passing the frontend gate.
"""
import os
import sys
import jwt
from fastapi import Request, HTTPException

_DEFAULT = "dev-secret-change-me"
SECRET = os.environ.get("BUILDER_SESSION_SECRET", _DEFAULT)
PRO_TIERS = {"pro", "teams", "team", "enterprise"}

if SECRET == _DEFAULT:
    # Fail loud: with the default secret, session cookies are forgeable.
    print("[memorymaker] WARNING: BUILDER_SESSION_SECRET is unset — using an insecure "
          "default. Sessions are forgeable. Set a real secret before exposing this API.",
          file=sys.stderr)


def session(request: Request):
    tok = request.cookies.get("zb_session")
    if not tok:
        return None
    try:
        return jwt.decode(tok, SECRET, algorithms=["HS256"])
    except Exception:
        return None


def owner_of(request: Request):
    s = session(request)
    return s.get("sub") if s else None


def is_pro(s: dict | None) -> bool:
    return bool(s) and str(s.get("tier") or "").lower() in PRO_TIERS


def require_pro(request: Request):
    """Enforce a signed-in Nyquest Pro user. 401 if unauthenticated, 403 if not Pro.
    Returns the owner (Nyquest user id)."""
    s = session(request)
    if not s or not s.get("sub"):
        raise HTTPException(status_code=401, detail="sign_in_required")
    if not is_pro(s):
        raise HTTPException(status_code=403, detail="pro_required")
    return s.get("sub")
