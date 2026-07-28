"""ZoidLab MemoryMaker API — AI memory control plane. Pro-gated at the frontend;
the backend requires a signed-in user for writes. Owner = Nyquest user id.
Spine: project → store → ingest → inspect → recall → rules → governance → export.
"""
import re
import socket
import ipaddress
from urllib.parse import urlparse, urljoin
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Any, List

import db_pg as db
import recall_engine
import rules_engine
import risk_scanner
import ingestion
import exporter
import seed_memory
from auth import owner_of, session, require_pro


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    n = seed_memory.run()
    if n:
        print(f"[memorymaker] seeded {n} stores + projects")
    yield


app = FastAPI(title="ZoidLab MemoryMaker API", lifespan=lifespan)

from foundry_common import assistant
from assistant_manifest import MANIFEST
app.include_router(assistant.make_router(MANIFEST))


def require_owner(request: Request):
    """Every mutation requires a signed-in Nyquest Pro user (backend-enforced)."""
    o = require_pro(request)
    s = session(request)
    db.upsert_user(o, s.get("email"), s.get("name"))
    return o


def owned_store_or_404(sid: str, request: Request):
    """Fetch a store the caller is allowed to see (own or shared) or 404. Closes IDOR
    on the by-id read endpoints that previously queried without a visibility scope."""
    s = db.get_store(sid, owner_of(request))
    if not s:
        raise HTTPException(404, "not_found")
    return s


def store_badges(store: dict) -> List[str]:
    gov = store.get("governance") or {}
    risk = (gov.get("risk_level") or store.get("risk_level") or "low").lower()
    out = [{"low": "Low Risk", "medium": "Medium Risk", "high": "High Risk"}.get(risk, "Low Risk")]
    if str(gov.get("pii_risk", "")).lower() in ("medium", "high"):
        out.append("PII Risk")
    if gov.get("requires_human_approval"):
        out.append("Requires Approval")
    if gov.get("auto_expire", (store.get("retention_policy") or {}).get("auto_expire")):
        out.append("Auto Expiration")
    if gov.get("tenant_isolation"):
        out.append("Tenant Isolated")
    if gov.get("logs_access"):
        out.append("Logs Access")
    if gov.get("right_to_be_forgotten"):
        out.append("Forgettable")
    return out


def entry_badges(e: dict) -> List[str]:
    out = []
    s = (e.get("sensitivity") or "low").lower()
    if s == "high":
        out.append("PII Risk")
    elif s == "medium":
        out.append("Sensitive")
    if e.get("expires_at"):
        import datetime
        try:
            days = (datetime.datetime.fromisoformat(e["expires_at"].rstrip("Z")) - datetime.datetime.utcnow()).days
            if days <= 30:
                out.append("Expiring Soon")
        except Exception:
            pass
    if e.get("archived_at"):
        out.append("Archived")
    if e.get("source") in ("csv", "markdown", "json", "import", "document"):
        out.append("External Source")
    out.append("Tenant Scoped" if e.get("user_scope_id") else "Global Memory")
    return out


def deco_store(s):
    if s:
        s["badges"] = store_badges(s)
    return s


# ---- meta ---------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "stores": len(db.list_stores())}


@app.get("/api/whoami")
def whoami(request: Request):
    s = session(request)
    if not s:
        return {"authenticated": False}
    return {"authenticated": True, "email": s.get("email"), "name": s.get("name"),
            "tier": s.get("tier"), "admin": db.is_admin(s.get("sub"))}


@app.get("/api/stats")
def stats(request: Request):
    return db.dashboard_stats(owner_of(request))


MEMORY_TYPES = ["conversation", "user_profile", "customer_profile", "project", "organization",
                "document", "tool", "agent", "session", "long_term", "episodic", "semantic", "procedural"]
BACKENDS = ["mock", "postgres_pgvector", "chroma", "qdrant", "pinecone", "weaviate", "redis_vector", "milvus"]


