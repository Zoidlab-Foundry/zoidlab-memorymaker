"""Nyquest Memory Package — the portable memory-store export format
(memory.package.json) + a minimal YAML serializer (no external deps)."""


def to_package(store: dict, rules: list, entries: list = None, include_entries=False) -> dict:
    gov = store.get("governance") or {}
    ret = store.get("retention_policy") or {}
    chunk = store.get("chunking_strategy") or {}
    pkg = {
        "schema_version": "1.0",
        "package_type": "nyquest_memory",
        "memory_store_id": store.get("slug") or store.get("id"),
        "name": store.get("name"),
        "version": "0.1.0",
        "description": store.get("description", ""),
        "project": store.get("project_id"),
        "memory_type": store.get("memory_type"),
        "storage": {
            "backend": store.get("storage_backend"),
            "embedding_provider": store.get("embedding_provider"),
            "embedding_model": store.get("embedding_model"),
            "dimension": 1536,
        },
        "retrieval": {
            "strategy": store.get("retrieval_strategy", "hybrid"),
            "top_k": ret.get("top_k", 5),
            "similarity_threshold": ret.get("similarity_threshold", 0.72),
            "prefer_recent": ret.get("prefer_recent", True),
            "exclude_expired": ret.get("auto_expire", True),
        },
        "chunking": {"strategy": chunk.get("strategy", "semantic"),
                     "chunk_size": chunk.get("chunk_size", 800),
                     "chunk_overlap": chunk.get("chunk_overlap", 120)},
        "retention": {"default_ttl_days": ret.get("default_ttl_days", 365),
                      "auto_expire": ret.get("auto_expire", True),
                      "allow_manual_forget": ret.get("allow_manual_forget", True)},
        "governance": {
            "risk_level": gov.get("risk_level", "low"), "pii_risk": gov.get("pii_risk", "low"),
            "tenant_isolation": gov.get("tenant_isolation", True),
            "requires_human_approval_for_high_risk": gov.get("requires_human_approval", False),
            "redact_secrets": gov.get("redaction", True), "logs_access": gov.get("logs_access", True),
            "supports_right_to_be_forgotten": gov.get("right_to_be_forgotten", True),
        },
        "rules": [{"name": r["name"], "rule_type": r["rule_type"], "description": r.get("description", ""),
                   "enabled": r["enabled"]} for r in (rules or [])],
        "example_memories": [{"title": e["title"], "content": e["content"], "memory_type": e["memory_type"],
                              "sensitivity": e["sensitivity"], "tags": e.get("tags", [])}
                             for e in (entries or [])[:5]],
    }
    if include_entries and entries:
        pkg["memories"] = [{"title": e["title"], "content": e["content"], "memory_type": e["memory_type"],
                            "source": e.get("source"), "sensitivity": e["sensitivity"], "confidence": e.get("confidence"),
                            "tags": e.get("tags", []), "expires_at": e.get("expires_at")} for e in entries]
    return pkg


def to_yaml(obj, indent=0) -> str:
    pad = "  " * indent
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{k}:")
                lines.append(to_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {_scalar(v)}")
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append(f"{pad}- {_scalar(item)}")
    else:
        return f"{pad}{_scalar(obj)}"
    return "\n".join(l for l in lines if l)


def _scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str) and (":" in v or "#" in v or v == ""):
        return '"' + v.replace('"', '\\"') + '"'
    return str(v)
