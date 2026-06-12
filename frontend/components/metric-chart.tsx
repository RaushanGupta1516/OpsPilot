"use client";

import {
	LineChart,
	Line,
	XAxis,
	YAxis,
	Tooltip,
	ResponsiveContainer,
} from "recharts";
import type { MetricSnapshot } from "@/lib/types";

interface Props {
	data: MetricSnapshot[];
	metric: "responseTime" | "errorRate" | "cpuUsage" | "memoryUsage";
	label?: string;
	color?: string;
	unit?: string;
}

const METRIC_LABELS: Record<Props["metric"], string> = {
	responseTime: "Response Time",
	errorRate: "Error Rate",
	cpuUsage: "CPU Usage",
	memoryUsage: "Memory Usage",
};

const METRIC_UNITS: Record<Props["metric"], string> = {
	responseTime: "ms",
	errorRate: "%",
	cpuUsage: "%",
	memoryUsage: "%",
};

function formatTime(ts: string) {
	const d = new Date(ts);
	return `${d.getHours().toString().padStart(2, "0")}:${d
		.getMinutes()
		.toString()
		.padStart(2, "0")}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label, unit }: any) {
	if (!active || !payload?.length) return null;
	return (
		<div className="bg-[--bg-elevated] border border-[--border] rounded-md px-3 py-2 text-xs shadow-lg">
			<p className="text-[--text-muted] mb-1">{label}</p>
			<p className="font-mono text-slate-200">
				{payload[0].value?.toFixed(1)}
				{unit}
			</p>
		</div>
	);
}

export function MetricChart({
	data,
	metric,
	label,
	color = "#6366f1",
	unit,
}: Props) {
	const chartData = data
		.slice()
		.sort(
			(a, b) =>
				new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
		)
		.map((s) => ({
			time: formatTime(s.timestamp ?? s.recordedAt),
			value:
				metric === "responseTime"
					? (s.responseTimeMs ?? s.responseTime ?? null)
					: metric === "cpuUsage"
						? (s.cpuPercent ?? s.cpuUsage ?? null)
						: metric === "memoryUsage"
							? (s.memoryMb ?? s.memoryUsage ?? null)
							: (s[metric] ?? null),
		}))
		.filter((d) => d.value !== null);

	const displayUnit = unit ?? METRIC_UNITS[metric];
	const displayLabel = label ?? METRIC_LABELS[metric];

	return (
		<div className="rounded-lg border border-[--border] bg-[--bg-surface] p-4">
			<p className="text-xs text-[--text-secondary] mb-3">{displayLabel}</p>
			{chartData.length === 0 ? (
				<div className="h-24 flex items-center justify-center text-xs text-[--text-muted]">
					No data yet
				</div>
			) : (
				<ResponsiveContainer width="100%" height={80}>
					<LineChart
						data={chartData}
						margin={{ top: 2, right: 2, bottom: 0, left: -28 }}
					>
						<XAxis
							dataKey="time"
							tick={{
								fontSize: 9,
								fill: "var(--text-muted)",
								fontFamily: "var(--font-mono)",
							}}
							tickLine={false}
							axisLine={false}
							interval="preserveStartEnd"
						/>
						<YAxis
							tick={{
								fontSize: 9,
								fill: "var(--text-muted)",
								fontFamily: "var(--font-mono)",
							}}
							tickLine={false}
							axisLine={false}
						/>
						<Tooltip content={<CustomTooltip unit={displayUnit} />} />
						<Line
							type="monotone"
							dataKey="value"
							stroke={color}
							strokeWidth={1.5}
							dot={false}
							activeDot={{ r: 3, fill: color }}
						/>
					</LineChart>
				</ResponsiveContainer>
			)}
		</div>
	);
}