@app.get("/api/meta")
def meta():
    return {"memory_types": MEMORY_TYPES, "backends": BACKENDS,
            "retrieval_modes": ["semantic", "keyword", "hybrid", "recent", "user", "project", "policy-safe"],
            "rule_types": ["remember", "forget", "expiration", "redaction", "sensitivity", "access", "retrieval", "summarization", "deduplication"]}


# ---- projects -----------------------------------------------------------
class ProjectBody(BaseModel):
    name: str
    description: Optional[str] = ""
    status: Optional[str] = "active"
    risk_level: Optional[str] = "low"
    icon: Optional[str] = "◆"
    accent: Optional[str] = "#7c5cfc"


@app.get("/api/projects")
def projects(request: Request):
    return {"projects": db.list_projects(owner_of(request))}


@app.post("/api/projects")
def create_project(body: ProjectBody, request: Request):
    o = require_owner(request)
    return {"ok": True, "project": db.create_project(body.model_dump(), o)}


@app.get("/api/projects/{pid}")
def get_project(pid: str, request: Request):
    p = db.get_project(pid, owner_of(request))
    if not p:
        raise HTTPException(404, "not_found")
    p["stores"] = [deco_store(s) for s in db.list_stores(owner_of(request), project_id=pid)]
    return p


@app.put("/api/projects/{pid}")
def update_project(pid: str, body: ProjectBody, request: Request):
    o = require_owner(request)
    p = db.update_project(pid, body.model_dump(), o)
    if not p:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "project": p}


@app.delete("/api/projects/{pid}")
def archive_project(pid: str, request: Request):
    o = require_owner(request)
    if not db.update_project(pid, {"status": "archived"}, o):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


# ---- stores -------------------------------------------------------------
class StoreBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_id: Optional[str] = None
    memory_type: Optional[str] = None
    storage_backend: Optional[str] = None
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    retrieval_strategy: Optional[str] = None
    chunking_strategy: Optional[dict] = None
    retention_policy: Optional[dict] = None
    access_scope: Optional[dict] = None
    governance: Optional[dict] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None


@app.get("/api/stores")
def stores(request: Request, search: Optional[str] = None, project_id: Optional[str] = None,
           memory_type: Optional[str] = None, risk_level: Optional[str] = None, status: Optional[str] = None,
           storage_backend: Optional[str] = None, sort: str = "updated"):
    items = db.list_stores(owner_of(request), search=search, project_id=project_id, memory_type=memory_type,
                           risk=risk_level, status=status, backend=storage_backend, sort=sort)
    for s in items:
        s["badges"] = store_badges(s)
    return {"stores": items, "count": len(items)}


