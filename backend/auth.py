"""Shared ZoidLab session — decode the `zb_session` cookie (jose HS256,
BUILDER_SESSION_SECRET). Same cookie every ZoidLab app uses."""
import os
import jwt
from fastapi import Request

SECRET = os.environ.get("BUILDER_SESSION_SECRET", "dev-secret-change-me")


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
