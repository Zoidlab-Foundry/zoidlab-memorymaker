"""SQLite persistence for ZoidLab MemoryMaker.

Postgres-portable: JSONB columns are JSON-encoded TEXT; all access goes through
these helpers so a swap to Postgres+pgvector touches only this file. Ownership =
Nyquest user id (session `sub`); seed content (owner NULL) is visible to everyone.
"""
import os
import json
import uuid
import sqlite3
import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "memorymaker.db")


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _j(v):
    return json.dumps(v)


def _pj(v, default=None):
    if v is None:
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


def _slug(s):
    import re
    return (re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:50] or "item") + "-" + uuid.uuid4().hex[:5]


def init():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT, name TEXT, role TEXT DEFAULT 'user',
                org_id TEXT, created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY, name TEXT, slug TEXT, created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS memory_projects (
                id TEXT PRIMARY KEY, org_id TEXT, owner_user_id TEXT, name TEXT NOT NULL, slug TEXT,
                description TEXT, status TEXT DEFAULT 'active', risk_level TEXT DEFAULT 'low',
                icon TEXT, accent TEXT, created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS memory_stores (
                id TEXT PRIMARY KEY, project_id TEXT, org_id TEXT, owner_user_id TEXT, name TEXT NOT NULL,
                slug TEXT, description TEXT, memory_type TEXT, storage_backend TEXT, embedding_provider TEXT,
                embedding_model TEXT, retrieval_strategy TEXT, chunking_strategy TEXT, retention_policy TEXT,
                access_scope TEXT, governance TEXT, status TEXT DEFAULT 'draft', risk_level TEXT DEFAULT 'low',
                created_at TEXT, updated_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_stores_owner ON memory_stores(owner_user_id);
            CREATE INDEX IF NOT EXISTS idx_stores_project ON memory_stores(project_id);
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY, store_id TEXT, project_id TEXT, org_id TEXT,
                user_scope_id TEXT, session_scope_id TEXT, title TEXT, content TEXT, summary TEXT,
                source TEXT, source_ref TEXT, memory_type TEXT, tags TEXT, metadata TEXT,
                sensitivity TEXT DEFAULT 'low', confidence REAL DEFAULT 0.8, embedding_status TEXT DEFAULT 'mock',
                token_count INTEGER, expires_at TEXT, archived_at TEXT, deleted_at TEXT,
                last_accessed_at TEXT, created_at TEXT, updated_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_entries_store ON memory_entries(store_id);
            CREATE TABLE IF NOT EXISTS memory_rules (
                id TEXT PRIMARY KEY, store_id TEXT, name TEXT, description TEXT, rule_type TEXT,
                condition_json TEXT, action_json TEXT, priority INTEGER DEFAULT 100, enabled INTEGER DEFAULT 1,
                created_at TEXT, updated_at TEXT );
            CREATE TABLE IF NOT EXISTS memory_ingestion_jobs (
                id TEXT PRIMARY KEY, store_id TEXT, source_type TEXT, source_name TEXT, status TEXT,
                records_processed INTEGER DEFAULT 0, records_created INTEGER DEFAULT 0, records_failed INTEGER DEFAULT 0,
                logs TEXT, created_by TEXT, created_at TEXT, completed_at TEXT );
            CREATE TABLE IF NOT EXISTS recall_tests (
                id TEXT PRIMARY KEY, store_id TEXT, query TEXT, context TEXT, retrieval_mode TEXT,
                top_k INTEGER, threshold REAL, retrieved_entries TEXT, assembled_context TEXT, score REAL,
                status TEXT, latency_ms INTEGER, created_by TEXT, created_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_recall_store ON recall_tests(store_id, created_at);
            CREATE TABLE IF NOT EXISTS memory_access_logs (
                id TEXT PRIMARY KEY, store_id TEXT, memory_entry_id TEXT, actor_user_id TEXT, action TEXT,
                query TEXT, reason TEXT, metadata TEXT, created_at TEXT );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY, entity_type TEXT, entity_id TEXT, action TEXT, actor_user_id TEXT,
                details TEXT, created_at TEXT );
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at);
            """
        )
        # migration: entry embedding vector (JSON float array) for real semantic recall
        cols = [r["name"] for r in c.execute("PRAGMA table_info(memory_entries)").fetchall()]
        if "embedding" not in cols:
            c.execute("ALTER TABLE memory_entries ADD COLUMN embedding TEXT")


def _visible(col="owner_user_id"):
    return f"({col} IS NULL OR {col}=?)"


# --- users / admin / audit --------------------------------------------
def upsert_user(uid, email=None, name=None):
    if not uid:
        return
    now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO users (id,email,name,role,created_at,updated_at) VALUES (?,?,?,'user',?,?)
                     ON CONFLICT(id) DO UPDATE SET email=COALESCE(excluded.email,users.email),
                       name=COALESCE(excluded.name,users.name), updated_at=excluded.updated_at""",
                  (uid, email, name, now, now))