@app.post("/api/stores")
def create_store(body: StoreBody, request: Request):
    o = require_owner(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data.get("name"):
        raise HTTPException(400, "name_required")
    return {"ok": True, "store": deco_store(db.create_store(data, o))}


@app.get("/api/stores/{sid}")
def get_store(sid: str, request: Request):
    s = db.get_store(sid, owner_of(request))
    if not s:
        raise HTTPException(404, "not_found")
    s["project"] = db.get_project(s["project_id"], owner_of(request)) if s.get("project_id") else None
    s["rules"] = db.list_rules(sid)
    s["recall_tests"] = db.list_recall_tests(sid, limit=8)
    return deco_store(s)


@app.put("/api/stores/{sid}")
def update_store(sid: str, body: StoreBody, request: Request):
    o = require_owner(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    s = db.update_store(sid, data, o)
    if not s:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "store": deco_store(s)}


@app.delete("/api/stores/{sid}")
def archive_store(sid: str, request: Request):
    o = require_owner(request)
    if not db.set_store_status(sid, "archived", o, require_owner=True):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


@app.post("/api/stores/{sid}/clone")
def clone_store(sid: str, request: Request):
    o = require_owner(request)
    s = db.clone_store(sid, o)
    if not s:
        raise HTTPException(404, "not_found")
    return {"ok": True, "store": deco_store(s)}


# ---- entries ------------------------------------------------------------
class EntryBody(BaseModel):
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    source: Optional[str] = "manual"
    memory_type: Optional[str] = None
    tags: Optional[list] = None
    metadata: Optional[dict] = None
    sensitivity: Optional[str] = None
    confidence: Optional[float] = None
    expires_at: Optional[str] = None
    user_scope_id: Optional[str] = None


@app.get("/api/stores/{sid}/memories")
def list_memories(sid: str, request: Request, search: Optional[str] = None, source: Optional[str] = None,
                  memory_type: Optional[str] = None, sensitivity: Optional[str] = None, tag: Optional[str] = None,
                  include_archived: bool = False, include_expired: bool = True, sort: str = "newest"):
    if not db.get_store(sid, owner_of(request)):
        raise HTTPException(404, "not_found")
    items = db.list_entries(sid, search=search, source=source, memory_type=memory_type, sensitivity=sensitivity,
                            tag=tag, include_archived=include_archived, include_expired=include_expired, sort=sort)
    for e in items:
        e["badges"] = entry_badges(e)
    return {"memories": items, "count": len(items)}


@app.post("/api/stores/{sid}/memories")
def create_memory(sid: str, body: EntryBody, request: Request):
    o = require_owner(request)
    store = owned_store_or_404(sid, request)
    # run through the rules engine (redaction / sensitivity / expiry)
    verdict = rules_engine.evaluate_ingest(store, db.list_rules(sid), body.content, body.sensitivity)
    if not verdict["allow"]:
        return JSONResponse({"ok": False, "blocked": True, "reasons": verdict["reasons"]}, status_code=400)
    data = body.model_dump()
    data["content"] = verdict["content"]
    data["sensitivity"] = verdict["sensitivity"]
    data["expires_at"] = data.get("expires_at") or verdict["expires_at"]
    e = db.create_entry(sid, data, o, source=body.source or "manual")
    e["badges"] = entry_badges(e)
    return {"ok": True, "memory": e, "governance": verdict["reasons"]}


@app.get("/api/memories/{mid}")
def get_memory(mid: str, request: Request):
    e = db.get_entry_visible(mid, owner_of(request))
    if not e:
        raise HTTPException(404, "not_found")
    db.touch_entry(mid)
    e["badges"] = entry_badges(e)
    return e


@app.put("/api/memories/{mid}")
def update_memory(mid: str, body: EntryBody, request: Request):
    o = require_owner(request)
    e = db.update_entry(mid, {k: v for k, v in body.model_dump().items() if v is not None}, o)
    if not e:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "memory": e}


@app.post("/api/memories/{mid}/archive")
def archive_memory(mid: str, request: Request):
    if not db.entry_action(mid, "archive", require_owner(request)):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


@app.post("/api/memories/{mid}/restore")
def restore_memory(mid: str, request: Request):
    if not db.entry_action(mid, "restore", require_owner(request)):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


@app.delete("/api/memories/{mid}")
def delete_memory(mid: str, request: Request):
    if not db.entry_action(mid, "delete", require_owner(request)):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True}


@app.post("/api/memories/{mid}/forget")
def forget_memory(mid: str, request: Request):
    if not db.entry_action(mid, "forget", require_owner(request)):
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "forgotten": True}


# ---- ingestion ----------------------------------------------------------
class TextIngest(BaseModel):
    text: str
    title: Optional[str] = None
    tags: Optional[list] = None
    source: Optional[str] = "manual"


def _run_ingest(sid, owner, fn, *args):
    store = db.get_store(sid, owner)  # visibility-scoped: no injecting into another tenant's store
    if not store:
        raise HTTPException(404, "not_found")
    res = fn(store, db.list_rules(sid), *args, owner)
    job = db.log_ingestion(sid, res["source_type"], res["source_name"], res["created"], res["failed"], res["logs"], owner)
    return {"ok": True, "job_id": job, **res}


@app.post("/api/stores/{sid}/ingest/text")
def ingest_text(sid: str, body: TextIngest, request: Request):
    o = require_owner(request)
    return _run_ingest(sid, o, lambda st, ru, owner: ingestion.ingest_text(st, ru, body.text, owner, body.title, body.tags, body.source or "manual"))


