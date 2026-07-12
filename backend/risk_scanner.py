"""Detect secrets / sensitive content in memory text and assign a sensitivity level.
Structured so a real Nyquest Policy Engine can replace it later."""
import re

SECRET_KEYWORDS = ["password", "api key", "apikey", "api-key", "token", "secret", "ssn",
                   "social security", "credit card", "bank account", "private key", "attorney-client"]
SENSITIVE_KEYWORDS = ["medical diagnosis", "diagnosis", "salary", "passport", "date of birth",
                      "dob", "home address", "confidential", "license number"]

_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "api_key": re.compile(r"\b(sk-|nq-v1-|ghp_|gho_)[A-Za-z0-9_-]{10,}"),
}


def scan(content: str):
    low = (content or "").lower()
    secrets = [k for k in SECRET_KEYWORDS if k in low]
    sensitive = [k for k in SENSITIVE_KEYWORDS if k in low]
    patterns = [name for name, rx in _PATTERNS.items() if rx.search(content or "")]
    has_secret = bool(secrets or patterns)
    if has_secret:
        level = "high"
    elif sensitive:
        level = "medium"
    else:
        level = "low"
    return {"sensitivity": level, "secrets": secrets, "sensitive": sensitive,
            "patterns": patterns, "has_secret": has_secret}


def redact(content: str) -> str:
    out = content or ""
    for rx in _PATTERNS.values():
        out = rx.sub("[REDACTED]", out)
    return out
