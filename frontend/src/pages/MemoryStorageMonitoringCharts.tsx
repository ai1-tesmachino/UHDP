import { memo } from "react";
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import type { MemoryMonitoringReading } from "../demo/memoryMonitoring";
import type { StorageMonitoringReading } from "../demo/storageMonitoring";

type MemoryChartProps = {
    kind: "memory";
    totalGb: number;
    readings: MemoryMonitoringReading[];
};

type StorageChartProps = {
    kind: "storage";
    readings: StorageMonitoringReading[];
};

type MemoryStorageMonitoringChartsProps = MemoryChartProps | StorageChartProps;

function formatMonitoringTime(seconds: number): string {
    const wholeSeconds = Math.max(0, Math.floor(seconds));
    const minutes = Math.floor(wholeSeconds / 60);
    const remainingSeconds = wholeSeconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function getElapsedDomain(data: Array<{ elapsedSeconds: number }>): [number, number] {
    const first = data[0]?.elapsedSeconds ?? 0;
    const last = data[data.length - 1]?.elapsedSeconds ?? first + 1;
    return first === last ? [first, first + 1] : [first, last];
}

function ChartShell({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div className="h-56 min-w-0" role="img" aria-label={label}>
            {children}
        </div>
    );
}

function ChartGrid() {
    return <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" vertical={false} />;
}

const MemoryUsageChart = memo(function MemoryUsageChart({
    totalGb,
    readings,
}: MemoryChartProps) {
    return (
        <ChartShell label="Memory used and available history">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={readings} margin={{ top: 8, right: 12, bottom: 10, left: 8 }}>
                    <ChartGrid />
                    <XAxis
                        type="number"
                        dataKey="elapsedSeconds"
                        domain={getElapsedDomain(readings)}
                        tickFormatter={formatMonitoringTime}
                        tick={{ fontSize: 10 }}
                        tickCount={5}
                        stroke="var(--muted-foreground)"
                        label={{ value: "Time (mm:ss)", position: "insideBottom", offset: -4, fill: "var(--muted-foreground)", fontSize: 10 }}
                    />
                    <YAxis
                        type="number"
                        domain={[0, totalGb]}
                        tickFormatter={(value: number) => `${value} GB`}
                        tick={{ fontSize: 10 }}
                        width={48}
                        stroke="var(--muted-foreground)"
                        label={{ value: "Memory (GB)", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 10 }}
                    />
                    <Tooltip
                        formatter={(value, name) => [`${Number(value).toFixed(2)} GB`, name]}
                        labelFormatter={(value) => `Time: ${formatMonitoringTime(Number(value))}`}
                        contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", color: "var(--foreground)" }}
                        labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Line type="monotone" dataKey="usedGb" name="Used" stroke="var(--primary)" strokeWidth={2} dot={false} isAnimationActive={false} />
                    <Line type="monotone" dataKey="availableGb" name="Available" stroke="var(--information)" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
            </ResponsiveContainer>
        </ChartShell>
    );
});

const ThroughputChart = memo(function ThroughputChart({
    readings,
    metric,
    title,
    color,
}: {
    readings: StorageMonitoringReading[];
    metric: "readMBps" | "writeMBps";
    title: string;
    color: string;
}) {
    return (
        <ChartShell label={`${title} throughput history`}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={readings} margin={{ top: 8, right: 12, bottom: 10, left: 8 }}>
                    <ChartGrid />
                    <XAxis
                        type="number"
                        dataKey="elapsedSeconds"
                        domain={getElapsedDomain(readings)}
                        tickFormatter={formatMonitoringTime}
                        tick={{ fontSize: 10 }}
                        tickCount={5}
                        stroke="var(--muted-foreground)"
                        label={{ value: "Time (mm:ss)", position: "insideBottom", offset: -4, fill: "var(--muted-foreground)", fontSize: 10 }}
                    />
                    <YAxis
                        type="number"
                        domain={[0, "auto"]}
                        tickFormatter={(value: number) => `${value}`}
                        tick={{ fontSize: 10 }}
                        width={42}
                        stroke="var(--muted-foreground)"
                        label={{ value: "MB/s", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 10 }}
                    />
                    <Tooltip
                        formatter={(value) => [`${Number(value).toFixed(1)} MB/s`, title]}
                        labelFormatter={(value) => `Time: ${formatMonitoringTime(Number(value))}`}
                        contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", color: "var(--foreground)" }}
                        labelStyle={{ color: "var(--foreground)" }}
                    />
                    <Line type="monotone" dataKey={metric} name={title} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
            </ResponsiveContainer>
        </ChartShell>
    );
});

export default function MemoryStorageMonitoringCharts(props: MemoryStorageMonitoringChartsProps) {
    if (props.kind === "memory") {
        return <MemoryUsageChart kind="memory" totalGb={props.totalGb} readings={props.readings} />;
    }

    return (
        <div className="grid min-w-0 gap-4 xl:grid-cols-2">
            <section className="min-w-0 rounded-sm border border-border bg-card p-3" aria-labelledby="drive-read-chart-title">
                <h4 className="mb-1 text-xs font-bold text-foreground" id="drive-read-chart-title">Read speed history</h4>
                <ThroughputChart readings={props.readings} metric="readMBps" title="Read" color="var(--information)" />
            </section>
            <section className="min-w-0 rounded-sm border border-border bg-card p-3" aria-labelledby="drive-write-chart-title">
                <h4 className="mb-1 text-xs font-bold text-foreground" id="drive-write-chart-title">Write speed history</h4>
                <ThroughputChart readings={props.readings} metric="writeMBps" title="Write" color="var(--warning)" />
            </section>
        </div>
    );
}