@app.post("/api/stores/{sid}/ingest/json")
async def ingest_json(sid: str, request: Request):
    o = require_owner(request)
    payload = await request.json()
    return _run_ingest(sid, o, lambda st, ru, owner: ingestion.ingest_json(st, ru, payload, owner))


@app.post("/api/stores/{sid}/ingest/file")
async def ingest_file(sid: str, request: Request, file: UploadFile = File(...)):
    o = require_owner(request)
    content = await file.read()
    return _run_ingest(sid, o, lambda st, ru, owner: ingestion.ingest_file(st, ru, file.filename, content, owner))


# --- website ingestion (SSRF-guarded fetch, redirects re-checked) --------
def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        try:
            addr = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
                or addr.is_multicast or addr.is_unspecified):
            return False
    return bool(infos)


def _guard_url(url: str):
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"blocked scheme '{p.scheme or 'none'}'")
    if not p.hostname or not _host_is_public(p.hostname):
        raise ValueError(f"blocked internal/non-public host '{p.hostname}'")


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style|nav|footer|header).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


async def _fetch_page(url: str, max_hops: int = 4):
    async with httpx.AsyncClient(timeout=30, follow_redirects=False,
                                 headers={"User-Agent": "ZoidLab-MemoryMaker/1.0 (+https://memorymaker.zoidlab.ai)"}) as c:
        for _ in range(max_hops):
            _guard_url(url)
            r = await c.get(url)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = urljoin(url, r.headers["location"])
                continue
            r.raise_for_status()
            m = re.search(r"(?is)<title[^>]*>(.*?)</title>", r.text)
            title = (re.sub(r"\s+", " ", m.group(1)).strip() if m else url)[:120]
            return title or url, _html_to_text(r.text)
    raise ValueError("too many redirects")


class UrlIngest(BaseModel):
    url: str


@app.post("/api/stores/{sid}/ingest/url")
async def ingest_url(sid: str, body: UrlIngest, request: Request):
    o = require_owner(request)
    owned_store_or_404(sid, request)
    try:
        title, text = await _fetch_page(body.url)
    except Exception as e:
        raise HTTPException(400, f"could not read that URL: {str(e)[:140]}")
    if not (text or "").strip():
        raise HTTPException(400, "no extractable text at that URL")
    return _run_ingest(sid, o, lambda st, ru, owner: ingestion.ingest_url_text(st, ru, text, body.url, owner, title))


@app.get("/api/stores/{sid}/ingestion-jobs")
def ingestion_jobs(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"jobs": db.list_ingestion_jobs(sid)}


# ---- recall -------------------------------------------------------------
class RecallBody(BaseModel):
    query: str
    context: Optional[dict] = {}
    retrieval_mode: Optional[str] = "hybrid"
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.3
    include_expired: Optional[bool] = False
    include_archived: Optional[bool] = False
    save: Optional[bool] = True


@app.post("/api/stores/{sid}/recall")
def run_recall(sid: str, body: RecallBody, request: Request):
    require_owner(request)  # recall is a Pro feature and writes access logs
    store = db.get_store(sid, owner_of(request))
    if not store:
        raise HTTPException(404, "not_found")
    entries = db.list_entries(sid, include_archived=True, include_expired=True)
    res = recall_engine.recall(store, entries, body.query, top_k=body.top_k or 5, threshold=body.threshold or 0.3,
                               mode=body.retrieval_mode or "hybrid",
                               include_expired=bool(body.include_expired), include_archived=bool(body.include_archived),
                               entry_vectors=db.entry_embeddings(sid))
    for r in res["retrieved"]:
        db.touch_entry(r["id"])
        db.log_access(sid, r["id"], owner_of(request), "recall", body.query, r["reason"])
    if body.save:
        res["recall_test_id"] = db.log_recall(sid, {
            "query": body.query, "context": body.context, "retrieval_mode": body.retrieval_mode,
            "top_k": body.top_k, "threshold": body.threshold, "retrieved_entries": res["retrieved"],
            "assembled_context": res["assembled_context"], "score": res["recall_quality_score"],
            "latency_ms": res["latency_ms"]}, owner_of(request))
    return res


