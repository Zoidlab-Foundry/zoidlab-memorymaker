"""MemoryMaker assistant manifest — what the in-app assistant knows and may do.

This file is the assistant's security boundary: only the capabilities declared here exist
for it, and they execute through this app's own session-authed API (require_pro/require_owner
+ visibility scoping apply). Delete/forget/archive operations are intentionally not declared.
"""
from foundry_common.assistant import cap, page

MANIFEST = {
    "app": "MemoryMaker",
    "description": (
        "MemoryMaker is an AI memory studio: memory stores hold typed memories "
        "(conversation, profile, project, episodic, semantic, ...), recall is real semantic "
        "retrieval over local embeddings, and every store carries retention/redaction rules "
        "and governance (sensitivity, expiry, right-to-be-forgotten). Stores can be deployed "
        "as live recall APIs for agents to call."
    ),
    "base_url": "http://127.0.0.1:8500",
    "pages": [
        page("/", "Dashboard", "Overview: stats, recent stores and activity."),
        page("/projects", "Projects", "Group memory stores into projects."),
        page("/stores", "Memory Stores", "Browse, search, and filter every memory store.",
             assists={"new-store": "the Create Store button"}),
        page("/stores/new", "Create Store", "Define a new store: type, backend, retrieval, governance."),
        page("/stores/[id]", "Store Detail", "One store: config, rules, recent recall tests."),
        page("/stores/[id]/memories", "Memories", "The entries inside a store, with badges and filters."),
        page("/stores/[id]/ingest", "Ingest", "Add memories from text, files, JSON, or a URL."),
        page("/stores/[id]/recall", "Recall Test Lab", "Run recall queries and see what's retrieved and why.",
             assists={"run-recall": "the Run recall button"}),
        page("/stores/[id]/rules", "Rules", "Retention, redaction, and sensitivity rules for the store."),
        page("/stores/[id]/governance", "Governance", "Risk level, PII flags, retention policy, access scope."),
        page("/stores/[id]/deploy", "Deploy", "Serve the store as a live token-authed recall API."),
    ],
    "capabilities": [
        cap("list_stores", "GET", "/api/stores", risk="read",
            desc="The user's memory stores with type, backend, risk, and badges.",
            params={"search": "text filter", "project_id": "filter by project id",
                    "memory_type": "filter by memory type", "risk_level": "low|medium|high",
                    "status": "draft|active|testing|approved|deployed|archived"}),
        cap("get_store", "GET", "/api/stores/{sid}", risk="read",
            desc="One store with its config, rules, and recent recall tests.",
            params={"sid": "store id"}),
        cap("list_memories", "GET", "/api/stores/{sid}/memories", risk="read",
            desc="The memory entries inside a store, with sensitivity/expiry badges.",
            params={"sid": "store id", "search": "text filter",
                    "memory_type": "filter by memory type", "sensitivity": "low|medium|high"}),
        cap("list_rules", "GET", "/api/stores/{sid}/rules", risk="read",
            desc="A store's retention/redaction/sensitivity rules.", params={"sid": "store id"}),
        cap("stats", "GET", "/api/stats", risk="read",
            desc="Dashboard counts: stores, memories, projects, recent activity."),
        cap("create_store", "POST", "/api/stores", risk="write",
            desc="Create a memory store. memory_type is one of the typed memories "
                 "(e.g. long_term, conversation, user_profile, episodic, semantic).",
            params={"name": "store name (required)", "description": "short description",
                    "project_id": "optional project id", "memory_type": "memory type",
                    "storage_backend": "e.g. postgres_pgvector",
                    "retrieval_strategy": "semantic|keyword|hybrid|recent",
                    "risk_level": "low|medium|high"}),
        cap("add_memory", "POST", "/api/stores/{sid}/memories", risk="write",
            desc="Add one memory entry to a store. Content passes through the store's "
                 "redaction/sensitivity rules on ingest.",
            params={"sid": "store id", "content": "the memory text (required)",
                    "title": "short title", "summary": "one-line summary",
                    "tags": "list of tag strings", "memory_type": "memory type",
                    "sensitivity": "low|medium|high",
                    "expires_at": "ISO datetime when it should expire"}),
        cap("run_recall", "POST", "/api/stores/{sid}/recall", risk="write",
            desc="Run a real recall test against a store (semantic/hybrid over local "
                 "embeddings). Saves the test and writes access logs.",
            params={"sid": "store id", "query": "the recall query (required)",
                    "retrieval_mode": "semantic|keyword|hybrid|recent (default hybrid)",
                    "top_k": "how many memories to retrieve (default 5)",
                    "threshold": "similarity threshold 0-1 (default 0.3)"}),
    ],
}
