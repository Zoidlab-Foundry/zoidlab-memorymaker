# ZoidLab MemoryMaker

**Part of the [ZoidLab platform](https://github.com/Zoidlab-Foundry-m/zoidlab-foundry) · Foundry Package 04 · Live at [memorymaker.zoidlab.ai](https://memorymaker.zoidlab.ai)**

**Design, govern, and deploy AI memory systems.** — *Where AI memory becomes manageable.*

MemoryMaker is the control plane for how AI remembers, forgets, retrieves, ranks, expires, and
protects information. Not a vector-database UI — an inspectable, governed, tenant-aware memory
layer for Nyquest agents, workflows, websites, and enterprise apps.

> **Access — Nyquest Pro.** MemoryMaker is a Pro workspace: sign in with your Nyquest account
> (a **Pro or Teams** plan is required; the whole app is gated). One `.zoidlab.ai` session is
> shared across every ZoidLab app.

## The core workflow

**Project → Memory Store → Ingest → Inspect → Recall Test → Rules → Governance → Export / Deploy**

It answers three questions clearly: **what** does the AI remember, **why** did it remember that,
and **when** should it forget it.

- **Memory Explorer** — inspect every stored memory: content, source, tags, sensitivity, confidence,
  expiration, access history; edit / archive / delete / forget.
- **Ingestion** — manual text, JSON, or TXT/MD/CSV upload; every entry runs the rules engine
  (secret redaction, sensitivity scoring, retention).
- **Recall Test Lab** — enter a query and see what's retrieved, the score and reason, the assembled
  context, what was excluded, and suggested tuning.
- **Rules** — remember / forget / expiration / redaction / sensitivity / access / retrieval rules.
- **Governance** — risk level, PII risk, retention, redaction, tenant isolation, right-to-be-forgotten,
  visible badges, and a risk scan.
- **Analytics** — growth, recall scores, by source / sensitivity / type, expiring-soon, high-risk.
- **Export** — the **Nyquest Memory Package** (`memory.package.json`) + YAML.

## Stack

Aligned to the ZoidLab platform standard (Builder / Marketplace / Prompter / Foundry):

- **Frontend** — Next.js 15, React 19, TypeScript, TailwindCSS (dark)
- **Backend** — FastAPI (Python), Postgres with per-tenant FORCE row-level security (all access
  behind `db_pg.py`; every query runs as the non-superuser `app_rls` role keyed on
  `app.current_owner`, so tenant isolation is enforced by the database, not by application
  code). Vector backend is a config-level abstraction (`postgres_pgvector`, `chroma`, `qdrant`,
  `pinecone`, `weaviate`, `redis_vector`, `milvus`, `mock`).
- **Recall** — deterministic hybrid recall (keyword overlap + tag/source/type + recency + confidence
  + expiration/archive exclusion). Set `ENABLE_MOCK_EMBEDDINGS=false` to wire real vector search.
- **Auth** — shared ZoidLab / Nyquest SSO cookie (`zb_session`), Pro-gated.
- **Deploy** — systemd + Cloudflare Tunnel (`memorymaker-api` :8500, `memorymaker-web` :3500).

## Quick start (local)

```bash
cp .env.example .env          # set BUILDER_SESSION_SECRET

cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8500   # seeds 7 projects + 10 stores on first boot

cd ../frontend
npm install && npm run dev     # http://localhost:3500
```

Or with Docker: `docker compose up --build` (frontend :3500, backend :8500). The backend needs
the shared `foundry-infra` Postgres — set `DATABASE_URL` / `DATABASE_URL_ADMIN`.

## API summary

Projects `GET/POST /api/projects`, `GET/PUT/DELETE /api/projects/{id}`.
Stores `GET/POST /api/stores`, `GET/PUT/DELETE /api/stores/{id}`, `/clone`.
Memories `GET/POST /api/stores/{id}/memories`, `GET/PUT /api/memories/{id}`,
`/archive|/restore|/forget`, `DELETE /api/memories/{id}`.
Ingestion `POST /api/stores/{id}/ingest/text|json|file`, `GET .../ingestion-jobs`.
Recall `POST /api/stores/{id}/recall`, `GET .../recall-tests`.
Rules `GET/POST /api/stores/{id}/rules`, `PUT/DELETE /api/rules/{id}`, `/enable|/disable`.
Governance `GET/PUT /api/stores/{id}/governance`, `POST /api/stores/{id}/scan-risk`.
Analytics `GET /api/stores/{id}/analytics`. Export `GET /api/stores/{id}/export/json|yaml`.

## Nyquest Memory Package

`memory.package.json` (schema_version `1.0`) — storage, retrieval, chunking, retention, governance,
rules, and example (or full) memories. Built by `backend/exporter.py`.

## Data model

`users`, `organizations`, `memory_projects`, `memory_stores`, `memory_entries`, `memory_rules`,
`memory_ingestion_jobs`, `recall_tests`, `memory_access_logs`, `audit_logs` — see `backend/database.py`.

## Deploy notes (memorymaker.zoidlab.ai)

Two systemd services behind the shared Cloudflare Tunnel: `memorymaker-web` (Next, :3500) and
`memorymaker-api` (FastAPI, :8500, localhost). The frontend proxies `/api/*` to the backend. Add
the hostname to the tunnel ingress and route DNS with `cloudflared tunnel route dns`.
