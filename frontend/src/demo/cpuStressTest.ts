import type { DiagnosticResult } from "./hardwareDiagnostics";

export type CpuStressTestStatus =
    | "Not Started"
    | "Ready"
    | "Running"
    | "Stopped"
    | "Finalized";

export interface CpuTemperatureReading {
    elapsedSeconds: number;
    temperatureC: number;
    cpuUtilisationPercent: number;
}

export interface CpuStressTestState {
    status: CpuStressTestStatus;
    elapsedSeconds: number;
    durationSeconds: number;
    readings: CpuTemperatureReading[];
    currentTemperatureC: number | null;
    maximumTemperatureC: number | null;
    cpuUtilisationPercent: number;
    stopReason: "manual" | "duration" | null;
    finalResult: DiagnosticResult | null;
}

const temperatureKeyframes = [
    { second: 0, temperatureC: 42, cpuUtilisationPercent: 20 },
    { second: 30, temperatureC: 51, cpuUtilisationPercent: 47 },
    { second: 60, temperatureC: 59, cpuUtilisationPercent: 66 },
    { second: 90, temperatureC: 66, cpuUtilisationPercent: 79 },
    { second: 120, temperatureC: 71, cpuUtilisationPercent: 88 },
    { second: 150, temperatureC: 75, cpuUtilisationPercent: 94 },
    { second: 180, temperatureC: 78, cpuUtilisationPercent: 96 },
    { second: 210, temperatureC: 77, cpuUtilisationPercent: 92 },
    { second: 240, temperatureC: 78, cpuUtilisationPercent: 97 },
    { second: 270, temperatureC: 77, cpuUtilisationPercent: 93 },
    { second: 300, temperatureC: 78, cpuUtilisationPercent: 95 },
] as const;

export const cpuStressTestDurationSeconds = 300;

export function createInitialCpuStressTest(): CpuStressTestState {
    return {
        status: "Not Started",
        elapsedSeconds: 0,
        durationSeconds: cpuStressTestDurationSeconds,
        readings: [],
        currentTemperatureC: null,
        maximumTemperatureC: null,
        cpuUtilisationPercent: 0,
        stopReason: null,
        finalResult: null,
    };
}

function interpolateAt(second: number, key: "temperatureC" | "cpuUtilisationPercent"): number {
    const upperIndex = temperatureKeyframes.findIndex((frame) => frame.second >= second);
    if (upperIndex <= 0) return temperatureKeyframes[Math.max(upperIndex, 0)][key];

    const lower = temperatureKeyframes[upperIndex - 1];
    const upper = temperatureKeyframes[upperIndex];
    const fraction = (second - lower.second) / (upper.second - lower.second);
    return Number((lower[key] + (upper[key] - lower[key]) * fraction).toFixed(1));
}

export function createCpuTemperatureReading(elapsedSeconds: number): CpuTemperatureReading {
    const second = Math.max(0, Math.min(cpuStressTestDurationSeconds, elapsedSeconds));
    return {
        elapsedSeconds: second,
        temperatureC: interpolateAt(second, "temperatureC"),
        cpuUtilisationPercent: interpolateAt(second, "cpuUtilisationPercent"),
    };
}

function formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
    const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${remainingSeconds}`;
}

export function createCpuStressTestResult(state: CpuStressTestState): DiagnosticResult {
    const completedDuration = state.stopReason === "duration"
        && state.elapsedSeconds >= state.durationSeconds;
    const wasStarted = state.readings.length > 0;
    const status = completedDuration
        ? "PASS"
        : wasStarted
            ? "CANCELLED"
            : "INCONCLUSIVE";
    const summary = completedDuration
        ? "Simulated CPU stress test completed successfully. No actual CPU test or sensor reading was performed."
        : wasStarted
            ? `The simulated CPU stress test stopped at ${formatDuration(state.elapsedSeconds)} and is incomplete; no pass/fail conclusion was made.`
            : "The test was finalized without being started. No CPU test result is available.";

    return {
        status,
        summary,
        measurements: [
            {
                label: "Maximum recorded temperature",
                value: state.maximumTemperatureC === null
                    ? "Not Available"
                    : `${state.maximumTemperatureC.toFixed(1)} °C`,
            },
            { label: "Elapsed duration", value: formatDuration(state.elapsedSeconds) },
            { label: "Configured duration", value: formatDuration(state.durationSeconds) },
        ],
        observations: completedDuration
            ? ["Temperature readings are simulated demo data; no real thermal thresholds were applied."]
            : ["This incomplete demo does not indicate that the CPU passed or failed."],
        isDemoData: true,
    };
}
