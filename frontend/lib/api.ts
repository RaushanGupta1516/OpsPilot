import type {
  MonitoredApp,
  MetricSnapshot,
  Anomaly,
  Incident,
  AgentRunResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Apps ─────────────────────────────────────────────────────────────────
export const getApps = () => apiFetch<MonitoredApp[]>("/apps/");

export const getApp = (id: string) => apiFetch<MonitoredApp>(`/apps/${id}`);

export const createApp = (payload: { name: string; url: string }) =>
  apiFetch<MonitoredApp>("/apps/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const deleteApp = (id: string) =>
  apiFetch<{ message: string }>(`/apps/${id}`, { method: "DELETE" });

// ── Metrics ──────────────────────────────────────────────────────────────
export const getMetrics = (appId: string, limit = 60) =>
  apiFetch<MetricSnapshot[]>(`/metrics/${appId}?limit=${limit}`);

export const triggerHealthCheck = (appId: string) =>
  apiFetch<{ status: string; response_time: number | null }>(
    `/apps/${appId}/check`,
    { method: "POST" }
  );

// ── Anomalies ────────────────────────────────────────────────────────────
export const getAnomalies = (appId?: string, limit = 50) => {
  const q = new URLSearchParams({ limit: String(limit) });
  if (appId) q.set("app_id", appId);
  return apiFetch<Anomaly[]>(`/metrics/anomalies?${q}`);
};

// ── Incidents ────────────────────────────────────────────────────────────
export const getIncidents = (appId?: string) => {
  const q = appId ? `?app_id=${appId}` : "";
  return apiFetch<Incident[]>(`/agent/incidents${q}`);
};

export const getIncident = (id: string) =>
  apiFetch<Incident>(`/agent/incidents/${id}`);

export const approveIncidentFix = (incidentId: string) =>
  apiFetch<AgentRunResult>(`/agent/resume`, {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, approved: true }),
  });

export const rejectIncidentFix = (incidentId: string) =>
  apiFetch<AgentRunResult>(`/agent/resume`, {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId, approved: false }),
  });

export const triggerAgentRun = (incidentId: string) =>
  apiFetch<AgentRunResult>(`/agent/trigger`, {
    method: "POST",
    body: JSON.stringify({ incident_id: incidentId }),
  });

// ── RAG ──────────────────────────────────────────────────────────────────
export const getRagStats = () =>
  apiFetch<{ total_documents: number; collection_name: string }>("/rag/stats");