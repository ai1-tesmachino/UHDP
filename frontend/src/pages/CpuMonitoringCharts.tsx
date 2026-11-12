import { memo, useMemo } from "react";
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import type { CpuMonitoringReading } from "../demo/cpuMonitoring";

interface CpuUsageChartPoint {
    elapsedSeconds: number;
    utilisationPercent: number;
}

interface CpuTemperatureChartPoint {
    elapsedSeconds: number;
    packageTemperatureC: number;
}

interface CpuMonitoringChartsProps {
    readings: CpuMonitoringReading[];
    logicalThreadCount: number;
    minimumPackageTemperatureC: number | null;
    maximumPackageTemperatureC: number | null;
}

const cpuThreadChartColors = [
    "var(--primary)",
    "var(--information)",
    "var(--success)",
    "var(--warning)",
    "var(--destructive)",
    "#0f766e",
    "#7c3aed",
    "#c2410c",
];

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

const CpuThreadChart = memo(function CpuThreadChart({
    threadIndex,
    currentUtilisation,
    data,
}: {
    threadIndex: number;
    currentUtilisation: number | null;
    data: CpuUsageChartPoint[];
}) {
    const color = cpuThreadChartColors[threadIndex % cpuThreadChartColors.length];
    return (
        <article className="min-w-0 rounded-sm border border-border bg-card p-3">
            <header className="mb-1 flex items-center justify-between gap-2">
                <h4 className="m-0 text-xs font-bold text-foreground">CPU {threadIndex}</h4>
                <span className="text-xs tabular-nums text-muted-foreground">
                    Current: <strong className="text-foreground">{currentUtilisation === null ? "—" : `${currentUtilisation}%`}</strong>
                </span>
            </header>
            <div className="h-[150px] min-w-0" role="img" aria-label={`CPU ${threadIndex} utilisation history`}>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 6, right: 6, bottom: 4, left: -20 }}>
                        <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" vertical={false} />
                        <XAxis
                            type="number"
                            dataKey="elapsedSeconds"
                            domain={getElapsedDomain(data)}
                            tickFormatter={formatMonitoringTime}
                            tick={{ fontSize: 9 }}
                            tickCount={3}
                            stroke="var(--muted-foreground)"
                            label={{
                                value: "Time (mm:ss)",
                                position: "insideBottom",
                                offset: -1,
                                fill: "var(--muted-foreground)",
                                fontSize: 9,
                            }}
                        />
                        <YAxis
                            type="number"
                            domain={[0, 100]}
                            ticks={[0, 50, 100]}
                            tickFormatter={(value: number) => `${value}%`}
                            tick={{ fontSize: 9 }}
                            width={38}
                            stroke="var(--muted-foreground)"
                        />
                        <Tooltip
                            formatter={(value) => [`${Number(value).toFixed(0)}%`, "Utilisation"]}
                            labelFormatter={(value) => `Time: ${formatMonitoringTime(Number(value))}`}
                            contentStyle={{
                                backgroundColor: "var(--card)",
                                borderColor: "var(--border)",
                                borderRadius: "var(--radius-md)",
                                color: "var(--foreground)",
                            }}
                            labelStyle={{ color: "var(--foreground)" }}
                        />
                        <Line
                            type="monotone"
                            dataKey="utilisationPercent"
                            name={`CPU ${threadIndex}`}
                            stroke={color}
                            strokeWidth={2}
                            dot={data.length === 1 ? { r: 2 } : false}
                            activeDot={{ r: 3 }}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </article>
    );
});

const CpuTemperatureHistoryChart = memo(function CpuTemperatureHistoryChart({
    data,
}: {
    data: CpuTemperatureChartPoint[];
}) {
    const temperatures = data.map((reading) => reading.packageTemperatureC);
    const lowest = temperatures.length > 0 ? Math.min(...temperatures) : 0;
    const highest = temperatures.length > 0 ? Math.max(...temperatures) : 100;
    const padding = Math.max(2, (highest - lowest) * 0.15);
    const temperatureDomain: [number, number] = [
        Math.floor(lowest - padding),
        Math.ceil(highest + padding),
    ];
    return (
        <div className="h-64 min-w-0" role="img" aria-label="CPU package temperature history">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 10, right: 16, bottom: 12, left: 8 }}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" />
                    <XAxis
                        type="number"
                        dataKey="elapsedSeconds"
                        domain={getElapsedDomain(data)}
                        tickFormatter={formatMonitoringTime}
                        tick={{ fontSize: 10 }}
                        tickCount={6}
                        stroke="var(--muted-foreground)"
                        label={{
                            value: "Time (mm:ss)",
                            position: "insideBottom",
                            offset: -5,
                            fill: "var(--muted-foreground)",
                            fontSize: 10,
                        }}
                    />
                    <YAxis
                        type="number"
                        domain={temperatureDomain}
                        tickFormatter={(value: number) => `${value}°`}
                        tick={{ fontSize: 10 }}
                        width={42}
                        stroke="var(--muted-foreground)"
                        label={{
                            value: "Temperature (°C)",
                            angle: -90,
                            position: "insideLeft",
                            fill: "var(--muted-foreground)",
                            fontSize: 10,
                        }}
                    />
                    <Tooltip
                        formatter={(value) => [`${Number(value).toFixed(1)} °C`, "CPU package"]}
                        labelFormatter={(value) => `Time: ${formatMonitoringTime(Number(value))}`}
                        contentStyle={{
                            backgroundColor: "var(--card)",
                            borderColor: "var(--border)",
                            borderRadius: "var(--radius-md)",
                            color: "var(--foreground)",
                        }}
                        labelStyle={{ color: "var(--foreground)" }}
                        itemStyle={{ color: "var(--information)" }}
                    />
                    <Line
                        type="monotone"
                        dataKey="packageTemperatureC"
                        name="CPU package temperature"
                        stroke="var(--information)"
                        strokeWidth={2}
                        dot={data.length === 1 ? { r: 2 } : false}
                        activeDot={{ r: 4 }}
                        isAnimationActive={false}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
});

