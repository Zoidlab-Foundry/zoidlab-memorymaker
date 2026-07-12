export interface Project {
  id: string; name: string; slug: string; description: string; status: string;
  risk_level: string; icon: string; accent: string; owner_user_id?: string | null;
  store_count?: number; memory_count?: number; updated_at?: string;
}

export interface Governance {
  risk_level: string; pii_risk?: string; sensitive_data?: boolean; retention_days?: number;
  auto_expire?: boolean; redaction?: boolean; requires_human_approval?: boolean;
  tenant_isolation?: boolean; audit_logging?: boolean; logs_access?: boolean;
  user_deletion?: boolean; right_to_be_forgotten?: boolean;
}

export interface Store {
  id: string; name: string; slug: string; description: string; project_id?: string | null;
  memory_type: string; storage_backend: string; embedding_provider: string; embedding_model: string;
  retrieval_strategy: string; chunking_strategy: any; retention_policy: any; access_scope: any;
  governance: Governance; status: string; risk_level: string; owner_user_id?: string | null;
  memory_count?: number; recall_score?: number | null; last_test?: string | null;
  created_at?: string; updated_at?: string; badges?: string[];
  project?: Project | null; rules?: Rule[]; recall_tests?: any[];
}

export interface MemoryEntry {
  id: string; store_id: string; title: string; content: string; summary?: string;
  source: string; source_ref?: string; memory_type: string; tags: string[]; metadata: any;
  sensitivity: string; confidence: number; embedding_status: string; token_count?: number;
  expires_at?: string | null; archived_at?: string | null; deleted_at?: string | null;
  last_accessed_at?: string | null; created_at?: string; updated_at?: string;
  user_scope_id?: string | null; badges?: string[];
}

export interface Rule {
  id: string; store_id: string; name: string; description: string; rule_type: string;
  condition_json: any; action_json: any; priority: number; enabled: boolean;
}

export interface Retrieved {
  id: string; title: string; content: string; score: number; reason: string; matched: string[];
  source?: string; memory_type?: string; sensitivity?: string; tags: string[];
  created_at?: string; expires_at?: string | null; expired?: boolean;
}

export interface RecallResult {
  query: string; retrieved: Retrieved[]; excluded: { title: string; reason: string }[];
  assembled_context: string; recall_quality_score: number; latency_ms: number;
  suggestions: string[]; mode: string; strategy: string; recall_test_id?: string;
}

export interface Stats {
  stores: number; total: number; active: number; expired: number; high_risk: number;
  recall_tests: number; avg_recall: number | null; storage_kb: number;
}

export interface WhoAmI { authenticated: boolean; email?: string; name?: string; tier?: string; admin?: boolean; }
