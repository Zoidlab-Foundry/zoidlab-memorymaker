"""ZoidLab MemoryMaker API — AI memory control plane. Pro-gated at the frontend;
the backend requires a signed-in user for writes. Owner = Nyquest user id.
Spine: project → store → ingest → inspect → recall → rules → governance → export.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Any, List

import database as db
import recall_engine
import rules_engine
import risk_scanner
import ingestion
import exporter
import seed_memory
from auth import owner_of, session


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    n = seed_memory.run()
    if n:
        print(f"[memorymaker] seeded {n} stores + projects")
    yield


app = FastAPI(title="ZoidLab MemoryMaker API", lifespan=lifespan)


def require_owner(request: Request):
    o = owner_of(request)
    if not o:
        raise HTTPException(status_code=401, detail="sign_in_required")
    s = session(request)
    db.upsert_user(o, s.get("email"), s.get("name"))
    return o


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
    store = db.get_store_raw(sid)
    if not store:
        raise HTTPException(404, "not_found")
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
def get_memory(mid: str):
    e = db.get_entry(mid)
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
    store = db.get_store_raw(sid)
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


@app.get("/api/stores/{sid}/ingestion-jobs")
def ingestion_jobs(sid: str):
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
    store = db.get_store(sid, owner_of(request))
    if not store:
        raise HTTPException(404, "not_found")
    entries = db.list_entries(sid, include_archived=True, include_expired=True)
    res = recall_engine.recall(store, entries, body.query, top_k=body.top_k or 5, threshold=body.threshold or 0.3,
                               mode=body.retrieval_mode or "hybrid",
                               include_expired=bool(body.include_expired), include_archived=bool(body.include_archived))
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
def recall_tests(sid: str):
    return {"recall_tests": db.list_recall_tests(sid)}


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
def list_rules(sid: str):
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
def store_access_logs(sid: str):
    return {"logs": db.access_logs(sid)}


@app.get("/api/stores/{sid}/audit")
def store_audit(sid: str):
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
