// mirrors backend schemas.py + prisma models

export type AppStatus = "healthy" | "degraded" | "down" | "unknown";
export type AnomalySeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "pending_approval" | "resolved" | "failed";

export interface MonitoredApp {
  id: string;
  name: string;
  url: string;
  status: AppStatus;
  lastChecked: string | null;
  createdAt: string;
}

export interface MetricSnapshot {
  id: string;
  appId: string;
  responseTime: number | null;
  responseTimeMs: number | null;
  statusCode: number | null;
  cpuUsage: number | null;
  cpuPercent: number | null;
  memoryUsage: number | null;
  memoryMb: number | null;
  errorRate: number | null;
  timestamp: string;
  recordedAt: string;
}

export interface Anomaly {
  id: string;
  appId: string;
  app?: MonitoredApp;
  metricType: string;
  severity: AnomalySeverity;
  value: number;
  baseline: number;
  deviation: number;
  description: string;
  timestamp: string;
  incidentId: string | null;
}

export interface Incident {
  id: string;
  appId: string;
  app?: MonitoredApp;
  status: IncidentStatus;
  summary: string;
  rootCause: string | null;
  causalChain: string[] | null;
  timeline: TimelineEvent[] | null;
  proposedFix: string | null;
  fixApplied: boolean;
  fixResult: string | null;
  postmortem: string | null;
  createdAt: string;
  resolvedAt: string | null;
  anomalies?: Anomaly[];
}

export interface TimelineEvent {
  time: string;
  event: string;
}

export interface AgentRunResult {
  incidentId: string;
  status: string;
  summary: string;
  rootCause: string | null;
  proposedFix: string | null;
}

export type WSMessageType =
  | "agent_event"
  | "metric_update"
  | "health_update"
  | "approval_request"
  | "pong";

export interface WSMessage {
  type: WSMessageType;
  data: unknown;
}

export interface WSAnomalyData {
  anomaly: Anomaly;
  appName: string;
}

export interface WSApprovalData {
  incidentId: string;
  appName: string;
  proposedFix: string;
  rootCause: string;
}

export interface WSAgentUpdateData {
  incidentId: string;
  message: string;
  step: string;
}

export interface WSHealthUpdateData {
  app_id: string;
  app_name: string;
  is_healthy: boolean;
  message: string;
}