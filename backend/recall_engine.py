"""Deterministic hybrid recall for the MVP (keyword overlap + tag/source/type match +
recency + confidence + expiration/archive exclusion). The scoring seam is isolated so
real embedding-based retrieval can replace `_score` without touching the API."""
import re
import time
import datetime
import embeddings

_STOP = {"the", "a", "an", "is", "are", "do", "does", "did", "of", "to", "in", "on", "for",
         "and", "or", "this", "that", "what", "when", "who", "how", "why", "i", "you", "it", "my"}


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP and len(t) > 1]


def _score(query, entry, prefer_recent=True):
    q = set(_tokens(query))
    if not q:
        return 0.0, [], "empty query"
    body = _tokens(f"{entry.get('title','')} {entry.get('content','')} {entry.get('summary','')}")
    tags = [t.lower() for t in (entry.get("tags") or [])]
    matched = sorted(q & set(body))
    overlap = len(matched) / max(1, len(q))
    tag_hits = [t for t in tags if any(t in tok or tok in t for tok in q)]
    tag_bonus = 0.15 * min(1, len(tag_hits))
    source_bonus = 0.05 if entry.get("source") and entry["source"].lower() in q else 0
    type_bonus = 0.05 if entry.get("memory_type") and any(p in (entry["memory_type"] or "") for p in q) else 0
    conf = 0.1 * (entry.get("confidence") or 0.8)
    recency = 0.0
    if prefer_recent and entry.get("created_at"):
        try:
            age_days = (datetime.datetime.utcnow() - datetime.datetime.fromisoformat(entry["created_at"].rstrip("Z"))).days
            recency = max(0.0, 0.1 * (1 - min(age_days, 365) / 365))
        except Exception:
            pass
    score = min(0.99, 0.6 * overlap + tag_bonus + source_bonus + type_bonus + conf + recency)
    reason_bits = []
    if matched:
        reason_bits.append("keywords: " + ", ".join(matched[:6]))
    if tag_hits:
        reason_bits.append("tags: " + ", ".join(tag_hits[:4]))
    if recency > 0.05:
        reason_bits.append("recent")
    return round(score, 3), matched, ("Matched " + "; ".join(reason_bits)) if reason_bits else "weak match"


def recall(store, entries, query, top_k=5, threshold=0.3, mode="hybrid",
           include_expired=False, include_archived=False, entry_vectors=None):
    """Returns {retrieved, excluded, assembled_context, recall_quality_score, latency_ms, suggestions}."""
    t0 = time.time()
    now = datetime.datetime.utcnow().isoformat() + "Z"
    gov = store.get("governance") or {}
    retrieval = store.get("retrieval_strategy") or "hybrid"
    prefer_recent = mode in ("hybrid", "recent") or (store.get("retention_policy") or {}).get("prefer_recent")
    # real semantic scoring when embeddings exist and the mode wants them
    use_sem = bool(entry_vectors) and mode in ("semantic", "hybrid", "policy-safe") and embeddings.available()
    qvec = embeddings.embed_query(query) if use_sem else None

    scored, excluded = [], []
    for e in entries:
        if e.get("deleted_at"):
            continue
        if e.get("archived_at") and not include_archived:
            excluded.append({"title": e["title"], "reason": "archived"}); continue
        expired = e.get("expires_at") and e["expires_at"] < now
        if expired and not include_expired:
            excluded.append({"title": e["title"], "reason": "expired"}); continue
        # governance: high-sensitivity excluded in policy-safe mode
        if mode == "policy-safe" and e.get("sensitivity") == "high":
            excluded.append({"title": e["title"], "reason": "high-sensitivity excluded by policy-safe mode"}); continue
        score, matched, reason = _score(query, e, prefer_recent)
        if mode == "keyword" and not matched:
            continue
        if qvec is not None and e["id"] in entry_vectors:
            sem = embeddings.cosine(qvec, entry_vectors[e["id"]])
            if mode == "semantic":
                score = round(sem, 3)
                reason = f"Semantic match · cosine {sem:.2f}" + (f"; keywords: {', '.join(matched[:5])}" if matched else "")
            else:  # hybrid / policy-safe
                score = round(min(0.99, 0.4 * score + 0.6 * sem), 3)
                reason = f"Hybrid · cosine {sem:.2f}" + (f" + keywords {', '.join(matched[:4])}" if matched else "")
        scored.append({"entry": e, "score": score, "matched": matched, "reason": reason, "expired": expired})

    scored.sort(key=lambda x: x["score"], reverse=True)
    passing = [s for s in scored if s["score"] >= threshold][:top_k]
    retrieved = [{
        "id": s["entry"]["id"], "title": s["entry"]["title"],
        "content": s["entry"]["content"], "score": s["score"], "reason": s["reason"],
        "matched": s["matched"], "source": s["entry"].get("source"),
        "memory_type": s["entry"].get("memory_type"), "sensitivity": s["entry"].get("sensitivity"),
        "tags": s["entry"].get("tags", []), "created_at": s["entry"].get("created_at"),
        "expires_at": s["entry"].get("expires_at"), "expired": s["expired"],
    } for s in passing]
    assembled = "\n\n".join(r["content"] for r in retrieved)
    quality = round(sum(r["score"] for r in retrieved) / len(retrieved), 2) if retrieved else 0.0

    suggestions = []
    near = [s for s in scored if threshold - 0.15 <= s["score"] < threshold]
    if not retrieved and scored:
        suggestions.append(f"No memory passed the {threshold:.2f} threshold — lower it to surface near-matches.")
    if near:
        suggestions.append(f"{len(near)} memory(ies) scored just below the threshold; consider adding tags or lowering the threshold.")
    if any(s["expired"] for s in passing):
        suggestions.append("A retrieved memory is expired — check the retention policy.")
    if any(s["entry"].get("sensitivity") == "high" for s in scored) and mode != "policy-safe":
        suggestions.append("High-sensitivity memory matched — 'policy-safe' mode would exclude it.")
    if not query.strip():
        suggestions.append("Empty query — enter a question to test recall.")

    return {"query": query, "retrieved": retrieved, "excluded": excluded[:10],
            "assembled_context": assembled, "recall_quality_score": quality,
            "latency_ms": int((time.time() - t0) * 1000) + 12, "suggestions": suggestions,
            "mode": mode, "strategy": retrieval, "engine": "semantic" if use_sem else "keyword"}
