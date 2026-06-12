
"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, XCircle, Loader } from "lucide-react";
import type { WSApprovalData } from "@/lib/types";
import { approveIncidentFix, rejectIncidentFix } from "@/lib/api";
import { useWSEvent } from "@/lib/websocket";

export function ApprovalModal() {
  const [pending, setPending] = useState<WSApprovalData | null>(null);
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [result, setResult] = useState<"approved" | "rejected" | null>(null);

  useWSEvent("approval_request", (raw) => {
    setPending(raw as WSApprovalData);
    setResult(null);
    setLoading(null);
  });

  useEffect(() => {
    if (!result) return;
    const t = setTimeout(() => {
      setPending(null);
      setResult(null);
    }, 2500);
    return () => clearTimeout(t);
  }, [result]);

  if (!pending) return null;

  async function handleApprove() {
    if (!pending || loading) return;
    setLoading("approve");
    try {
      await approveIncidentFix(pending.incidentId);
      setResult("approved");
    } catch {
      setResult(null);
    } finally {
      setLoading(null);
    }
  }

  async function handleReject() {
    if (!pending || loading) return;
    setLoading("reject");
    try {
      await rejectIncidentFix(pending.incidentId);
      setResult("rejected");
    } catch {
      setResult(null);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pb-8 pointer-events-none">
      <div
        className="pointer-events-auto w-full max-w-lg mx-4 rounded-xl border border-orange-500/30 bg-[--bg-elevated] shadow-2xl shadow-orange-500/10"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-3 border-b border-[--border]">
          <AlertTriangle size={16} className="text-orange-400 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-slate-100">Approval Required</p>
            <p className="text-xs text-[--text-muted]">
              {pending.appName} · Incident {pending.incidentId.slice(0, 8)}
            </p>
          </div>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[--text-muted] mb-1">
              Root Cause
            </p>
            <p className="text-xs text-[--text-secondary] leading-relaxed">
              {pending.rootCause}
            </p>
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-widest text-[--text-muted] mb-1">
              Proposed Fix
            </p>
            <pre className="text-xs font-mono text-slate-200 bg-[--bg-base] rounded-md p-3 overflow-x-auto whitespace-pre-wrap break-words border border-[--border-subtle]">
              {pending.proposedFix}
            </pre>
          </div>

          {result && (
            <div
              className={`flex items-center gap-2 text-sm font-medium ${
                result === "approved" ? "text-green-400" : "text-red-400"
              }`}
            >
              {result === "approved" ? (
                <CheckCircle size={15} />
              ) : (
                <XCircle size={15} />
              )}
              {result === "approved" ? "Fix approved — executing…" : "Fix rejected"}
            </div>
          )}
        </div>

        {!result && (
          <div className="flex items-center gap-3 px-5 pb-5">
            <button
              onClick={handleApprove}
              disabled={!!loading}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {loading === "approve" ? (
                <Loader size={13} className="animate-spin" />
              ) : (
                <CheckCircle size={13} />
              )}
              Approve
            </button>
            <button
              onClick={handleReject}
              disabled={!!loading}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-md border border-[--border] hover:bg-[--bg-surface] disabled:opacity-50 text-sm text-[--text-secondary] transition-colors"
            >
              {loading === "reject" ? (
                <Loader size={13} className="animate-spin" />
              ) : (
                <XCircle size={13} />
              )}
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}