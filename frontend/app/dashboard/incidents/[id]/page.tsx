
"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import {
  getIncident,
  approveIncidentFix,
  rejectIncidentFix,
  triggerAgentRun,
} from "@/lib/api";
import type { Incident, WSAgentUpdateData } from "@/lib/types";
import { useWSEvent } from "@/lib/websocket";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Loader,
  Play,
  AlertTriangle,
  Clock,
  FileText,
} from "lucide-react";

function formatDate(ts: string) {
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function IncidentDetailPage({ params }: PageProps) {
  const { id } = use(params);

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  async function fetchIncident() {
    try {
      const data = await getIncident(id);
      const parsed: Incident = {
        ...data,
        causalChain:
          typeof data.causalChain === "string"
            ? JSON.parse(data.causalChain as unknown as string)
            : data.causalChain,
        timeline:
          typeof data.timeline === "string"
            ? JSON.parse(data.timeline as unknown as string)
            : data.timeline,
      };
      setIncident(parsed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load incident");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchIncident();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useWSEvent(
    "agent_update",
    (raw) => {
      const d = raw as WSAgentUpdateData;
      if (d.incidentId === id) {
        setAgentLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ${d.step}: ${d.message}`,
        ]);
      }
    },
    [id]
  );

  useWSEvent("incident_resolved", (raw) => {
    const d = raw as { incidentId: string };
    if (d.incidentId === id) fetchIncident();
  });

  async function handleApprove() {
    if (!incident || actionLoading) return;
    setActionLoading("approve");
    try {
      await approveIncidentFix(incident.id);
      await fetchIncident();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject() {
    if (!incident || actionLoading) return;
    setActionLoading("reject");
    try {
      await rejectIncidentFix(incident.id);
      await fetchIncident();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rejection failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRunAgent() {
    if (!incident || actionLoading) return;
    setActionLoading("run");
    setAgentLogs([]);
    try {
      await triggerAgentRun(incident.id);
      await fetchIncident();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader size={20} className="animate-spin text-indigo-400" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-6">
        <p className="text-red-400 text-sm">{error ?? "Incident not found"}</p>
        <Link href="/dashboard/incidents" className="text-xs text-indigo-400 mt-2 inline-block">
          ← Back
        </Link>
      </div>
    );
  }

  const isPendingApproval = incident.status === "pending_approval";
  const canRun = ["open", "failed"].includes(incident.status);

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-[--border] flex items-center gap-3">
        <Link
          href="/dashboard/incidents"
          className="text-[--text-muted] hover:text-slate-200 transition-colors"
        >
          <ArrowLeft size={16} />
        </Link>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{incident.summary}</p>
          <p className="text-xs text-[--text-muted] font-mono mt-0.5">
            {incident.id} · {incident.app?.name ?? incident.appId} ·{" "}
            {formatDate(incident.createdAt)}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {canRun && (
            <button
              onClick={handleRunAgent}
              disabled={!!actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-medium transition-colors"
            >
              {actionLoading === "run" ? (
                <Loader size={12} className="animate-spin" />
              ) : (
                <Play size={12} />
              )}
              Run Agent
            </button>
          )}

          {isPendingApproval && (
            <>
              <button
                onClick={handleApprove}
                disabled={!!actionLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-green-600 hover:bg-green-500 disabled:opacity-50 text-xs font-medium transition-colors"
              >
                {actionLoading === "approve" ? (
                  <Loader size={12} className="animate-spin" />
                ) : (
                  <CheckCircle2 size={12} />
                )}
                Approve Fix
              </button>
              <button
                onClick={handleReject}
                disabled={!!actionLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[--border] hover:bg-[--bg-elevated] disabled:opacity-50 text-xs text-[--text-secondary] transition-colors"
              >
                {actionLoading === "reject" ? (
                  <Loader size={12} className="animate-spin" />
                ) : (
                  <XCircle size={12} />
                )}
                Reject
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-5">
        {incident.rootCause && (
          <section>
            <SectionHeader icon={<AlertTriangle size={13} />} label="Root Cause" />
            <div className="mt-2 p-3 rounded-lg bg-[--bg-surface] border border-[--border] text-sm text-[--text-secondary] leading-relaxed">
              {incident.rootCause}
            </div>
          </section>
        )}

        {incident.causalChain && incident.causalChain.length > 0 && (
          <section>
            <SectionHeader icon={<Clock size={13} />} label="Causal Chain" />
            <ol className="mt-2 space-y-1.5">
              {incident.causalChain.map((step, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0 w-5 h-5 rounded-full bg-[--accent-dim] flex items-center justify-center text-[10px] font-mono text-indigo-300">
                    {i + 1}
                  </span>
                  <p className="text-sm text-[--text-secondary] pt-0.5">{step}</p>
                </li>
              ))}
            </ol>
          </section>
        )}

        {incident.timeline && incident.timeline.length > 0 && (
          <section>
            <SectionHeader icon={<Clock size={13} />} label="Event Timeline" />
            <div className="mt-2 space-y-0">
              {incident.timeline.map((ev, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-2 h-2 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                    {i < incident.timeline!.length - 1 && (
                      <div className="w-px flex-1 bg-[--border] mt-0.5" />
                    )}
                  </div>
                  <div className="pb-4 min-w-0">
                    <p className="text-[10px] font-mono text-[--text-muted]">{ev.time}</p>
                    <p className="text-sm text-[--text-secondary]">{ev.event}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {incident.proposedFix && (
          <section>
            <SectionHeader icon={<Play size={13} />} label="Proposed Fix" />
            <pre className="mt-2 p-4 rounded-lg bg-[--bg-base] border border-[--border] text-xs font-mono text-slate-200 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {incident.proposedFix}
            </pre>
            {incident.fixApplied && (
              <div className="mt-2 flex items-center gap-2">
                <CheckCircle2 size={13} className="text-green-400" />
                <span className="text-xs text-green-400">Fix applied</span>
                {incident.fixResult && (
                  <span className="text-xs text-[--text-muted] ml-1">
                    — {incident.fixResult}
                  </span>
                )}
              </div>
            )}
          </section>
        )}

        {incident.postmortem && (
          <section>
            <SectionHeader icon={<FileText size={13} />} label="Postmortem" />
            <div className="mt-2 p-4 rounded-lg bg-[--bg-surface] border border-[--border] text-sm text-[--text-secondary] leading-relaxed whitespace-pre-wrap">
              {incident.postmortem}
            </div>
          </section>
        )}

        {agentLogs.length > 0 && (
          <section>
            <SectionHeader
              icon={<Loader size={13} className="animate-spin" />}
              label="Agent Log (live)"
            />
            <div className="mt-2 p-3 rounded-lg bg-[--bg-base] border border-[--border] space-y-0.5">
              {agentLogs.map((log, i) => (
                <p key={i} className="text-xs font-mono text-[--text-secondary] slide-in">
                  {log}
                </p>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function SectionHeader({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-[--text-muted] uppercase tracking-widest">
      <span className="text-indigo-400">{icon}</span>
      {label}
    </div>
  );
}