@app.get("/api/stores/{sid}/recall-tests")
def recall_tests(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"recall_tests": db.list_recall_tests(sid)}


@app.post("/api/admin/backfill-embeddings")
def backfill_embeddings(request: Request):
    """Embed any memories that don't yet have a vector (e.g. seed data). Idempotent."""
    require_owner(request)
    import embeddings
    if not embeddings.available():
        return {"ok": False, "reason": "embeddings_unavailable"}
    missing = db.entries_missing_embeddings(limit=5000)
    done = 0
    for i in range(0, len(missing), 64):
        batch = missing[i:i + 64]
        vecs = embeddings.embed_texts([t for _, t in batch])
        if not vecs:
            break
        for (mid, _), v in zip(batch, vecs):
            db.set_entry_embedding(mid, v)
            done += 1
    return {"ok": True, "embedded": done, "remaining": len(db.entries_missing_embeddings(limit=1))}


# ---- deploy: serve a store as a live recall API --------------------------
class StoreDeployBody(BaseModel):
    top_k: Optional[int] = 5
    threshold: Optional[float] = 0.3
    retrieval_mode: Optional[str] = "hybrid"


@app.get("/api/stores/{sid}/deployment")
def get_store_deployment(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"deployment": db.get_store_deployment(sid)}


@app.post("/api/stores/{sid}/deploy")
def deploy_store_endpoint(sid: str, body: StoreDeployBody, request: Request):
    o = require_owner(request)
    owned_store_or_404(sid, request)
    dep = db.deploy_store(sid, o, body.model_dump())
    return {"ok": True, "deployment": dep, "path": f"/api/memory-endpoint/{dep['token']}/recall"}


@app.delete("/api/stores/{sid}/deploy")
def undeploy_store_endpoint(sid: str, request: Request):
    require_owner(request)
    owned_store_or_404(sid, request)
    db.undeploy_store(sid)
    return {"ok": True}


# Public — the unguessable token IS the credential.
@app.get("/api/memory-endpoint/{token}")
def memory_endpoint_info(token: str):
    dep = db.store_deployment_by_token(token)
    if not dep:
        raise HTTPException(404, "unknown_or_disabled_endpoint")
    store = db.get_store_raw(dep["store_id"])
    return {"ok": True, "store": store["name"] if store else None, "calls": dep["call_count"],
            "usage": "POST {\"query\": \"...\"} to this path + /recall for relevant memories."}


class MemoryRecallBody(BaseModel):
    query: str
    top_k: Optional[int] = None
    threshold: Optional[float] = None


@app.post("/api/memory-endpoint/{token}/recall")
def memory_endpoint_recall(token: str, body: MemoryRecallBody):
    dep = db.store_deployment_by_token(token)
    if not dep:
        raise HTTPException(404, "unknown_or_disabled_endpoint")
    sid = dep["store_id"]
    store = db.get_store_raw(sid)
    if not store:
        raise HTTPException(404, "store_not_found")
    s = db._pj(dep.get("settings"), {}) or {}
    entries = db.list_entries(sid, include_archived=False, include_expired=False)
    res = recall_engine.recall(store, entries, body.query,
                               top_k=body.top_k or s.get("top_k") or 5,
                               threshold=body.threshold if body.threshold is not None else s.get("threshold", 0.3),
                               mode=s.get("retrieval_mode", "hybrid"), entry_vectors=db.entry_embeddings(sid))
    db.bump_store_deployment(token)
    return {"query": body.query, "memories": res["retrieved"], "engine": res.get("engine"),
            "recall_quality_score": res["recall_quality_score"]}


