export const RISK_STYLE: Record<string, string> = {
  low: "text-ok border-ok/40 bg-ok/10",
  medium: "text-warn border-warn/40 bg-warn/10",
  high: "text-bad border-bad/40 bg-bad/10",
};
export const STATUS_STYLE: Record<string, string> = {
  draft: "text-dim border-line bg-white/5",
  active: "text-ok border-ok/40 bg-ok/10",
  testing: "text-ind border-ind/40 bg-ind/10",
  approved: "text-cy border-cy/40 bg-cy/10",
  deployed: "text-cy border-cy/40 bg-cy/10",
  deprecated: "text-faint border-line bg-white/5",
  archived: "text-faint border-line bg-white/5",
};
export const SENS_STYLE: Record<string, string> = {
  low: "text-ok border-ok/40 bg-ok/10",
  medium: "text-warn border-warn/40 bg-warn/10",
  high: "text-bad border-bad/40 bg-bad/10",
};
export const BADGE_STYLE: Record<string, string> = {
  "Low Risk": RISK_STYLE.low, "Medium Risk": RISK_STYLE.medium, "High Risk": RISK_STYLE.high,
  "PII Risk": "text-bad border-bad/40 bg-bad/10", "Sensitive": "text-warn border-warn/40 bg-warn/10",
  "Requires Approval": "text-vi border-vi/40 bg-vi/10", "Auto Expiration": "text-ind border-ind/40 bg-ind/10",
  "Expiring Soon": "text-warn border-warn/40 bg-warn/10", "Archived": "text-faint border-line bg-white/5",
  "Tenant Isolated": "text-cy border-cy/40 bg-cy/10", "Tenant Scoped": "text-cy border-cy/40 bg-cy/10",
  "Global Memory": "text-dim border-line bg-white/5", "Logs Access": "text-dim border-line bg-white/5",
  "Forgettable": "text-ind border-ind/40 bg-ind/10", "External Source": "text-ind border-ind/40 bg-ind/10",
};

export const MEMORY_TYPES = ["conversation", "user_profile", "customer_profile", "project", "organization",
  "document", "tool", "agent", "session", "long_term", "episodic", "semantic", "procedural"];
export const BACKENDS = ["mock", "postgres_pgvector", "chroma", "qdrant", "pinecone", "weaviate", "redis_vector", "milvus"];
export const RETRIEVAL_MODES = ["hybrid", "semantic", "keyword", "recent", "user", "project", "policy-safe"];
export const RULE_TYPES = ["remember", "forget", "expiration", "redaction", "sensitivity", "access", "retrieval", "summarization", "deduplication"];

export const label = (s: string) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
