"""Parse ingestion sources (text / json / csv / markdown / website) into memory
entries, each passed through the rules engine (secret redaction, sensitivity, expiry)."""
import re
import csv
import io
import json
import db_pg as db
import rules_engine


def _add(store, rules, item, owner, source, source_name, logs):
    content = item.get("content") or item.get("text") or ""
    if not content.strip():
        return 0
    verdict = rules_engine.evaluate_ingest(store, rules, content, item.get("sensitivity"))
    if not verdict["allow"]:
        logs.append({"skipped": item.get("title") or content[:40], "reason": verdict["reasons"]})
        return 0
    db.create_entry(store["id"], {
        "title": item.get("title") or content[:60],
        "content": verdict["content"], "summary": item.get("summary", ""),
        "source": item.get("source") or source, "source_ref": source_name,
        "memory_type": item.get("memory_type") or store.get("memory_type"),
        "tags": item.get("tags", []), "metadata": {**(item.get("metadata") or {}), "ingest_notes": verdict["reasons"]},
        "sensitivity": verdict["sensitivity"], "confidence": item.get("confidence", 0.8),
        "expires_at": item.get("expires_at") or verdict["expires_at"],
    }, owner, source=source)
    return 1


def ingest_text(store, rules, text, owner, title=None, tags=None, source="manual"):
    created = _add(store, rules, {"title": title, "content": text, "tags": tags or []}, owner, source, "text", logs := [])
    return {"created": created, "failed": 0 if created else 1, "logs": logs, "source_type": "text", "source_name": title or "text"}


def ingest_url_text(store, rules, text, url, owner, title=None):
    """A fetched web page's text -> one memory per paragraph (short nav fragments skipped)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text or "") if len(p.strip()) >= 40]
    created, failed, logs = 0, 0, []
    for para in paras[:200]:
        c = _add(store, rules, {"content": para, "title": title, "source": "website"}, owner, "website", url, logs)
        created += c; failed += (0 if c else 1)
    return {"created": created, "failed": failed, "logs": logs, "source_type": "website", "source_name": url}


def ingest_json(store, rules, payload, owner):
    items = payload if isinstance(payload, list) else payload.get("memories") or payload.get("entries") or [payload]
    created, failed, logs = 0, 0, []
    for it in items:
        if not isinstance(it, dict):
            it = {"content": str(it)}
        c = _add(store, rules, it, owner, "import", "json", logs)
        created += c; failed += (0 if c else 1)
    return {"created": created, "failed": failed, "logs": logs, "source_type": "json", "source_name": "json"}


def ingest_file(store, rules, filename, content_bytes, owner):
    name = filename.lower()
    text = content_bytes.decode("utf-8", errors="replace")
    created, failed, logs = 0, 0, []
    if name.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            item = {"title": row.get("title") or row.get("name"),
                    "content": row.get("content") or row.get("text") or " ".join(str(v) for v in row.values()),
                    "tags": [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
                    "source": row.get("source") or "csv", "sensitivity": row.get("sensitivity")}
            c = _add(store, rules, item, owner, "csv", filename, logs); created += c; failed += (0 if c else 1)
    elif name.endswith((".md", ".markdown")):
        # split on markdown headings; each section becomes a memory
        blocks, cur_title, cur = [], None, []
        for line in text.splitlines():
            if line.startswith("#"):
                if cur_title or cur:
                    blocks.append((cur_title, "\n".join(cur).strip()))
                cur_title = line.lstrip("# ").strip(); cur = []
            else:
                cur.append(line)
        if cur_title or cur:
            blocks.append((cur_title, "\n".join(cur).strip()))
        for t, body in blocks:
            if body:
                c = _add(store, rules, {"title": t, "content": body, "source": "markdown"}, owner, "markdown", filename, logs)
                created += c; failed += (0 if c else 1)
    else:  # plain text — split on blank lines into paragraphs
        for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
            c = _add(store, rules, {"content": para, "source": "text"}, owner, "text", filename, logs)
            created += c; failed += (0 if c else 1)
    return {"created": created, "failed": failed, "logs": logs,
            "source_type": name.split(".")[-1], "source_name": filename}