def is_admin(uid):
    if not uid:
        return False
    admins = [a.strip() for a in os.environ.get("MEMORYMAKER_ADMINS", "").split(",") if a.strip()]
    if uid in admins:
        return True
    with _conn() as c:
        r = c.execute("SELECT role,email FROM users WHERE id=?", (uid,)).fetchone()
    return bool(r and (r["role"] == "admin" or (r["email"] and r["email"] in admins)))


def audit(entity_type, entity_id, action, actor, details=None):
    with _conn() as c:
        c.execute("INSERT INTO audit_logs (id,entity_type,entity_id,action,actor_user_id,details,created_at) VALUES (?,?,?,?,?,?,?)",
                  (new_id("aud"), entity_type, entity_id, action, actor, _j(details or {}), now_iso()))


def audit_for(entity_id, limit=60):
    with _conn() as c:
        rows = c.execute("SELECT * FROM audit_logs WHERE entity_id=? ORDER BY created_at DESC LIMIT ?", (entity_id, limit)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["details"] = _pj(d.get("details"), {}); out.append(d)
    return out


def log_access(store_id, entry_id, actor, action, query=None, reason=None):
    with _conn() as c:
        c.execute("INSERT INTO memory_access_logs (id,store_id,memory_entry_id,actor_user_id,action,query,reason,metadata,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                  (new_id("acc"), store_id, entry_id, actor, action, query, reason, _j({}), now_iso()))


def access_logs(store_id, limit=100):
    with _conn() as c:
        rows = c.execute("SELECT * FROM memory_access_logs WHERE store_id=? ORDER BY created_at DESC LIMIT ?", (store_id, limit)).fetchall()
    return [dict(r) for r in rows]


# --- projects ----------------------------------------------------------
def list_projects(viewer=None):
    with _conn() as c:
        rows = c.execute(
            f"""SELECT p.*,
                 (SELECT COUNT(*) FROM memory_stores s WHERE s.project_id=p.id) AS store_count,
                 (SELECT COUNT(*) FROM memory_entries e JOIN memory_stores s ON s.id=e.store_id
                    WHERE s.project_id=p.id AND e.deleted_at IS NULL) AS memory_count
                FROM memory_projects p WHERE {_visible()} ORDER BY p.updated_at DESC""", (viewer,)).fetchall()
    return [dict(r) for r in rows]


def get_project(pid, viewer=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM memory_projects WHERE id=? AND {_visible()}", (pid, viewer)).fetchone()
    return dict(r) if r else None


def create_project(data, owner):
    pid = new_id("mproj"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO memory_projects (id,owner_user_id,name,slug,description,status,risk_level,icon,accent,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (pid, owner, data["name"], _slug(data.get("slug") or data["name"]), data.get("description", ""),
                   data.get("status", "active"), data.get("risk_level", "low"), data.get("icon", "◆"),
                   data.get("accent", "#7c5cfc"), now, now))
    audit("project", pid, "created", owner)
    return get_project(pid, owner)


def update_project(pid, data, owner):
    with _conn() as c:
        r = c.execute("SELECT owner_user_id FROM memory_projects WHERE id=?", (pid,)).fetchone()
        if not r or (r["owner_user_id"] != owner and not is_admin(owner)):
            return None
        sets, args = [], []
        for k in ("name", "description", "status", "risk_level", "icon", "accent"):
            if k in data:
                sets.append(f"{k}=?"); args.append(data[k])
        sets.append("updated_at=?"); args.append(now_iso()); args.append(pid)
        c.execute(f"UPDATE memory_projects SET {', '.join(sets)} WHERE id=?", args)
    return get_project(pid, owner)


# --- stores ------------------------------------------------------------
_STORE_JSON = ["chunking_strategy", "retention_policy", "access_scope", "governance"]

DEFAULT_RETENTION = {"default_ttl_days": 365, "auto_expire": True, "allow_manual_forget": True}
DEFAULT_CHUNKING = {"strategy": "semantic", "chunk_size": 800, "chunk_overlap": 120}
DEFAULT_ACCESS = {"scope": "project", "tenant_isolation": True}
DEFAULT_GOV = {"risk_level": "low", "pii_risk": "low", "sensitive_data": False, "retention_days": 365,
               "auto_expire": True, "redaction": True, "requires_human_approval": False,
               "tenant_isolation": True, "audit_logging": True, "logs_access": True,
               "user_deletion": True, "right_to_be_forgotten": True}


def _store_out(row, full=False):
    if not row:
        return None
    d = dict(row)
    for k in _STORE_JSON:
        d[k] = _pj(d.get(k), {})
    with _conn() as c:
        d["memory_count"] = c.execute("SELECT COUNT(*) n FROM memory_entries WHERE store_id=? AND deleted_at IS NULL AND archived_at IS NULL", (d["id"],)).fetchone()["n"]
        lr = c.execute("SELECT score, created_at FROM recall_tests WHERE store_id=? ORDER BY created_at DESC LIMIT 1", (d["id"],)).fetchone()
    d["recall_score"] = round(lr["score"], 2) if lr and lr["score"] is not None else None
    d["last_test"] = lr["created_at"] if lr else None
    return d


def list_stores(viewer=None, search=None, project_id=None, memory_type=None, risk=None, status=None, backend=None, sort="updated"):
    q = f"SELECT * FROM memory_stores WHERE {_visible()}"
    args = [viewer]
    if project_id: q += " AND project_id=?"; args.append(project_id)
    if memory_type and memory_type != "all": q += " AND memory_type=?"; args.append(memory_type)
    if risk and risk != "all": q += " AND risk_level=?"; args.append(risk)
    if status and status != "all": q += " AND status=?"; args.append(status)
    if backend and backend != "all": q += " AND storage_backend=?"; args.append(backend)
    if search:
        q += " AND (lower(name) LIKE ? OR lower(description) LIKE ?)"
        s = f"%{search.lower()}%"; args += [s, s]
    order = {"newest": "created_at DESC", "updated": "updated_at DESC", "name": "name ASC"}.get(sort, "updated_at DESC")
    q += f" ORDER BY {order}"
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    out = [_store_out(r) for r in rows]
    if sort == "largest":
        out.sort(key=lambda s: s["memory_count"], reverse=True)
    if sort == "recall":
        out.sort(key=lambda s: s.get("recall_score") or 0, reverse=True)
    return out


def get_store(sid, viewer=None):
    with _conn() as c:
        r = c.execute(f"SELECT * FROM memory_stores WHERE id=? AND {_visible()}", (sid, viewer)).fetchone()
    return _store_out(r, full=True)


def get_store_raw(sid):
    with _conn() as c:
        r = c.execute("SELECT * FROM memory_stores WHERE id=?", (sid,)).fetchone()
    return _store_out(r, full=True)


def create_store(data, owner):
    sid = new_id("mstore"); now = now_iso()
    gov = {**DEFAULT_GOV, **(data.get("governance") or {})}
    gov["risk_level"] = data.get("risk_level") or gov.get("risk_level", "low")
    with _conn() as c:
        c.execute("""INSERT INTO memory_stores (id,project_id,owner_user_id,name,slug,description,memory_type,storage_backend,
                     embedding_provider,embedding_model,retrieval_strategy,chunking_strategy,retention_policy,access_scope,
                     governance,status,risk_level,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (sid, data.get("project_id"), owner, data["name"], _slug(data.get("slug") or data["name"]),
                   data.get("description", ""), data.get("memory_type", "long_term"), data.get("storage_backend", "mock"),
                   data.get("embedding_provider", "nyquest-router"), data.get("embedding_model", "auto"),
                   data.get("retrieval_strategy", "hybrid"), _j(data.get("chunking_strategy", DEFAULT_CHUNKING)),
                   _j(data.get("retention_policy", DEFAULT_RETENTION)), _j(data.get("access_scope", DEFAULT_ACCESS)),
                   _j(gov), data.get("status", "draft"), gov["risk_level"], now, now))
    audit("store", sid, "created", owner)
    return get_store_raw(sid)


def update_store(sid, data, owner):
    with _conn() as c:
        r = c.execute("SELECT owner_user_id, governance FROM memory_stores WHERE id=?", (sid,)).fetchone()
        if not r or (r["owner_user_id"] != owner and not is_admin(owner)):
            return None
        sets, args = [], []
        for k in ("name", "description", "memory_type", "storage_backend", "embedding_provider", "embedding_model",
                  "retrieval_strategy", "status", "risk_level", "project_id"):
            if k in data:
                sets.append(f"{k}=?"); args.append(data[k])
        for k in ("chunking_strategy", "retention_policy", "access_scope", "governance"):
            if k in data:
                sets.append(f"{k}=?"); args.append(_j(data[k]))
        if "risk_level" in data and "governance" not in data:
            gov = _pj(r["governance"], {}); gov["risk_level"] = data["risk_level"]
            sets.append("governance=?"); args.append(_j(gov))
        sets.append("updated_at=?"); args.append(now_iso()); args.append(sid)
        c.execute(f"UPDATE memory_stores SET {', '.join(sets)} WHERE id=?", args)
    audit("store", sid, "updated", owner)
    return get_store_raw(sid)


def set_store_status(sid, status, owner=None, require_owner=False):
    with _conn() as c:
        r = c.execute("SELECT owner_user_id FROM memory_stores WHERE id=?", (sid,)).fetchone()
        if not r:
            return None
        if require_owner and r["owner_user_id"] != owner and not is_admin(owner):
            return None
        c.execute("UPDATE memory_stores SET status=?, updated_at=? WHERE id=?", (status, now_iso(), sid))
    return get_store_raw(sid)


def clone_store(sid, owner):
    src = get_store_raw(sid)
    if not src:
        return None
    data = {k: src.get(k) for k in ("description", "memory_type", "storage_backend", "embedding_provider",
            "embedding_model", "retrieval_strategy", "chunking_strategy", "retention_policy", "access_scope",
            "governance", "risk_level", "project_id")}
    data["name"] = src["name"] + " (copy)"
    data["status"] = "draft"
    new = create_store(data, owner)
    for r in list_rules(sid):
        create_rule(new["id"], r)
    return new


# --- entries -----------------------------------------------------------
def _entry_out(row):
    d = dict(row)
    d["tags"] = _pj(d.get("tags"), [])
    d["metadata"] = _pj(d.get("metadata"), {})
    d.pop("embedding", None)  # never ship the raw vector to the client
    return d


def set_entry_embedding(mid, vector):
    with _conn() as c:
        c.execute("UPDATE memory_entries SET embedding=?, embedding_status='real' WHERE id=?",
                  (_j(vector) if vector is not None else None, mid))


def entry_embeddings(sid):
    """{entry_id: [floats]} for entries in a store that have a stored embedding."""
    with _conn() as c:
        rows = c.execute("SELECT id, embedding FROM memory_entries WHERE store_id=? AND embedding IS NOT NULL AND deleted_at IS NULL", (sid,)).fetchall()
    out = {}
    for r in rows:
        v = _pj(r["embedding"], None)
        if v:
            out[r["id"]] = v
    return out


def entries_missing_embeddings(limit=5000):
    with _conn() as c:
        rows = c.execute("SELECT id, title, content FROM memory_entries WHERE embedding IS NULL AND deleted_at IS NULL LIMIT ?", (limit,)).fetchall()
    return [(r["id"], f"{r['title'] or ''} {r['content'] or ''}".strip()) for r in rows]


SENSITIVITY_RANK = {"low": 0, "medium": 1, "high": 2}


def list_entries(sid, search=None, source=None, memory_type=None, sensitivity=None, tag=None,
                 include_archived=False, include_expired=True, sort="newest"):
    q = "SELECT * FROM memory_entries WHERE store_id=? AND deleted_at IS NULL"
    args = [sid]
    if not include_archived:
        q += " AND archived_at IS NULL"
    if source and source != "all": q += " AND source=?"; args.append(source)
    if memory_type and memory_type != "all": q += " AND memory_type=?"; args.append(memory_type)
    if sensitivity and sensitivity != "all": q += " AND sensitivity=?"; args.append(sensitivity)
    if search:
        q += " AND (lower(title) LIKE ? OR lower(content) LIKE ?)"
        s = f"%{search.lower()}%"; args += [s, s]
    order = {"newest": "created_at DESC", "oldest": "created_at ASC",
             "expiring": "CASE WHEN expires_at IS NULL THEN 1 ELSE 0 END, expires_at ASC"}.get(sort, "created_at DESC")
    q += f" ORDER BY {order}"
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    out = [_entry_out(r) for r in rows]
    now = now_iso()
    if not include_expired:
        out = [e for e in out if not (e.get("expires_at") and e["expires_at"] < now)]
    if tag:
        out = [e for e in out if tag.lower() in [t.lower() for t in e.get("tags", [])]]
    return out


def get_entry(mid):
    with _conn() as c:
        r = c.execute("SELECT * FROM memory_entries WHERE id=?", (mid,)).fetchone()
    return _entry_out(r) if r else None


def get_entry_visible(mid, viewer=None):
    """Entry lookup scoped to a store the viewer may see (own or shared). Closes IDOR."""
    with _conn() as c:
        r = c.execute(f"""SELECT e.* FROM memory_entries e JOIN memory_stores s ON s.id=e.store_id
                          WHERE e.id=? AND {_visible('s.owner_user_id')}""", (mid, viewer)).fetchone()
    return _entry_out(r) if r else None


def create_entry(sid, data, owner, source="manual"):
    store = get_store_raw(sid)
    if not store:
        return None
    mid = new_id("mem"); now = now_iso()
    content = data.get("content", "")
    with _conn() as c:
        c.execute("""INSERT INTO memory_entries (id,store_id,project_id,user_scope_id,session_scope_id,title,content,summary,
                     source,source_ref,memory_type,tags,metadata,sensitivity,confidence,embedding_status,token_count,
                     expires_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (mid, sid, store.get("project_id"), data.get("user_scope_id"), data.get("session_scope_id"),
                   data.get("title") or content[:60], content, data.get("summary", ""),
                   data.get("source", source), data.get("source_ref"),
                   data.get("memory_type") or store.get("memory_type"), _j(data.get("tags", [])),
                   _j(data.get("metadata") or {}), data.get("sensitivity") or "low", float(data.get("confidence") or 0.8),
                   "mock", max(1, len(content) // 4), data.get("expires_at"), now, now))
    # real semantic embedding (fail-soft to keyword recall if unavailable)
    try:
        import embeddings
        if embeddings.available():
            vecs = embeddings.embed_texts([f"{data.get('title') or ''} {content}".strip()])
            if vecs:
                set_entry_embedding(mid, vecs[0])
    except Exception:
        pass
    audit("store", sid, "memory_added", owner, {"memory_id": mid})
    return get_entry(mid)


def update_entry(mid, data, owner):
    with _conn() as c:
        r = c.execute("""SELECT e.id, s.owner_user_id FROM memory_entries e JOIN memory_stores s ON s.id=e.store_id WHERE e.id=?""", (mid,)).fetchone()
        if not r or (r["owner_user_id"] != owner and not is_admin(owner)):
            return None
        sets, args = [], []
        for k in ("title", "content", "summary", "source", "memory_type", "sensitivity", "expires_at"):
            if k in data:
                sets.append(f"{k}=?"); args.append(data[k])
        for k in ("tags", "metadata"):
            if k in data:
                sets.append(f"{k}=?"); args.append(_j(data[k]))
        if "confidence" in data:
            sets.append("confidence=?"); args.append(float(data["confidence"]))
        sets.append("updated_at=?"); args.append(now_iso()); args.append(mid)
        c.execute(f"UPDATE memory_entries SET {', '.join(sets)} WHERE id=?", args)
    return get_entry(mid)


def entry_action(mid, action, owner):
    now = now_iso()
    col = {"archive": "archived_at", "delete": "deleted_at"}.get(action)
    with _conn() as c:
        r = c.execute("""SELECT e.store_id, s.owner_user_id FROM memory_entries e JOIN memory_stores s ON s.id=e.store_id WHERE e.id=?""", (mid,)).fetchone()
        if not r or (r["owner_user_id"] != owner and not is_admin(owner)):
            return None
        if action == "restore":
            c.execute("UPDATE memory_entries SET archived_at=NULL, deleted_at=NULL, updated_at=? WHERE id=?", (now, mid))
        elif action == "forget":
            c.execute("DELETE FROM memory_entries WHERE id=?", (mid,))
        elif col:
            c.execute(f"UPDATE memory_entries SET {col}=?, updated_at=? WHERE id=?", (now, now, mid))
        db_log = r["store_id"]
    log_access(db_log, mid, owner, action)
    audit("store", db_log, f"memory_{action}", owner, {"memory_id": mid})
    return True


def touch_entry(mid):
    with _conn() as c:
        c.execute("UPDATE memory_entries SET last_accessed_at=? WHERE id=?", (now_iso(), mid))


# --- rules -------------------------------------------------------------
def _rule_out(row):
    d = dict(row); d["condition_json"] = _pj(d.get("condition_json"), {}); d["action_json"] = _pj(d.get("action_json"), {})
    d["enabled"] = bool(d.get("enabled")); return d


def list_rules(sid):
    with _conn() as c:
        rows = c.execute("SELECT * FROM memory_rules WHERE store_id=? ORDER BY priority, created_at", (sid,)).fetchall()
    return [_rule_out(r) for r in rows]


def create_rule(sid, data):
    rid = new_id("rule"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO memory_rules (id,store_id,name,description,rule_type,condition_json,action_json,priority,enabled,created_at,updated_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  (rid, sid, data.get("name", "Rule"), data.get("description", ""), data.get("rule_type", "remember"),
                   _j(data.get("condition_json", {})), _j(data.get("action_json", {})), data.get("priority", 100),
                   1 if data.get("enabled", True) else 0, now, now))
    return [r for r in list_rules(sid) if r["id"] == rid][0]


def update_rule(rid, data):
    with _conn() as c:
        sets, args = [], []
        for k in ("name", "description", "rule_type", "priority"):
            if k in data:
                sets.append(f"{k}=?"); args.append(data[k])
        for k in ("condition_json", "action_json"):
            if k in data:
                sets.append(f"{k}=?"); args.append(_j(data[k]))
        if "enabled" in data:
            sets.append("enabled=?"); args.append(1 if data["enabled"] else 0)
        if not sets:
            return None
        sets.append("updated_at=?"); args.append(now_iso()); args.append(rid)
        c.execute(f"UPDATE memory_rules SET {', '.join(sets)} WHERE id=?", args)
        r = c.execute("SELECT * FROM memory_rules WHERE id=?", (rid,)).fetchone()
    return _rule_out(r) if r else None


def delete_rule(rid):
    with _conn() as c:
        c.execute("DELETE FROM memory_rules WHERE id=?", (rid,))


# --- ingestion jobs / recall tests ------------------------------------
def log_ingestion(sid, source_type, source_name, created, failed, logs, owner):
    jid = new_id("job"); now = now_iso()
    with _conn() as c:
        c.execute("""INSERT INTO memory_ingestion_jobs (id,store_id,source_type,source_name,status,records_processed,
                     records_created,records_failed,logs,created_by,created_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (jid, sid, source_type, source_name, "complete", created + failed, created, failed, _j(logs or []), owner, now, now))
    return jid


def list_ingestion_jobs(sid):
    with _conn() as c:
        rows = c.execute("SELECT * FROM memory_ingestion_jobs WHERE store_id=? ORDER BY created_at DESC LIMIT 50", (sid,)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["logs"] = _pj(d.get("logs"), []); out.append(d)
    return out


def log_recall(sid, data, owner):
    rid = new_id("rt")
    with _conn() as c:
        c.execute("""INSERT INTO recall_tests (id,store_id,query,context,retrieval_mode,top_k,threshold,retrieved_entries,
                     assembled_context,score,status,latency_ms,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (rid, sid, data.get("query"), _j(data.get("context", {})), data.get("retrieval_mode"),
                   data.get("top_k"), data.get("threshold"), _j(data.get("retrieved_entries", [])),
                   data.get("assembled_context", ""), data.get("score"), "complete", data.get("latency_ms"), owner, now_iso()))
    return rid


def list_recall_tests(sid, limit=30):
    with _conn() as c:
        rows = c.execute("SELECT id,query,retrieval_mode,top_k,threshold,score,latency_ms,created_at FROM recall_tests WHERE store_id=? ORDER BY created_at DESC LIMIT ?", (sid, limit)).fetchall()
    return [dict(r) for r in rows]


# --- dashboard / analytics --------------------------------------------
def dashboard_stats(viewer=None):
    now = now_iso()
    with _conn() as c:
        stores = c.execute(f"SELECT COUNT(*) n FROM memory_stores WHERE {_visible()}", (viewer,)).fetchone()["n"]
        ent = c.execute(f"""SELECT e.* FROM memory_entries e JOIN memory_stores s ON s.id=e.store_id
                            WHERE {_visible('s.owner_user_id')} AND e.deleted_at IS NULL""", (viewer,)).fetchall()
        recalls = c.execute(f"""SELECT r.score FROM recall_tests r JOIN memory_stores s ON s.id=r.store_id
                               WHERE {_visible('s.owner_user_id')}""", (viewer,)).fetchall()
    total = len(ent)
    active = sum(1 for e in ent if not e["archived_at"] and not (e["expires_at"] and e["expires_at"] < now))
    expired = sum(1 for e in ent if e["expires_at"] and e["expires_at"] < now)
    high_risk = sum(1 for e in ent if e["sensitivity"] == "high")
    scores = [r["score"] for r in recalls if r["score"] is not None]
    return {"stores": stores, "total": total, "active": active, "expired": expired,
            "high_risk": high_risk, "recall_tests": len(recalls),
            "avg_recall": round(sum(scores) / len(scores), 2) if scores else None,
            "storage_kb": round(sum((e["token_count"] or 0) for e in ent) * 4 / 1024, 1)}


def store_analytics(sid):
    now = now_iso()
    with _conn() as c:
        ent = [dict(r) for r in c.execute("SELECT * FROM memory_entries WHERE store_id=? AND deleted_at IS NULL", (sid,)).fetchall()]
        recalls = c.execute("SELECT score FROM recall_tests WHERE store_id=?", (sid,)).fetchall()
    def group(key):
        g = {}
        for e in ent:
            g[e.get(key) or "unknown"] = g.get(e.get(key) or "unknown", 0) + 1
        return g
    days = {}
    for e in ent:
        d = (e["created_at"] or "")[:10]
        days[d] = days.get(d, 0) + 1
    scores = [r["score"] for r in recalls if r["score"] is not None]
    expiring = sum(1 for e in ent if e["expires_at"] and now <= e["expires_at"] <= (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat() + "Z")
    return {
        "total": len(ent),
        "active": sum(1 for e in ent if not e["archived_at"] and not (e["expires_at"] and e["expires_at"] < now)),
        "expiring_soon": expiring,
        "high_risk": sum(1 for e in ent if e["sensitivity"] == "high"),
        "recall_tests": len(recalls),
        "avg_recall": round(sum(scores) / len(scores), 2) if scores else None,
        "by_source": group("source"), "by_sensitivity": group("sensitivity"), "by_type": group("memory_type"),
        "growth": [{"date": d, "count": days[d]} for d in sorted(days)][-14:],
        "most_accessed": sorted([{"id": e["id"], "title": e["title"], "last_accessed": e["last_accessed_at"]}
                                 for e in ent if e["last_accessed_at"]], key=lambda x: x["last_accessed"] or "", reverse=True)[:5],
    }
