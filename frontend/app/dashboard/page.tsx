"use client";

import { useEffect, useState } from "react";
import { AppHealthCard } from "@/components/app-health-card";
import { AnomalyFeed } from "@/components/anomaly-feed";
import { MetricChart } from "@/components/metric-chart";
import { ApprovalModal } from "@/components/approval-modal";
import { getApps, getAnomalies, getMetrics } from "@/lib/api";
import type { MonitoredApp, Anomaly, MetricSnapshot } from "@/lib/types";
import { Activity, RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const [apps, setApps] = useState<MonitoredApp[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [metrics, setMetrics] = useState<Record<string, MetricSnapshot[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const [appsData, anomalyData] = await Promise.all([
        getApps(),
        getAnomalies(undefined, 30),
      ]);
      setApps(appsData);
      setAnomalies(anomalyData);

      if (appsData.length > 0) {
        const sel = selectedApp ?? appsData[0].id;
        setSelectedApp(sel);
        const m = await getMetrics(sel, 60);
        setMetrics((prev) => ({ ...prev, [sel]: m }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedApp) return;
    getMetrics(selectedApp, 60)
      .then((m) => setMetrics((prev) => ({ ...prev, [selectedApp]: m })))
      .catch(() => null);
  }, [selectedApp]);

  const currentMetrics = selectedApp ? (metrics[selectedApp] ?? []) : [];
  const selectedAppObj = apps.find((a) => a.id === selectedApp);

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-[--border] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-indigo-400" />
          <h1 className="text-sm font-semibold">Dashboard</h1>
          {!loading && (
            <span className="text-xs text-[--text-muted] font-mono ml-1">
              {apps.length} app{apps.length !== 1 ? "s" : ""} monitored
            </span>
          )}
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-[--text-secondary] hover:text-indigo-400 transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          {error} — is the backend running?
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <section>
          <p className="text-xs text-[--text-muted] uppercase tracking-widest mb-3">
            Monitored Apps
          </p>
          {loading ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="h-24 rounded-lg bg-[--bg-surface] border border-[--border] animate-pulse"
                />
              ))}
            </div>
          ) : apps.length === 0 ? (
            <p className="text-sm text-[--text-muted]">
              No apps registered yet. Add one via the API.
            </p>
          ) : (
            <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {apps.map((app) => (
                <div
                  key={app.id}
                  onClick={() => setSelectedApp(app.id)}
                  className={`cursor-pointer rounded-lg transition-all ${
                    selectedApp === app.id
                      ? "ring-1 ring-indigo-500/60"
                      : "hover:ring-1 hover:ring-[--border]"
                  }`}
                >
                  <AppHealthCard app={app} />
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2 space-y-3">
            <p className="text-xs text-[--text-muted] uppercase tracking-widest">
              Metrics
              {selectedAppObj && (
                <span className="ml-2 normal-case text-indigo-400">
                  — {selectedAppObj.name}
                </span>
              )}
            </p>

            {loading ? (
              <div className="grid grid-cols-2 gap-3">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="h-32 rounded-lg bg-[--bg-surface] border border-[--border] animate-pulse"
                  />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <MetricChart data={currentMetrics} metric="responseTime" color="#6366f1" />
                <MetricChart data={currentMetrics} metric="errorRate"    color="#ef4444" />
                <MetricChart data={currentMetrics} metric="cpuUsage"     color="#eab308" />
                <MetricChart data={currentMetrics} metric="memoryUsage"  color="#22c55e" />
              </div>
            )}
          </div>

          <div className="rounded-lg border border-[--border] bg-[--bg-surface] min-h-[300px] flex flex-col">
            <AnomalyFeed initial={anomalies} />
          </div>
        </div>
      </div>

      <ApprovalModal />
    </div>
  );
}