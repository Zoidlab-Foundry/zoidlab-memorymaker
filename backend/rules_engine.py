"""A small memory rules engine for the MVP. Decides what to do with an incoming
memory (block / redact / flag high-risk / require approval / expire) based on the
store's rules + governance and a risk scan. Structured for a future policy engine."""
import datetime
import risk_scanner


def evaluate_ingest(store: dict, rules: list, content: str, sensitivity_hint: str = None):
    """Returns {allow, content, sensitivity, expires_at, requires_approval, reasons:[...]}."""
    gov = store.get("governance") or {}
    retention = store.get("retention_policy") or {}
    scan = risk_scanner.scan(content)
    sensitivity = sensitivity_hint or scan["sensitivity"]
    reasons = []
    allow = True
    out_content = content

    redaction_on = gov.get("redaction", True) or any(r["rule_type"] == "redaction" and r["enabled"] for r in rules)
    if scan["has_secret"]:
        found = ", ".join(scan["secrets"] + scan["patterns"]) or "pattern"
        if redaction_on:
            out_content, clean = risk_scanner.redact_and_verify(content)
            if out_content != content:
                reasons.append(f"Redacted detected secrets ({found}).")
            if not clean:
                # A secret was detected but could not be fully masked — fail closed.
                allow = False
                reasons.append("Blocked: a detected secret could not be fully redacted; memory was not stored.")
            elif out_content.strip() in ("", "[REDACTED]"):
                allow = False
                reasons.append("Blocked: content was entirely secret material.")
        else:
            allow = False
            reasons.append("Blocked: contains secrets and redaction is disabled.")
        sensitivity = "high"

    # expiration from retention policy / expiration rules
    expires_at = None
    ttl = retention.get("default_ttl_days")
    if retention.get("auto_expire") and ttl:
        expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=int(ttl))).isoformat() + "Z"
        reasons.append(f"Auto-expiry set to {ttl} days.")

    requires_approval = bool(gov.get("requires_human_approval")) and sensitivity == "high"
    if requires_approval:
        reasons.append("High-risk memory — flagged for human approval.")

    return {"allow": allow, "content": out_content, "sensitivity": sensitivity,
            "expires_at": expires_at, "requires_approval": requires_approval, "reasons": reasons,
            "scan": scan}


def scan_store_risk(entries: list):
    """Aggregate risk scan over a store's entries → summary."""
    high = [e for e in entries if e.get("sensitivity") == "high"]
    flagged = []
    for e in entries:
        s = risk_scanner.scan((e.get("content") or "") + " " + (e.get("title") or ""))
        if s["has_secret"]:
            flagged.append({"id": e["id"], "title": e["title"], "found": s["secrets"] + s["patterns"]})
    return {"high_risk_count": len(high), "secrets_found": len(flagged), "flagged": flagged[:20]}
