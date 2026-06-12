"use client";

import { useEffect, useState } from "react";
import { Zap } from "lucide-react";
import type { Anomaly, AnomalySeverity, WSAnomalyData } from "@/lib/types";
import { useWSEvent } from "@/lib/websocket";

const SEV: Record<
	AnomalySeverity,
	{ dot: string; label: string; text: string; pulse: string }
> = {
	critical: {
		dot: "bg-red-500",
		label: "bg-red-500/15 text-red-400 border border-red-500/20",
		text: "text-red-400",
		pulse: "pulse-critical",
	},
	high: {
		dot: "bg-orange-500",
		label: "bg-orange-500/15 text-orange-400 border border-orange-500/20",
		text: "text-orange-400",
		pulse: "pulse-high",
	},
	medium: {
		dot: "bg-yellow-500",
		label: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/20",
		text: "text-yellow-400",
		pulse: "pulse-medium",
	},
	low: {
		dot: "bg-blue-400",
		label: "bg-blue-500/15 text-blue-400 border border-blue-500/20",
		text: "text-blue-400",
		pulse: "",
	},
};

interface FeedItem extends Anomaly {
	_key: string;
	_new: boolean;
}

const MAX_FEED = 40;

function relativeTime(ts: string) {
	const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
	if (diff < 5) return "just now";
	if (diff < 60) return `${diff}s ago`;
	if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
	return `${Math.floor(diff / 3600)}h ago`;
}

interface Props {
	initial?: Anomaly[];
}

export function AnomalyFeed({ initial = [] }: Props) {
	const [items, setItems] = useState<FeedItem[]>(() =>
		initial.map((a, i) => ({ ...a, _key: `init-${i}`, _new: false })),
	);
	const [, tick] = useState(0);

	useWSEvent("anomaly_detected", (raw) => {
		const d = raw as WSAnomalyData;
		const item: FeedItem = {
			...d.anomaly,
			_key: `ws-${Date.now()}-${Math.random()}`,
			_new: true,
		};
		setItems((prev) => {
			const next = [item, ...prev].slice(0, MAX_FEED);
			setTimeout(() => {
				setItems((cur) =>
					cur.map((x) => (x._key === item._key ? { ...x, _new: false } : x)),
				);
			}, 400);
			return next;
		});
	});

	useEffect(() => {
		const t = setInterval(() => tick((n) => n + 1), 30_000);
		return () => clearInterval(t);
	}, []);

	return (
		<div className="flex flex-col h-full">
			<div className="flex items-center justify-between px-4 py-3 border-b border-[--border]">
				<div className="flex items-center gap-2">
					<Zap size={14} className="text-indigo-400" />
					<span className="text-sm font-medium">Anomaly Feed</span>
				</div>
				<span className="text-xs text-[--text-muted] font-mono">
					{items.length} events
				</span>
			</div>

			<div className="flex-1 overflow-y-auto">
				{items.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-32 text-[--text-muted]">
						<p className="text-sm">No anomalies detected</p>
						<p className="text-xs mt-1">All systems nominal</p>
					</div>
				) : (
					<ul className="divide-y divide-[--border-subtle]">
						{items.map((item) => {
							const cfg = SEV[item.severity];
							return (
								<li
									key={item._key}
									className={`px-4 py-3 hover:bg-[--bg-elevated] transition-colors ${item._new ? "slide-in" : ""}`}
								>
									<div className="flex items-start gap-3">
										<div className="mt-1 shrink-0">
											<span
												className={`block w-2 h-2 rounded-full ${cfg.dot} ${cfg.pulse}`}
											/>
										</div>
										<div className="flex-1 min-w-0">
											<div className="flex items-center gap-2 mb-0.5">
												<span className="text-xs font-medium text-slate-200 truncate">
													{item.app?.name ?? item.appId.slice(0, 8)}
												</span>
												<span
													className={`px-1.5 py-0 rounded text-[10px] font-mono ${cfg.label}`}
												>
													{item.severity}
												</span>
											</div>
											<p className="text-xs text-[--text-secondary] leading-relaxed">
												{item.description}
											</p>
											<div className="flex items-center gap-3 mt-1.5">
												<span className="text-[10px] font-mono text-[--text-muted]">
													{item.metricType}
												</span>
												<span className={`text-[10px] font-mono ${cfg.text}`}>
													{item.value.toFixed(1)} / baseline{" "}
													{item.baseline.toFixed(1)}
												</span>
												<span className="text-[10px] text-[--text-muted] ml-auto">
													{relativeTime(item.timestamp)}
												</span>
											</div>
										</div>
									</div>
								</li>
							);
						})}
					</ul>
				)}
			</div>
		</div>
	);
}
