import type { Project, Store, MemoryEntry, Rule, RecallResult, Stats, WhoAmI } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { ...init, credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try { const j = await r.json(); detail = j.detail || (j.reasons ? j.reasons.join("; ") : detail); } catch {}
    const e = new Error(detail) as Error & { status?: number }; e.status = r.status; throw e;
  }
  return r.json();
}
const qs = (q: Record<string, string>) => {
  const s = new URLSearchParams(Object.entries(q).filter(([, v]) => v)).toString();
  return s ? "?" + s : "";
};

export const api = {
  whoami: () => req<WhoAmI>("/api/whoami"),
  stats: () => req<Stats>("/api/stats"),
  meta: () => req<{ memory_types: string[]; backends: string[]; retrieval_modes: string[]; rule_types: string[] }>("/api/meta"),

  projects: () => req<{ projects: Project[] }>("/api/projects").then((d) => d.projects),
  project: (id: string) => req<Project & { stores: Store[] }>(`/api/projects/${id}`),
  createProject: (b: any) => req<{ ok: boolean; project: Project }>("/api/projects", { method: "POST", body: JSON.stringify(b) }),

  stores: (q: Record<string, string> = {}) => req<{ stores: Store[]; count: number }>(`/api/stores${qs(q)}`),
  store: (id: string) => req<Store>(`/api/stores/${id}`),
  createStore: (b: any) => req<{ ok: boolean; store: Store }>("/api/stores", { method: "POST", body: JSON.stringify(b) }),
  updateStore: (id: string, b: any) => req<{ ok: boolean; store: Store }>(`/api/stores/${id}`, { method: "PUT", body: JSON.stringify(b) }),
  cloneStore: (id: string) => req<{ ok: boolean; store: Store }>(`/api/stores/${id}/clone`, { method: "POST" }),

  memories: (id: string, q: Record<string, string> = {}) => req<{ memories: MemoryEntry[]; count: number }>(`/api/stores/${id}/memories${qs(q)}`),
  memory: (mid: string) => req<MemoryEntry>(`/api/memories/${mid}`),
  createMemory: (id: string, b: any) => req<{ ok: boolean; memory: MemoryEntry; governance: string[] }>(`/api/stores/${id}/memories`, { method: "POST", body: JSON.stringify(b) }),
  updateMemory: (mid: string, b: any) => req<{ ok: boolean; memory: MemoryEntry }>(`/api/memories/${mid}`, { method: "PUT", body: JSON.stringify(b) }),
  memoryAction: (mid: string, action: "archive" | "restore" | "forget") => req<{ ok: boolean }>(`/api/memories/${mid}/${action}`, { method: "POST" }),
  deleteMemory: (mid: string) => req<{ ok: boolean }>(`/api/memories/${mid}`, { method: "DELETE" }),

  ingestText: (id: string, b: any) => req<any>(`/api/stores/${id}/ingest/text`, { method: "POST", body: JSON.stringify(b) }),
  ingestJson: (id: string, payload: any) => req<any>(`/api/stores/${id}/ingest/json`, { method: "POST", body: JSON.stringify(payload) }),
  ingestFile: async (id: string, file: File) => {
    const fd = new FormData(); fd.append("file", file);
    const r = await fetch(`/api/stores/${id}/ingest/file`, { method: "POST", credentials: "include", body: fd });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
    return r.json();
  },
  ingestionJobs: (id: string) => req<{ jobs: any[] }>(`/api/stores/${id}/ingestion-jobs`).then((d) => d.jobs),

  recall: (id: string, b: any) => req<RecallResult>(`/api/stores/${id}/recall`, { method: "POST", body: JSON.stringify(b) }),
  recallTests: (id: string) => req<{ recall_tests: any[] }>(`/api/stores/${id}/recall-tests`).then((d) => d.recall_tests),

  rules: (id: string) => req<{ rules: Rule[] }>(`/api/stores/${id}/rules`).then((d) => d.rules),
  createRule: (id: string, b: any) => req<{ ok: boolean; rule: Rule }>(`/api/stores/${id}/rules`, { method: "POST", body: JSON.stringify(b) }),
  updateRule: (rid: string, b: any) => req<{ ok: boolean; rule: Rule }>(`/api/rules/${rid}`, { method: "PUT", body: JSON.stringify(b) }),
  deleteRule: (rid: string) => req<{ ok: boolean }>(`/api/rules/${rid}`, { method: "DELETE" }),
  toggleRule: (rid: string, on: boolean) => req<{ ok: boolean }>(`/api/rules/${rid}/${on ? "enable" : "disable"}`, { method: "POST" }),

  governance: (id: string) => req<{ governance: any; retention_policy: any; access_scope: any; badges: string[] }>(`/api/stores/${id}/governance`),
  updateGovernance: (id: string, b: any) => req<{ ok: boolean; store: Store }>(`/api/stores/${id}/governance`, { method: "PUT", body: JSON.stringify(b) }),
  scanRisk: (id: string) => req<{ high_risk_count: number; secrets_found: number; flagged: any[] }>(`/api/stores/${id}/scan-risk`, { method: "POST" }),

  analytics: (id: string) => req<any>(`/api/stores/${id}/analytics`),
  accessLogs: (id: string) => req<{ logs: any[] }>(`/api/stores/${id}/access-logs`).then((d) => d.logs),
  audit: (id: string) => req<{ audit: any[] }>(`/api/stores/${id}/audit`).then((d) => d.audit),
  storeDeployment: (id: string) => req<{ deployment: any }>(`/api/stores/${id}/deployment`).then((d) => d.deployment),
  deployStore: (id: string, b: any = {}) => req<{ ok: boolean; deployment: any; path: string }>(`/api/stores/${id}/deploy`, { method: "POST", body: JSON.stringify(b) }),
  undeployStore: (id: string) => req<{ ok: boolean }>(`/api/stores/${id}/deploy`, { method: "DELETE" }),
  exportJsonUrl: (id: string, entries = false) => `/api/stores/${id}/export/json${entries ? "?include_entries=true" : ""}`,
  exportYamlUrl: (id: string) => `/api/stores/${id}/export/yaml`,
};