# ---- rules --------------------------------------------------------------
class RuleBody(BaseModel):
    name: str
    description: Optional[str] = ""
    rule_type: Optional[str] = "remember"
    condition_json: Optional[dict] = {}
    action_json: Optional[dict] = {}
    priority: Optional[int] = 100
    enabled: Optional[bool] = True


@app.get("/api/stores/{sid}/rules")
def list_rules(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"rules": db.list_rules(sid)}


@app.post("/api/stores/{sid}/rules")
def create_rule(sid: str, body: RuleBody, request: Request):
    require_owner(request)
    return {"ok": True, "rule": db.create_rule(sid, body.model_dump())}


@app.put("/api/rules/{rid}")
def update_rule(rid: str, body: RuleBody, request: Request):
    require_owner(request)
    r = db.update_rule(rid, body.model_dump())
    if not r:
        raise HTTPException(404, "not_found")
    return {"ok": True, "rule": r}


@app.delete("/api/rules/{rid}")
def delete_rule(rid: str, request: Request):
    require_owner(request)
    db.delete_rule(rid)
    return {"ok": True}


@app.post("/api/rules/{rid}/enable")
def enable_rule(rid: str, request: Request):
    require_owner(request)
    return {"ok": True, "rule": db.update_rule(rid, {"enabled": True})}


@app.post("/api/rules/{rid}/disable")
def disable_rule(rid: str, request: Request):
    require_owner(request)
    return {"ok": True, "rule": db.update_rule(rid, {"enabled": False})}


# ---- governance ---------------------------------------------------------
@app.get("/api/stores/{sid}/governance")
def get_governance(sid: str, request: Request):
    s = db.get_store(sid, owner_of(request))
    if not s:
        raise HTTPException(404, "not_found")
    return {"governance": s.get("governance"), "retention_policy": s.get("retention_policy"),
            "access_scope": s.get("access_scope"), "badges": store_badges(s)}


class GovBody(BaseModel):
    governance: Optional[dict] = None
    retention_policy: Optional[dict] = None
    access_scope: Optional[dict] = None


@app.put("/api/stores/{sid}/governance")
def update_governance(sid: str, body: GovBody, request: Request):
    o = require_owner(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if data.get("governance", {}).get("risk_level"):
        data["risk_level"] = data["governance"]["risk_level"]
    s = db.update_store(sid, data, o)
    if not s:
        raise HTTPException(404, "not_found_or_forbidden")
    return {"ok": True, "store": deco_store(s)}


@app.post("/api/stores/{sid}/scan-risk")
def scan_risk(sid: str, request: Request):
    if not db.get_store(sid, owner_of(request)):
        raise HTTPException(404, "not_found")
    entries = db.list_entries(sid, include_archived=True)
    return rules_engine.scan_store_risk(entries)


# ---- analytics ----------------------------------------------------------
@app.get("/api/stores/{sid}/analytics")
def analytics(sid: str, request: Request):
    if not db.get_store(sid, owner_of(request)):
        raise HTTPException(404, "not_found")
    return db.store_analytics(sid)


@app.get("/api/stores/{sid}/access-logs")
def store_access_logs(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"logs": db.access_logs(sid)}


@app.get("/api/stores/{sid}/audit")
def store_audit(sid: str, request: Request):
    owned_store_or_404(sid, request)
    return {"audit": db.audit_for(sid)}


# ---- export -------------------------------------------------------------
@app.get("/api/stores/{sid}/export/json")
def export_json(sid: str, request: Request, include_entries: bool = False):
    s = db.get_store(sid, owner_of(request))
    if not s:
        raise HTTPException(404, "not_found")
    entries = db.list_entries(sid)
    return exporter.to_package(s, db.list_rules(sid), entries, include_entries=include_entries)


@app.get("/api/stores/{sid}/export/yaml")
def export_yaml(sid: str, request: Request):
    s = db.get_store(sid, owner_of(request))
    if not s:
        raise HTTPException(404, "not_found")
    pkg = exporter.to_package(s, db.list_rules(sid), db.list_entries(sid))
    return PlainTextResponse(exporter.to_yaml(pkg))
