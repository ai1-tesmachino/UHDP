export type BrowserBenchmarkId = "web-application" | "javascript" | "graphics-rendering";
export type BrowserTabCount = 2 | 4 | 6 | 8;
export type BrowserTestDuration = 1 | 3 | 5;
export type BrowserPerformanceStatus = "Ready" | "Running" | "Stopped" | "Completed";

export interface BrowserPerformanceResult {
    webApplicationScore: number | null;
    javascriptScore: number | null;
    graphicsScore: number | null;
    multiTabResponsiveness: number;
    peakMemoryUsageMb: number;
    browserCrashes: number;
    overallResult: "SIMULATED COMPLETE" | "INCOMPLETE — SIMULATED";
    isDemoData: true;
}

export interface BrowserPerformanceTestState {
    selectedBenchmarks: BrowserBenchmarkId[];
    selectedTabCount: BrowserTabCount;
    selectedDurationMinutes: BrowserTestDuration;
    status: BrowserPerformanceStatus;
    elapsedSeconds: number;
    finalResult: BrowserPerformanceResult | null;
}

export const browserBenchmarkOptions: Array<{
    id: BrowserBenchmarkId;
    label: string;
    description: string;
}> = [
    {
        id: "web-application",
        label: "Web Application Performance",
        description: "Illustrative page responsiveness score.",
    },
    {
        id: "javascript",
        label: "JavaScript Performance",
        description: "Illustrative script execution score.",
    },
    {
        id: "graphics-rendering",
        label: "Graphics / Rendering Performance",
        description: "Illustrative rendering score; no graphics workload is run.",
    },
];

export const browserTabCountOptions: BrowserTabCount[] = [2, 4, 6, 8];
export const browserTestDurationOptions: BrowserTestDuration[] = [1, 3, 5];

export function createInitialBrowserPerformanceTest(): BrowserPerformanceTestState {
    return {
        selectedBenchmarks: [],
        selectedTabCount: 2,
        selectedDurationMinutes: 1,
        status: "Ready",
        elapsedSeconds: 0,
        finalResult: null,
    };
}

export function createDemoBrowserPerformanceResult(
    test: BrowserPerformanceTestState,
    completed: boolean,
): BrowserPerformanceResult {
    const selected = new Set(test.selectedBenchmarks);
    const tabs = test.selectedTabCount;
    const duration = test.selectedDurationMinutes;

    return {
        webApplicationScore: selected.has("web-application")
            ? Math.max(35, 91 - tabs * 2 + duration)
            : null,
        javascriptScore: selected.has("javascript")
            ? Math.max(35, 96 - tabs + duration)
            : null,
        graphicsScore: selected.has("graphics-rendering")
            ? Math.max(35, 88 - tabs * 2 + duration * 2)
            : null,
        multiTabResponsiveness: Math.max(30, 100 - tabs * 7 + duration),
        peakMemoryUsageMb: 180 + tabs * 42,
        browserCrashes: 0,
        overallResult: completed ? "SIMULATED COMPLETE" : "INCOMPLETE — SIMULATED",
        isDemoData: true,
    };
}
