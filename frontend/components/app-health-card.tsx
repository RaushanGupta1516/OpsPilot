"use client";

import { useState } from "react";
import { ExternalLink, RefreshCw } from "lucide-react";
import type { MonitoredApp, AppStatus, WSHealthUpdateData } from "@/lib/types";
import { triggerHealthCheck } from "@/lib/api";
import { useWSEvent } from "@/lib/websocket";

const STATUS_CONFIG: Record<
	AppStatus,
	{ label: string; dot: string; border: string; bg: string }
> = {
	healthy: {
		label: "Healthy",
		dot: "bg-green-500",
		border: "border-green-500/20",
		bg: "bg-green-500/5",
	},
	degraded: {
		label: "Degraded",
		dot: "bg-yellow-500 pulse-medium",
		border: "border-yellow-500/20",
		bg: "bg-yellow-500/5",
	},
	down: {
		label: "Down",
		dot: "bg-red-500 pulse-critical",
		border: "border-red-500/25",
		bg: "bg-red-500/5",
	},
	unknown: {
		label: "Unknown",
		dot: "bg-slate-500",
		border: "border-slate-600",
		bg: "bg-slate-800/30",
	},
};

interface Props {
	app: MonitoredApp;
	responseTime?: number | null;
}

export function AppHealthCard({ app, responseTime: initialRt }: Props) {
	const [status, setStatus] = useState<AppStatus>(app.status);
	const [rt, setRt] = useState<number | null>(initialRt ?? null);
	const [checking, setChecking] = useState(false);

	useWSEvent(
		"health_update",
		(raw) => {
			const d = raw as WSHealthUpdateData;
			if (d.appId === app.id) {
				setStatus(d.status);
				if (d.responseTime !== null) setRt(d.responseTime);
			}
		},
		[app.id],
	);

	const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG["unknown"];

	async function handleCheck() {
		if (checking) return;
		setChecking(true);
		try {
			const res = await triggerHealthCheck(app.id);
			setRt(res.response_time);
		} catch (e) {
			void e;
		} finally {
			setChecking(false);
		}
	}

	return (
		<div
			className={`rounded-lg border ${cfg.border} ${cfg.bg} p-4 flex flex-col gap-3`}
		>
			<div className="flex items-start justify-between gap-2">
				<div className="min-w-0">
					<p className="text-sm font-medium text-slate-100 truncate">
						{app.name}
					</p>

					<a
						href={app.url}
						target="_blank"
						rel="noopener noreferrer"
						className="flex items-center gap-1 text-xs text-[--text-muted] hover:text-indigo-400 transition-colors mt-0.5"
					>
						<span className="truncate max-w-[140px]">
							{app.url.replace(/^https?:\/\//, "")}
						</span>
						<ExternalLink size={10} className="shrink-0" />
					</a>
				</div>
				<div className="flex items-center gap-1.5 shrink-0">
					<span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
					<span className="text-xs text-[--text-secondary]">{cfg.label}</span>
				</div>
			</div>
			<div className="flex items-center justify-between">
				<div>
					<p className="text-xs text-[--text-muted] mb-0.5">Response</p>
					<p className="font-mono text-sm text-slate-200">
						{rt != null ? `${rt}ms` : "—"}
					</p>
				</div>
				<button
					onClick={handleCheck}
					disabled={checking}
					className="flex items-center gap-1.5 text-xs text-[--text-secondary] hover:text-indigo-400 transition-colors disabled:opacity-40"
				>
					<RefreshCw size={12} className={checking ? "animate-spin" : ""} />
					Check
				</button>
			</div>
		</div>
	);
}
