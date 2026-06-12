"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getIncidents } from "@/lib/api";
import type { Incident, IncidentStatus } from "@/lib/types";
import {
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  Loader,
  ChevronRight,
} from "lucide-react";

const STATUS_CONFIG: Record
  IncidentStatus,
  { label: string; icon: React.ReactNode; color: string }
> = {
  open: {
    label: "Open",
    icon: <AlertTriangle size={12} />,
    color: "text-orange-400 bg-orange-500/10 border-orange-500/20",
  },
  investigating: {
    label: "Investigating",
    icon: <Loader size={12} className="animate-spin" />,
    color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
  },
  pending_approval: {
    label: "Awaiting Approval",
    icon: <Clock size={12} />,
    color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  },
  resolved: {
    label: "Resolved",
    icon: <CheckCircle2 size={12} />,
    color: "text-green-400 bg-green-500/10 border-green-500/20",
  },
  failed: {
    label: "Failed",
    icon: <XCircle size={12} />,
    color: "text-red-400 bg-red-500/10 border-red-500/20",
  },
};

function formatDate(ts: string) {
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getIncidents()
      .then((data) => {
        setIncidents(
          data.sort(
            (a, b) =>
              new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          )
        );
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-[--border] flex items-center gap-2">
        <AlertTriangle size={16} className="text-orange-400" />
        <h1 className="text-sm font-semibold">Incidents</h1>
        {!loading && (
          <span className="text-xs text-[--text-muted] font-mono ml-1">
            {incidents.length} total
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="p-3 rounded-md bg-red-500/10 border border-red-500/20 text-xs text-red-400 mb-4">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-16 rounded-lg bg-[--bg-surface] border border-[--border] animate-pulse"
              />
            ))}
          </div>
        ) : incidents.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-[--text-muted]">
            <CheckCircle2 size={24} className="mb-2 text-green-500/50" />
            <p className="text-sm">No incidents recorded</p>
            <p className="text-xs mt-1">The system is running clean</p>
          </div>
        ) : (
          <div className="space-y-2">
            {incidents.map((inc) => {
              const cfg = STATUS_CONFIG[inc.status];
              return (
                <Link
                  key={inc.id}
                  href={`/dashboard/incidents/${inc.id}`}
                  className="flex items-center gap-4 px-4 py-3 rounded-lg border border-[--border] bg-[--bg-surface] hover:bg-[--bg-elevated] hover:border-indigo-500/30 transition-all group"
                >
                  <span
                    className={`flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-medium shrink-0 ${cfg.color}`}
                  >
                    {cfg.icon}
                    {cfg.label}
                  </span>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 truncate">{inc.summary}</p>
                    {inc.app && (
                      <p className="text-xs text-[--text-muted] mt-0.5">{inc.app.name}</p>
                    )}
                  </div>

                  <span className="text-xs text-[--text-muted] shrink-0 font-mono">
                    {formatDate(inc.createdAt)}
                  </span>

                  <ChevronRight
                    size={14}
                    className="text-[--text-muted] shrink-0 group-hover:text-indigo-400 transition-colors"
                  />
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}