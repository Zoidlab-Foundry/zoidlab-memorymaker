"""Detect secrets / sensitive content in memory text, redact by value, and assign a
sensitivity level. Structured so a real Nyquest Policy Engine can replace it later.

Design guarantee: `has_secret` is true only when a concrete secret VALUE is present
(a known key pattern, or a `label: value` / "label is value" pair). `redact()` masks
those values; `redact_and_verify()` confirms none survived so the caller can fail
closed rather than store a secret in cleartext.
"""
import re

SECRET_KEYWORDS = ["password", "api key", "apikey", "api-key", "token", "secret", "ssn",
                   "social security", "credit card", "bank account", "private key", "attorney-client"]
SENSITIVE_KEYWORDS = ["medical diagnosis", "diagnosis", "salary", "passport", "date of birth",
                      "dob", "home address", "confidential", "license number"]

# Concrete secret VALUE patterns — each full match is replaced with [REDACTED].
_VALUE_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "api_key": re.compile(r"\b(?:sk-|nq-v1-|ghp_|gho_|xox[baprs]-)[A-Za-z0-9_-]{10,}"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "pem_private_key": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----[\s\S]+?-----END (?:[A-Z ]+ )?PRIVATE KEY-----"),
}

# "label: value" / "label is value" — mask the VALUE (group 3), keep the label.
_KV = re.compile(
    r"(?i)\b(password|passphrase|passwd|pwd|api[ _-]?key|apikey|access[ _-]?key|"
    r"secret[ _-]?key|client[ _-]?secret|secret|auth[ _-]?token|bearer[ _-]?token|token|"
    r"private[ _-]?key|bank\s+account(?:\s+number)?|account\s+number|routing\s+number|pin)"
    r"(\s*(?:is|are|=|:|:=|->)\s*)"
    r"(?!\[REDACTED\])([^\s,;]{3,})"
)

# user:password@host inside a connection string — mask just the password (group 2).
_CONNSTR = re.compile(r"(://[^:/\s@]+:)(?!\[REDACTED\])([^@\s/]{3,})(@)")


def scan(content):
    text = content or ""
    low = text.lower()
    patterns = [n for n, rx in _VALUE_PATTERNS.items() if rx.search(text)]
    if _CONNSTR.search(text):
        patterns.append("connection_string_password")
    kv = [m.group(1).lower() for m in _KV.finditer(text)]
    keyword_mentions = [k for k in SECRET_KEYWORDS if k in low]
    sensitive = [k for k in SENSITIVE_KEYWORDS if k in low]
    has_secret = bool(patterns or kv)
    if has_secret:
        level = "high"
    elif keyword_mentions or sensitive:
        level = "medium"
    else:
        level = "low"
    return {"sensitivity": level, "secrets": sorted(set(kv)) or keyword_mentions,
            "sensitive": sensitive, "patterns": patterns, "kv": sorted(set(kv)),
            "keyword_mentions": keyword_mentions, "has_secret": has_secret}


def redact(content: str) -> str:
    out = content or ""
    for rx in _VALUE_PATTERNS.values():
        out = rx.sub("[REDACTED]", out)
    out = _CONNSTR.sub(r"\1[REDACTED]\3", out)
    out = _KV.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", out)
    return out


def redact_and_verify(content: str):
    """Redact, then confirm no concrete secret value survived. Returns (redacted, clean:bool).
    The `(?!\\[REDACTED\\])` guards mean already-masked values don't re-trigger, so a
    residual match is a genuine leak — the caller should refuse to store when clean is False."""
    out = redact(content)
    residual = [n for n, rx in _VALUE_PATTERNS.items() if rx.search(out)]
    if _CONNSTR.search(out):
        residual.append("connection_string_password")
    if _KV.search(out):
        residual.append("keyword_value")
    return out, (len(residual) == 0)