export default function CpuMonitoringCharts({
    readings,
    logicalThreadCount,
    minimumPackageTemperatureC,
    maximumPackageTemperatureC,
}: CpuMonitoringChartsProps) {
    const latestReading = readings[readings.length - 1] ?? null;
    const threadHistories = useMemo(
        () => Array.from(
            { length: Math.max(0, Math.floor(logicalThreadCount)) },
            (_, threadIndex) => readings.flatMap((reading) => {
                const utilisationPercent = reading.threadUtilisationPercent[threadIndex];
                return utilisationPercent === undefined
                    ? []
                    : [{ elapsedSeconds: reading.elapsedSeconds, utilisationPercent }];
            }),
        ),
        [logicalThreadCount, readings],
    );
    const temperatureHistory = useMemo(
        () => readings.flatMap((reading) => reading.packageTemperatureC === null
            ? []
            : [{ elapsedSeconds: reading.elapsedSeconds, packageTemperatureC: reading.packageTemperatureC }]),
        [readings],
    );
    const currentTemperature = latestReading?.packageTemperatureC ?? null;
    const hasCpuTemperature = currentTemperature !== null;

    return (
        <>
            <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="cpu-threads-title">
                <div className="mb-3">
                    <h3 className="m-0 text-sm font-bold text-foreground" id="cpu-threads-title">Per-core utilisation</h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                        Separate history for every logical processor. Utilisation scale: 0–100%.
                    </p>
                </div>
                {threadHistories.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                        {threadHistories.map((history, threadIndex) => (
                            <CpuThreadChart
                                key={threadIndex}
                                threadIndex={threadIndex}
                                currentUtilisation={latestReading?.threadUtilisationPercent[threadIndex] ?? null}
                                data={history}
                            />
                        ))}
                    </div>
                ) : (
                    <p className="m-0 text-sm text-muted-foreground">No logical processors are listed in the demo inventory.</p>
                )}
            </section>

            <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="cpu-temperature-title">
                <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h3 className="m-0 text-sm font-bold text-foreground" id="cpu-temperature-title">CPU temperature</h3>
                        <p className="mt-1 text-xs text-muted-foreground">CPU package temperature · simulated demo sensor</p>
                    </div>
                    <span className="text-[10px] font-semibold text-muted-foreground">°C</span>
                </div>
                {hasCpuTemperature ? (
                    <>
                        <CpuTemperatureHistoryChart data={temperatureHistory} />
                        <div className="grid gap-3 border-t border-border pt-3 sm:grid-cols-3" aria-label="CPU package temperature summary">
                            <div>
                                <span className="block text-xs text-muted-foreground">Current</span>
                                <strong className="text-sm tabular-nums text-foreground">{currentTemperature.toFixed(1)} °C</strong>
                            </div>
                            <div>
                                <span className="block text-xs text-muted-foreground">Minimum this session</span>
                                <strong className="text-sm tabular-nums text-foreground">
                                    {minimumPackageTemperatureC === null ? "Not available" : `${minimumPackageTemperatureC.toFixed(1)} °C`}
                                </strong>
                            </div>
                            <div>
                                <span className="block text-xs text-muted-foreground">Maximum this session</span>
                                <strong className="text-sm tabular-nums text-foreground">
                                    {maximumPackageTemperatureC === null ? "Not available" : `${maximumPackageTemperatureC.toFixed(1)} °C`}
                                </strong>
                            </div>
                        </div>
                    </>
                ) : (
                    <p className="m-0 rounded-sm border border-border bg-muted/40 p-4 text-sm text-muted-foreground" role="status">
                        CPU temperature unavailable
                    </p>
                )}
            </section>
        </>
    );
}
