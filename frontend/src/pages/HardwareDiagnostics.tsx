import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    Activity,
    Battery,
    Cpu,
    HardDrive,
    MemoryStick,
    Monitor,
    Network,
    Thermometer,
    type LucideIcon,
} from "lucide-react";
import { PageHeader } from "../components/shared/PageHeader";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "../components/ui/dialog";
import {
    useDemoInspection,
    type DiagnosticSkipReason,
    type SkippedDiagnosticTest,
} from "../demo/DemoInspectionContext";
import { demoDevice, getTotalInstalledRamGb } from "../demo/demoDevice";
import { demoSensors } from "../demo/demoSensors";
import type { CpuMonitoringReading } from "../demo/cpuMonitoring";
import {
    createCpuStressTestResult,
    createCpuTemperatureReading,
    cpuStressTestDurationSeconds,
} from "../demo/cpuStressTest";
import {
    browserBenchmarkOptions,
    browserTabCountOptions,
    browserTestDurationOptions,
    type BrowserBenchmarkId,
} from "../demo/browserPerformanceTest";
import {
    hardwareDiagnosticDefinitions,
    type DiagnosticId,
    type DiagnosticResult,
    type DiagnosticStatus,
    type DiagnosticWorkspaceId,
} from "../demo/hardwareDiagnostics";
import {
    createMemoryTestResult,
    createOverallStorageDiagnosticResult,
    createStorageDiagnosticResult,
    createStorageTestResult,
    demoStorageDrives,
    memoryTestDurations,
    memoryTemperatureSensorAvailable,
    storageTestDefinitions,
    type DemoStorageDrive,
    type StorageTestId,
} from "../demo/memoryStorageTests";
import "./hardware-diagnostics.css";

const CpuMonitoringCharts = lazy(() => import("./CpuMonitoringCharts"));
const MemoryStorageMonitoringCharts = lazy(() => import("./MemoryStorageMonitoringCharts"));

type DiagnosticComponentKind =
    | "cpu"
    | "memory"
    | "storage"
    | "graphics"
    | "display"
    | "battery"
    | "sensors"
    | "network"
    | "browser-performance";

type WorkspaceStatus =
    | "Pending"
    | "Ready"
    | "In Progress"
    | "Passed"
    | "Failed"
    | "Warning"
    | "Inconclusive"
    | "Unsupported"
    | "Blocked"
    | "Cancelled"
    | "Skipped"
    | "Completed";

type SkipTarget =
    | { key: string; name: string; kind: "cpu" | "memory" | "browser-performance" }
    | { key: string; name: string; kind: "diagnostic"; diagnosticId: "battery" | "network" }
    | { key: string; name: string; kind: "storage"; driveId: string; testId: StorageTestId };

const skipReasonOptions: DiagnosticSkipReason[] = [
    "Not required",
    "Hardware not available",
    "Test not possible",
    "Technician decision",
    "Other",
];

interface DiagnosticComponentItem {
    id: DiagnosticWorkspaceId;
    title: string;
    detail?: string;
    kind: DiagnosticComponentKind;
    optional?: boolean;
}

interface DiagnosticComponentGroup {
    title: string;
    items: DiagnosticComponentItem[];
}

interface DiagnosticTestStatus {
    name: string;
    status: WorkspaceStatus;
    optional?: boolean;
    skipRecord?: SkippedDiagnosticTest;
}

const navigationGroups: DiagnosticComponentGroup[] = [
    {
        title: "Processor",
        items: [{ id: "cpu", title: "CPU", kind: "cpu" }],
    },
    {
        title: "Memory",
        items: [{ id: "memory", title: "Memory (RAM)", kind: "memory" }],
    },
    {
        title: "Storage",
        items: demoStorageDrives.length > 0
            ? demoStorageDrives.map((drive, index) => ({
                id: `storage:${drive.id}`,
                title: `Drive ${index + 1}`,
                detail: `${drive.type} · ${formatCapacity(drive.capacityGb)}`,
                kind: "storage",
            }))
            : [{ id: "storage", title: "No physical drives", detail: "Not available in demo inventory", kind: "storage" }],
    },
    {
        title: "Graphics",
        items: [
            { id: "graphics", title: "Graphics", kind: "graphics" },
            { id: "display", title: "Display", kind: "display" },
        ],
    },
    {
        title: "Power",
        items: [{ id: "battery", title: "Battery", kind: "battery" }],
    },
    {
        title: "Other Diagnostics",
        items: [
            { id: "sensors", title: "Sensors", kind: "sensors" },
            { id: "network", title: "Network", kind: "network" },
            {
                id: "browser-performance",
                title: "Browser Performance",
                detail: "Optional benchmark",
                kind: "browser-performance",
                optional: true,
            },
        ],
    },
];

const componentIcons: Record<DiagnosticComponentKind, LucideIcon> = {
    cpu: Cpu,
    memory: MemoryStick,
    storage: HardDrive,
    graphics: Activity,
    display: Monitor,
    battery: Battery,
    sensors: Thermometer,
    network: Network,
    "browser-performance": Activity,
};

const terminalStatuses: WorkspaceStatus[] = [
    "Passed",
    "Failed",
    "Warning",
    "Inconclusive",
    "Unsupported",
    "Blocked",
    "Cancelled",
    "Skipped",
    "Completed",
];

function formatCapacity(capacityGb: number) {
    return capacityGb >= 1000 ? `${(capacityGb / 1000).toFixed(2)} TB` : `${capacityGb} GB`;
}

function getStorageTestKey(driveId: string, testId: StorageTestId) {
    return `storage:${driveId}:${testId}`;
}

function formatMemorySize(gigabytes: number) {
    return gigabytes >= 1
        ? `${Number(gigabytes.toFixed(2))} GB`
        : `${Math.round(gigabytes * 1024)} MB`;
}

function formatDuration(seconds: number) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    return hours > 0
        ? `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`
        : `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function formatInspectionTimestamp(timestamp: string | null) {
    if (!timestamp) return "Starting inspection…";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "Unavailable";

    const dateLabel = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric",
    }).format(date);
    const timeLabel = new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
    return `${dateLabel} | ${timeLabel}`;
}

function statusFromDiagnostic(status: DiagnosticStatus): WorkspaceStatus {
    switch (status) {
        case "PASS": return "Passed";
        case "FAIL": return "Failed";
        case "WARNING": return "Warning";
        case "INCONCLUSIVE": return "Inconclusive";
        case "UNSUPPORTED": return "Unsupported";
        case "BLOCKED": return "Blocked";
        case "CANCELLED": return "Cancelled";
        case "NOT RUN": return "Pending";
    }
}

function statusClass(status: WorkspaceStatus) {
    return `is-${status.toLowerCase().replaceAll(" ", "-")}`;
}

function StatusIndicator({ status }: { status: WorkspaceStatus }) {
    return (
        <span className={`hardware-diagnostics-status ${statusClass(status)}`}>
            <span className="hardware-diagnostics-status-dot" aria-hidden="true" />
            {status}
        </span>
    );
}

function SkippedTestNotice({ record }: { record: SkippedDiagnosticTest }) {
    return (
        <div className="mt-3 rounded-sm border border-border bg-muted/40 p-3" role="status">
            <div className="flex flex-wrap items-center gap-2">
                <StatusIndicator status="Skipped" />
                <span className="text-xs text-muted-foreground">This test was not performed.</span>
            </div>
            {record.reason && <p className="mb-0 mt-2 text-xs text-muted-foreground">Reason: {record.reason}</p>}
            {record.note && <p className="mb-0 mt-1 text-xs text-muted-foreground">Remark: {record.note}</p>}
        </div>
    );
}

function DetailsList({ details }: { details: Array<{ label: string; value: string }> }) {
    return (
        <dl className="grid min-w-0 grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
            {details.map((detail) => (
                <div className="min-w-0 border-b border-border pb-2" key={detail.label}>
                    <dt className="text-xs text-muted-foreground">{detail.label}</dt>
                    <dd className="mt-1 break-words text-sm font-medium text-foreground">{detail.value}</dd>
                </div>
            ))}
        </dl>
    );
}

function ResultPanel({ result }: { result: DiagnosticResult }) {
    return (
        <section className="rounded-md border border-border bg-muted/50 p-4" aria-live="polite">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="m-0 text-sm font-bold text-foreground">Latest Result</h3>
                <StatusIndicator status={statusFromDiagnostic(result.status)} />
            </div>
            <p className="m-0 text-sm leading-6 text-foreground">{result.summary}</p>
            {result.measurements.length > 0 && (
                <div className="mt-4">
                    <DetailsList details={result.measurements} />
                </div>
            )}
            {result.observations.length > 0 && (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs leading-5 text-muted-foreground">
                    {result.observations.map((observation) => <li key={observation}>{observation}</li>)}
                </ul>
            )}
        </section>
    );
}

function ProgressBar({ label, value }: { label: string; value: number }) {
    const progress = Math.max(0, Math.min(100, Math.round(value)));
    return (
        <div>
            <div className="mb-2 flex items-center justify-between gap-2 text-xs">
                <span className="text-muted-foreground">{label}</span>
                <strong className="tabular-nums text-foreground">{progress}%</strong>
            </div>
            <div
                className="h-2 overflow-hidden rounded-sm bg-muted"
                role="progressbar"
                aria-label={label}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progress}
            >
                <div className="h-full bg-primary transition-[width] duration-200" style={{ width: `${progress}%` }} />
            </div>
        </div>
    );
}

function findDefinition(id: DiagnosticId) {
    return hardwareDiagnosticDefinitions.find((definition) => definition.id === id);
}

export default function HardwareDiagnostics() {
    const navigate = useNavigate();
    const {
        technicianName,
        physicalInspectionStartedAt,
        startPhysicalInspection,
        diagnosticResults,
        updateDiagnosticResult,
        skippedDiagnosticTests,
        skipDiagnosticTest,
        selectedDiagnosticComponentId,
        setSelectedDiagnosticComponentId,
        cpuStressTest,
        cpuMonitoring,
        advanceCpuMonitoring,
        memoryMonitoring,
        advanceMemoryMonitoring,
        storageMonitoring,
        advanceStorageMonitoring,
        prepareCpuStressTest,
        startCpuStressTest,
        appendCpuStressReading,
        stopCpuStressTest,
        finalizeCpuStressTest,
        memoryTest,
        prepareMemoryTest,
        selectMemoryTestDuration,
        confirmMemoryTestDuration,
        startMemoryTest,
        advanceMemoryTest,
        stopMemoryTest,
        finalizeMemoryTest: commitMemoryTestResult,
        storageTestResults,
        recordStorageTestResult,
        activeStorageTest,
        setActiveStorageTest,
        selectedStorageTestId,
        setSelectedStorageTestId,
        browserPerformanceTest,
        setBrowserPerformanceBenchmarks,
        setBrowserPerformanceTabCount,
        setBrowserPerformanceDuration,
        startBrowserPerformanceTest,
        advanceBrowserPerformanceTest,
        stopBrowserPerformanceTest,
    } = useDemoInspection();
    const [runningDiagnosticId, setRunningDiagnosticId] = useState<DiagnosticId | null>(null);
    const [mobileComponentId, setMobileComponentId] = useState<DiagnosticWorkspaceId>(selectedDiagnosticComponentId);
    const [skipTarget, setSkipTarget] = useState<SkipTarget | null>(null);
    const [skipReason, setSkipReason] = useState<DiagnosticSkipReason | "">("");
    const [skipNote, setSkipNote] = useState("");
    const simpleTestTimerRef = useRef<number | null>(null);
    const cpuTimerRef = useRef<number | null>(null);
    const cpuMonitoringTimerRef = useRef<number | null>(null);
    const memoryTimerRef = useRef<number | null>(null);
    const browserTimerRef = useRef<number | null>(null);
    const cpuTestRef = useRef(cpuStressTest);
    const memoryTestRef = useRef(memoryTest);
    const activeStorageTestRef = useRef(activeStorageTest);
    const browserTestRef = useRef(browserPerformanceTest);

    cpuTestRef.current = cpuStressTest;
    memoryTestRef.current = memoryTest;
    activeStorageTestRef.current = activeStorageTest;
    browserTestRef.current = browserPerformanceTest;

    const overallStorageResult = useMemo(
        () => createOverallStorageDiagnosticResult(demoStorageDrives, storageTestResults),
        [storageTestResults],
    );

    useEffect(() => {
        startPhysicalInspection();
        prepareCpuStressTest();
        prepareMemoryTest();
    }, [prepareCpuStressTest, prepareMemoryTest, startPhysicalInspection]);

    useEffect(() => {
        updateDiagnosticResult("storage", overallStorageResult);
    }, [overallStorageResult, updateDiagnosticResult]);

    useEffect(() => {
        if (cpuStressTest.status !== "Running" || cpuTimerRef.current !== null) return;
        cpuTimerRef.current = window.setInterval(() => {
            const current = cpuTestRef.current;
            if (current.status !== "Running") return;
            const nextElapsed = Math.min(current.elapsedSeconds + 1, current.durationSeconds);
            appendCpuStressReading(createCpuTemperatureReading(nextElapsed));
            if (nextElapsed >= current.durationSeconds) stopCpuStressTest("duration");
        }, 1000);
        return () => {
            if (cpuTimerRef.current !== null) {
                window.clearInterval(cpuTimerRef.current);
                cpuTimerRef.current = null;
            }
        };
    }, [appendCpuStressReading, cpuStressTest.status, stopCpuStressTest]);

    useEffect(() => {
        if (cpuMonitoringTimerRef.current !== null) return;
        cpuMonitoringTimerRef.current = window.setInterval(() => {
            advanceCpuMonitoring(cpuTestRef.current.status === "Running");
        }, 1000);
        return () => {
            if (cpuMonitoringTimerRef.current !== null) {
                window.clearInterval(cpuMonitoringTimerRef.current);
                cpuMonitoringTimerRef.current = null;
            }
        };
    }, [advanceCpuMonitoring]);

    useEffect(() => {
        if (memoryTest.status !== "Running" || memoryTimerRef.current !== null) return;
        memoryTimerRef.current = window.setInterval(() => {
            const current = memoryTestRef.current;
            if (current.status !== "Running") return;
            const nextElapsed = Math.min(current.elapsedSeconds + 1, current.selectedDurationSeconds);
            advanceMemoryTest(nextElapsed);
            if (nextElapsed >= current.selectedDurationSeconds) stopMemoryTest("duration");
        }, 1000);
        return () => {
            if (memoryTimerRef.current !== null) {
                window.clearInterval(memoryTimerRef.current);
                memoryTimerRef.current = null;
            }
        };
    }, [advanceMemoryTest, memoryTest.status, stopMemoryTest]);

    useEffect(() => {
        if (browserPerformanceTest.status !== "Running" || browserTimerRef.current !== null) return;
        browserTimerRef.current = window.setInterval(() => {
            const current = browserTestRef.current;
            if (current.status !== "Running") return;
            const durationSeconds = current.selectedDurationMinutes * 60;
            const nextElapsed = Math.min(current.elapsedSeconds + 1, durationSeconds);
            advanceBrowserPerformanceTest(nextElapsed);
        }, 1000);
        return () => {
            if (browserTimerRef.current !== null) {
                window.clearInterval(browserTimerRef.current);
                browserTimerRef.current = null;
            }
        };
    }, [advanceBrowserPerformanceTest, browserPerformanceTest.status]);

    useEffect(() => {
        if (!activeStorageTest) return;
        const drive = demoStorageDrives.find((item) => item.id === activeStorageTest.driveId);
        if (!drive) {
            setActiveStorageTest(null);
            return;
        }
        const driveId = activeStorageTest.driveId;
        const testId = activeStorageTest.testId;
        const durationSeconds = storageTestDefinitions.find((test) => test.id === testId)?.demoResult.durationSeconds ?? 5;
        let elapsedSeconds = Math.floor((activeStorageTest.progressPercent / 100) * durationSeconds);
        const timer = window.setInterval(() => {
            elapsedSeconds = Math.min(elapsedSeconds + 1, durationSeconds);
            const progressPercent = (elapsedSeconds / durationSeconds) * 100;
            if (elapsedSeconds >= durationSeconds) {
                window.clearInterval(timer);
                recordStorageTestResult(createStorageTestResult(testId, drive));
                setActiveStorageTest(null);
                return;
            }
            setActiveStorageTest({ driveId, testId, progressPercent });
        }, 1000);
        return () => window.clearInterval(timer);
    }, [activeStorageTest?.driveId, activeStorageTest?.testId, recordStorageTestResult, setActiveStorageTest]);

    useEffect(() => () => {
        if (simpleTestTimerRef.current !== null) window.clearTimeout(simpleTestTimerRef.current);
    }, []);

    const selectedDrive = selectedDiagnosticComponentId.startsWith("storage:")
        ? demoStorageDrives.find((drive) => `storage:${drive.id}` === selectedDiagnosticComponentId) ?? null
        : null;
    const selectedKind: DiagnosticComponentKind = selectedDrive
        ? "storage"
        : selectedDiagnosticComponentId as DiagnosticComponentKind;
    const selectedItem = navigationGroups
        .flatMap((group) => group.items)
        .find((item) => item.id === selectedDiagnosticComponentId)
        ?? navigationGroups[0].items[0];
    const selectedDefinition = selectedKind === "storage" || selectedKind === "browser-performance"
        ? undefined
        : findDefinition(selectedKind);
    const selectedStorageResults = selectedDrive ? storageTestResults[selectedDrive.id] ?? {} : {};
    const selectedStorageMethod = storageTestDefinitions.find(({ id }) => id === selectedStorageTestId)
        ?? storageTestDefinitions[0];
    const selectedStorageResult = selectedStorageResults[selectedStorageMethod.id];
    const cpuRemainingSeconds = Math.max(cpuStressTest.durationSeconds - cpuStressTest.elapsedSeconds, 0);
    const cpuProgress = (cpuStressTest.elapsedSeconds / cpuStressTest.durationSeconds) * 100;
    const memoryRemainingSeconds = Math.max(memoryTest.selectedDurationSeconds - memoryTest.elapsedSeconds, 0);
    const memoryProgress = (memoryTest.elapsedSeconds / memoryTest.selectedDurationSeconds) * 100;
    const browserDurationSeconds = browserPerformanceTest.selectedDurationMinutes * 60;
    const browserRemainingSeconds = Math.max(browserDurationSeconds - browserPerformanceTest.elapsedSeconds, 0);
    const browserProgress = (browserPerformanceTest.elapsedSeconds / browserDurationSeconds) * 100;
    const cpuMonitoringReadings: CpuMonitoringReading[] = cpuMonitoring.readings;
    const latestCpuMonitoringReading = cpuMonitoringReadings[cpuMonitoringReadings.length - 1] ?? null;
    const averageCpuFrequencyGhz = useMemo(() => {
        const frequencies = cpuMonitoringReadings.flatMap((reading) =>
            reading.currentFrequencyGhz === null ? [] : [reading.currentFrequencyGhz]);
        return frequencies.length > 0
            ? frequencies.reduce((total, frequency) => total + frequency, 0) / frequencies.length
            : null;
    }, [cpuMonitoringReadings]);

    useEffect(() => {
        if (selectedKind !== "memory" && memoryTest.status !== "Running") return;
        const timer = window.setInterval(() => {
            advanceMemoryMonitoring(memoryTestRef.current.status === "Running");
        }, 1000);
        return () => window.clearInterval(timer);
    }, [advanceMemoryMonitoring, memoryTest.status, selectedKind]);

    useEffect(() => {
        const hasActiveStorageTest = activeStorageTest !== null;
        if (selectedKind !== "storage" && !hasActiveStorageTest) return;
        const timer = window.setInterval(() => {
            const activeTest = activeStorageTestRef.current;
            const driveIds = new Set<string>();
            if (selectedKind === "storage" && selectedDrive) driveIds.add(selectedDrive.id);
            if (activeTest) driveIds.add(activeTest.driveId);
            driveIds.forEach((driveId) => {
                advanceStorageMonitoring(
                    driveId,
                    activeTest?.driveId === driveId ? activeTest : null,
                );
            });
        }, 1000);
        return () => window.clearInterval(timer);
    }, [activeStorageTest !== null, advanceStorageMonitoring, selectedDrive?.id, selectedKind]);

    function getStorageTestStatus(drive: DemoStorageDrive, testId: StorageTestId): WorkspaceStatus {
        const key = getStorageTestKey(drive.id, testId);
        if (skippedDiagnosticTests[key]) return "Skipped";
        if (activeStorageTest?.driveId === drive.id && activeStorageTest.testId === testId) return "In Progress";
        const result = storageTestResults[drive.id]?.[testId];
        return result ? statusFromDiagnostic(result.status) : "Pending";
    }

    function getDriveStatus(drive: DemoStorageDrive): WorkspaceStatus {
        const statuses = storageTestDefinitions.map(({ id }) => getStorageTestStatus(drive, id));
        if (activeStorageTest?.driveId === drive.id) return "In Progress";
        if (statuses.every((status) => status === "Skipped")) return "Skipped";
        const results = storageTestResults[drive.id] ?? {};
        if (Object.keys(results).length === 0) {
            return statuses.some((status) => status === "Skipped") ? "Pending" : "Ready";
        }
        return statusFromDiagnostic(createStorageDiagnosticResult(drive, results).status);
    }

    function getItemStatus(item: DiagnosticComponentItem): WorkspaceStatus {
        switch (item.kind) {
            case "cpu":
                if (skippedDiagnosticTests.cpu) return "Skipped";
                if (cpuStressTest.status === "Running") return "In Progress";
                if (cpuStressTest.status === "Finalized") {
                    return statusFromDiagnostic(cpuStressTest.finalResult?.status ?? diagnosticResults.cpu.status);
                }
                return "Ready";
            case "memory":
                if (skippedDiagnosticTests.memory) return "Skipped";
                if (memoryTest.status === "Running") return "In Progress";
                if (memoryTest.status === "Finalized") {
                    return statusFromDiagnostic(memoryTest.finalResult?.status ?? diagnosticResults.memory.status);
                }
                return "Ready";
            case "storage": {
                const drive = demoStorageDrives.find((candidate) => `storage:${candidate.id}` === item.id);
                return drive ? getDriveStatus(drive) : "Unsupported";
            }
            case "browser-performance":
                if (skippedDiagnosticTests["browser-performance"]) return "Skipped";
                if (browserPerformanceTest.status === "Running") return "In Progress";
                return browserPerformanceTest.finalResult ? "Completed" : "Ready";
            default: {
                if (skippedDiagnosticTests[item.kind]) return "Skipped";
                if (runningDiagnosticId === item.kind) return "In Progress";
                const result = diagnosticResults[item.kind as DiagnosticId];
                if (result.status === "NOT RUN" && findDefinition(item.kind as DiagnosticId)?.simulatedResult) {
                    return "Ready";
                }
                return statusFromDiagnostic(result.status);
            }
        }
    }

    const diagnosticTestStatuses: DiagnosticTestStatus[] = [
        {
            name: "CPU stress test",
            status: getItemStatus({ id: "cpu", title: "CPU", kind: "cpu" }),
            skipRecord: skippedDiagnosticTests.cpu,
        },
        {
            name: "Memory diagnostic",
            status: getItemStatus({ id: "memory", title: "Memory (RAM)", kind: "memory" }),
            skipRecord: skippedDiagnosticTests.memory,
        },
        ...demoStorageDrives.flatMap((drive, index) =>
            storageTestDefinitions.map((test) => ({
                name: `Drive ${index + 1} · ${test.name}`,
                status: getStorageTestStatus(drive, test.id),
                skipRecord: skippedDiagnosticTests[getStorageTestKey(drive.id, test.id)],
            })),
        ),
        {
            name: "Battery assessment",
            status: getItemStatus({ id: "battery", title: "Battery", kind: "battery" }),
            skipRecord: skippedDiagnosticTests.battery,
        },
        {
            name: "Network adapter check",
            status: getItemStatus({ id: "network", title: "Network", kind: "network" }),
            skipRecord: skippedDiagnosticTests.network,
        },
        {
            name: "Browser Performance benchmark",
            status: getItemStatus({
                id: "browser-performance",
                title: "Browser Performance",
                kind: "browser-performance",
                optional: true,
            }),
            optional: true,
            skipRecord: skippedDiagnosticTests["browser-performance"],
        },
    ];
    const requiredStatuses = diagnosticTestStatuses
        .filter((test) => !test.optional)
        .map((test) => test.status);
    const summaryStatuses = diagnosticTestStatuses.map((test) => test.status);
    const completedCount = summaryStatuses.filter((status) => terminalStatuses.includes(status)).length;
    const passedCount = summaryStatuses.filter((status) => status === "Passed").length;
    const failedCount = summaryStatuses.filter((status) => status === "Failed").length;
    const warningCount = summaryStatuses.filter((status) => status === "Warning").length;
    const skippedCount = summaryStatuses.filter((status) => status === "Skipped").length;
    const inProgressCount = summaryStatuses.filter((status) => status === "In Progress").length;
    const pendingCount = summaryStatuses.filter((status) => status === "Pending" || status === "Ready").length;
    const inconclusiveCount = summaryStatuses.filter((status) => status === "Inconclusive").length;
    const unsupportedCount = summaryStatuses.filter((status) => status === "Unsupported").length;
    const cancelledCount = summaryStatuses.filter((status) => status === "Cancelled").length;
    const skippedTestStatuses = diagnosticTestStatuses.filter((test) => test.status === "Skipped");
    const diagnosticsComplete = requiredStatuses.every((status) =>
        !["Pending", "Ready", "In Progress"].includes(status),
    );
    const pendingItemTitles = diagnosticTestStatuses
        .filter((test) => !test.optional && ["Pending", "Ready"].includes(test.status))
        .map((test) => test.name);
    const continueMessage = diagnosticsComplete
        ? `Required diagnostics have been handled. ${skippedCount} test${skippedCount === 1 ? "" : "s"} skipped; optional Browser Performance does not block continuation.`
        : pendingItemTitles.length > 0
            ? `Complete or explicitly resolve: ${pendingItemTitles.join(", ")}.`
            : "Finalize running or stopped tests before continuing.";

    function selectComponent(id: DiagnosticWorkspaceId) {
        setSelectedDiagnosticComponentId(id);
        setMobileComponentId(id);
    }

    function runSimpleDiagnostic(id: "battery" | "network") {
        const definition = findDefinition(id);
        if (!definition?.simulatedResult || runningDiagnosticId !== null || skippedDiagnosticTests[id]) return;
        setRunningDiagnosticId(id);
        simpleTestTimerRef.current = window.setTimeout(() => {
            updateDiagnosticResult(id, definition.simulatedResult);
            setRunningDiagnosticId(null);
            simpleTestTimerRef.current = null;
        }, 700);
    }

    function finalizeCpuTest() {
        if (cpuStressTest.status === "Running" || cpuStressTest.status === "Finalized" || skippedDiagnosticTests.cpu) return;
        finalizeCpuStressTest(createCpuStressTestResult(cpuStressTest));
    }

    function finalizeCurrentMemoryTest() {
        if (memoryTest.status === "Running" || memoryTest.status === "Finalized" || skippedDiagnosticTests.memory) return;
        commitMemoryTestResult(createMemoryTestResult(memoryTest));
    }

    function openSkipConfirmation(target: SkipTarget) {
        setSkipReason("");
        setSkipNote("");
        setSkipTarget(target);
    }

    function closeSkipConfirmation() {
        setSkipTarget(null);
        setSkipReason("");
        setSkipNote("");
    }

    function skipTargetHasResult(target: SkipTarget) {
        switch (target.kind) {
            case "cpu":
                return cpuStressTest.status === "Finalized" || cpuStressTest.finalResult !== null;
            case "memory":
                return memoryTest.status === "Finalized" || memoryTest.finalResult !== null;
            case "storage":
                return Boolean(storageTestResults[target.driveId]?.[target.testId]);
            case "diagnostic":
                return diagnosticResults[target.diagnosticId].status !== "NOT RUN";
            case "browser-performance":
                return browserPerformanceTest.finalResult !== null;
        }
    }

    function confirmSkipTest() {
        if (!skipTarget) return;
        if (skippedDiagnosticTests[skipTarget.key] || skipTargetHasResult(skipTarget)) {
            closeSkipConfirmation();
            return;
        }

        switch (skipTarget.kind) {
            case "cpu":
                if (cpuStressTest.status === "Running") stopCpuStressTest("manual");
                break;
            case "memory":
                if (memoryTest.status === "Running") stopMemoryTest("manual");
                break;
            case "storage":
                if (activeStorageTest?.driveId === skipTarget.driveId
                    && activeStorageTest.testId === skipTarget.testId) {
                    setActiveStorageTest(null);
                }
                break;
            case "diagnostic":
                if (runningDiagnosticId === skipTarget.diagnosticId) {
                    if (simpleTestTimerRef.current !== null) {
                        window.clearTimeout(simpleTestTimerRef.current);
                        simpleTestTimerRef.current = null;
                    }
                    setRunningDiagnosticId(null);
                }
                break;
            case "browser-performance":
                if (browserPerformanceTest.status === "Running") stopBrowserPerformanceTest(false);
                break;
        }

        const note = skipReason === "Other" ? skipNote.trim() : "";
        skipDiagnosticTest(skipTarget.key, skipReason || null, note || undefined);
        closeSkipConfirmation();
    }

    function startSelectedStorageTest() {
        if (!selectedDrive
            || activeStorageTest !== null
            || selectedStorageResults[selectedStorageMethod.id]
            || skippedDiagnosticTests[getStorageTestKey(selectedDrive.id, selectedStorageMethod.id)]) return;
        setActiveStorageTest({
            driveId: selectedDrive.id,
            testId: selectedStorageMethod.id,
            progressPercent: 0,
        });
    }

    function stopSelectedStorageTest() {
        if (!activeStorageTest) return;
        const drive = demoStorageDrives.find((item) => item.id === activeStorageTest.driveId);
        if (!drive) return;
        const result = createStorageTestResult(activeStorageTest.testId, drive);
        recordStorageTestResult({
            ...result,
            status: "CANCELLED",
            summary: `The simulated ${result.testName} was stopped at ${activeStorageTest.progressPercent}% progress; no drive was accessed.`,
            measurements: [
                ...result.measurements,
                { label: "Progress at stop", value: `${activeStorageTest.progressPercent}% (demo)` },
            ],
            observations: [
                ...result.observations,
                "The test was cancelled before its simulated progress completed.",
            ],
        });
        setActiveStorageTest(null);
    }

    function toggleBrowserBenchmark(benchmarkId: BrowserBenchmarkId) {
        const selected = new Set(browserPerformanceTest.selectedBenchmarks);
        if (selected.has(benchmarkId)) selected.delete(benchmarkId);
        else selected.add(benchmarkId);
        setBrowserPerformanceBenchmarks([...selected]);
    }

    function renderCpuPanel() {
        const processor = demoDevice.processor;
        const isRunning = cpuStressTest.status === "Running";
        const result = cpuStressTest.finalResult;
        const overallUtilisation = latestCpuMonitoringReading?.overallUtilisationPercent;
        const currentFrequency = latestCpuMonitoringReading?.currentFrequencyGhz ?? null;
        const currentTemperature = latestCpuMonitoringReading?.packageTemperatureC ?? null;
        const hasCpuTemperature = currentTemperature !== null;
        return (
            <div className="space-y-5">
                <section className="space-y-4 rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="cpu-hardware-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="cpu-hardware-title">CPU Monitoring</h3>
                            <p className="mt-1 text-sm font-medium text-foreground">
                                {processor.manufacturer} {processor.model}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                                {processor.physicalCores} physical cores · {processor.logicalThreads} logical processors · Current frequency: {currentFrequency === null ? "Not available" : `${currentFrequency.toFixed(2)} GHz (simulated)`}
                            </p>
                        </div>
                        <StatusIndicator status={getItemStatus({ id: "cpu", title: "CPU", kind: "cpu" })} />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Overall CPU activity">
                        <div className="rounded-sm border border-border bg-muted/40 p-3">
                            <span className="block text-xs text-muted-foreground">Overall usage</span>
                            <strong className="mt-1 block text-xl tabular-nums text-foreground">
                                {overallUtilisation === null || overallUtilisation === undefined ? "Not available" : `${overallUtilisation.toFixed(1)}%`}
                            </strong>
                            <span className="text-[11px] text-muted-foreground">Mean across {processor.logicalThreads} logical processors</span>
                        </div>
                        <div className="rounded-sm border border-border bg-muted/40 p-3">
                            <span className="block text-xs text-muted-foreground">Average frequency</span>
                            <strong className="mt-1 block text-xl tabular-nums text-foreground">
                                {averageCpuFrequencyGhz === null ? "Not available" : `${averageCpuFrequencyGhz.toFixed(2)} GHz`}
                            </strong>
                            <span className="text-[11px] text-muted-foreground">Recent simulated samples</span>
                        </div>
                        <div className="rounded-sm border border-border bg-muted/40 p-3">
                            <span className="block text-xs text-muted-foreground">Current CPU frequency</span>
                            <strong className="mt-1 block text-xl tabular-nums text-foreground">
                                {currentFrequency === null ? "Not available" : `${currentFrequency.toFixed(2)} GHz`}
                            </strong>
                            <span className="text-[11px] text-muted-foreground">Simulated demo value</span>
                        </div>
                        <div className="rounded-sm border border-border bg-muted/40 p-3">
                            <span className="block text-xs text-muted-foreground">CPU package temperature</span>
                            <strong className="mt-1 block text-xl tabular-nums text-foreground">
                                {hasCpuTemperature ? `${currentTemperature.toFixed(1)} °C` : "CPU temperature unavailable"}
                            </strong>
                            <span className="text-[11px] text-muted-foreground">Simulated demo value</span>
                        </div>
                    </div>
                    <p className="m-0 text-xs leading-5 text-muted-foreground">
                        Monitoring values are simulated demo data, not hardware measurements. Per-thread utilisation is averaged for overall usage; monitoring does not determine the CPU test result.
                    </p>
                </section>

                <Suspense fallback={<div className="rounded-md border border-border bg-card p-4 text-sm text-muted-foreground" role="status">Loading CPU monitoring charts…</div>}>
                    <CpuMonitoringCharts
                        readings={cpuMonitoringReadings}
                        logicalThreadCount={processor.logicalThreads}
                        minimumPackageTemperatureC={cpuMonitoring.minimumPackageTemperatureC}
                        maximumPackageTemperatureC={cpuMonitoring.maximumPackageTemperatureC}
                    />
                </Suspense>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="cpu-test-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="cpu-test-title">CPU Stress Test</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Simulates a bounded test sequence. No processor load or real sensor readings are generated.
                            </p>
                        </div>
                        <StatusIndicator status={getItemStatus({ id: "cpu", title: "CPU", kind: "cpu" })} />
                    </div>
                    <label className="mb-4 block max-w-xs text-xs font-semibold text-foreground" htmlFor="cpu-duration">
                        Test duration
                        <select id="cpu-duration" className="hardware-diagnostics-input mt-1 w-full" value={cpuStressTest.durationSeconds} disabled>
                            <option value={cpuStressTestDurationSeconds}>5 minutes (demo duration)</option>
                        </select>
                    </label>
                    <div className="grid gap-3 sm:grid-cols-3">
                        {[
                            ["Configured duration", formatDuration(cpuStressTest.durationSeconds)],
                            ["Elapsed time", formatDuration(cpuStressTest.elapsedSeconds)],
                            ["Remaining time", formatDuration(cpuRemainingSeconds)],
                        ].map(([label, value]) => (
                            <div className="rounded-sm border border-border bg-muted/40 p-3" key={label}>
                                <span className="block text-xs text-muted-foreground">{label}</span>
                                <strong className="mt-1 block text-sm tabular-nums text-foreground">{value}</strong>
                            </div>
                        ))}
                    </div>
                    <div className="mt-4">
                        <ProgressBar label="Elapsed test time" value={cpuProgress} />
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                        <button className="button button-primary" type="button" disabled={!["Ready", "Not Started"].includes(cpuStressTest.status) || Boolean(skippedDiagnosticTests.cpu)} onClick={startCpuStressTest}>
                            Start Test
                        </button>
                        <button className="button button-secondary" type="button" disabled={!isRunning || Boolean(skippedDiagnosticTests.cpu)} onClick={() => stopCpuStressTest("manual")}>
                            Stop Test
                        </button>
                        <button className="button button-secondary" type="button" disabled={cpuStressTest.status === "Finalized" || isRunning || Boolean(skippedDiagnosticTests.cpu)} onClick={finalizeCpuTest}>
                            Finalize Test
                        </button>
                        {!cpuStressTest.finalResult && cpuStressTest.status !== "Finalized" && !skippedDiagnosticTests.cpu && (
                            <button
                                className="button button-secondary"
                                type="button"
                                onClick={() => openSkipConfirmation({ key: "cpu", name: "CPU Stress Test", kind: "cpu" })}
                            >
                                Skip Test
                            </button>
                        )}
                    </div>
                    {skippedDiagnosticTests.cpu && <SkippedTestNotice record={skippedDiagnosticTests.cpu} />}
                    {result && <div className="mt-4"><ResultPanel result={result} /></div>}
                    <p className="mt-3 text-xs text-muted-foreground">
                        Manually stopped tests are recorded as cancelled, not passed.
                    </p>
                </section>
            </div>
        );
    }

    function renderMemoryPanel() {
        const modules = demoDevice.memory.modules;
        const occupiedSlots = modules.map((module) => module.slot).filter(Boolean).length;
        const moduleTypes = [...new Set(modules.map((module) => module.type))].join(", ") || "Not available";
        const isRunning = memoryTest.status === "Running";
        const result = memoryTest.finalResult;
        const currentReading = memoryMonitoring.readings[memoryMonitoring.readings.length - 1];
        const usedPercent = currentReading && memoryMonitoring.totalGb > 0
            ? (currentReading.usedGb / memoryMonitoring.totalGb) * 100
            : 0;
        const memoryBreakdown = currentReading
            ? [
                { label: "Used", value: currentReading.usedGb, className: "bg-primary" },
                { label: "Free", value: currentReading.freeGb, className: "bg-information" },
                { label: "Cached", value: currentReading.cachedGb, className: "bg-success" },
                { label: "Buffered", value: currentReading.bufferedGb, className: "bg-warning" },
            ]
            : [];
        return (
            <div className="space-y-5">
                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="memory-monitoring-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="memory-monitoring-title">Memory Monitoring</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Simulated system-wide readings; memory totals remain fixed at {formatMemorySize(memoryMonitoring.totalGb)}.
                            </p>
                        </div>
                        <span className="text-xs font-semibold text-information">DEMO MONITORING</span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                        {[
                            ["Total installed", formatMemorySize(memoryMonitoring.totalGb)],
                            ["Used", currentReading ? formatMemorySize(currentReading.usedGb) : "Unavailable"],
                            ["Available", currentReading ? formatMemorySize(currentReading.availableGb) : "Unavailable"],
                            ["Free", currentReading ? formatMemorySize(currentReading.freeGb) : "Unavailable"],
                            ["Cached", currentReading ? formatMemorySize(currentReading.cachedGb) : "Unavailable"],
                            ["Buffered", currentReading ? formatMemorySize(currentReading.bufferedGb) : "Unavailable"],
                        ].map(([label, value]) => (
                            <div className="rounded-sm border border-border bg-muted/40 p-3" key={label}>
                                <span className="block text-xs text-muted-foreground">{label}</span>
                                <strong className="mt-1 block text-sm tabular-nums text-foreground">{value}</strong>
                            </div>
                        ))}
                    </div>
                    <div className="mt-4 rounded-sm border border-border bg-background p-3">
                        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                            <h4 className="text-xs font-bold text-foreground">RAM usage history</h4>
                            <div className="flex items-center gap-3 text-[11px] text-muted-foreground" aria-label="Chart legend">
                                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-primary" aria-hidden="true" />Used</span>
                                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-information" aria-hidden="true" />Available</span>
                            </div>
                        </div>
                        <Suspense fallback={<div className="h-56" aria-label="Loading memory chart" />}>
                            <MemoryStorageMonitoringCharts
                                kind="memory"
                                totalGb={memoryMonitoring.totalGb}
                                readings={memoryMonitoring.readings}
                            />
                        </Suspense>
                        <div className="mt-2">
                            <ProgressBar label="Current RAM usage" value={usedPercent} />
                        </div>
                    </div>
                    <div className="mt-4">
                        <h4 className="mb-2 text-xs font-bold text-foreground">Memory breakdown</h4>
                        <div className="flex h-3 overflow-hidden rounded-sm bg-muted" role="img" aria-label="Memory breakdown by used, free, cached and buffered memory">
                            {memoryBreakdown.map((part) => (
                                <div
                                    className={part.className}
                                    key={part.label}
                                    style={{ width: memoryMonitoring.totalGb > 0 ? `${(part.value / memoryMonitoring.totalGb) * 100}%` : "0%" }}
                                    title={`${part.label}: ${formatMemorySize(part.value)}`}
                                />
                            ))}
                        </div>
                        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                            {memoryBreakdown.map((part) => (
                                <div className="flex min-w-0 items-center gap-2 text-xs" key={part.label}>
                                    <span className={`h-2.5 w-2.5 shrink-0 rounded-sm ${part.className}`} aria-hidden="true" />
                                    <span className="text-muted-foreground">{part.label}</span>
                                    <strong className="ml-auto tabular-nums text-foreground">{formatMemorySize(part.value)}</strong>
                                </div>
                            ))}
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">
                            Available memory is free + cached + buffered; cached and buffered are breakdowns of available memory, not additional capacity.
                        </p>
                    </div>
                    <section className="mt-4 border-t border-border pt-4" aria-labelledby="memory-swap-title">
                        <h4 className="text-xs font-bold text-foreground" id="memory-swap-title">Swap</h4>
                        {memoryMonitoring.swap === null
                            ? <p className="mt-2 text-sm text-muted-foreground">Swap not configured or unavailable</p>
                            : <p className="mt-2 text-sm text-muted-foreground">Swap readings unavailable</p>}
                    </section>
                </section>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="memory-hardware-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="memory-hardware-title">Installed memory</h3>
                            <p className="mt-1 text-sm text-muted-foreground">Specifications from the demo device inventory.</p>
                        </div>
                        <StatusIndicator status={getItemStatus({ id: "memory", title: "Memory (RAM)", kind: "memory" })} />
                    </div>
                    <DetailsList details={[
                        { label: "Total installed RAM", value: `${getTotalInstalledRamGb(demoDevice)} GB` },
                        { label: "Memory type", value: moduleTypes },
                        { label: "Occupied slots", value: String(occupiedSlots) },
                        { label: "Available slots", value: "Not available in demo inventory" },
                        { label: "Memory temperature", value: memoryTemperatureSensorAvailable ? "Sensor available" : "Memory temperature unavailable" },
                    ]} />
                    <div className="mt-4 divide-y divide-border border-y border-border">
                        {modules.map((module, index) => (
                            <div className="grid gap-1 py-3 sm:grid-cols-4 sm:gap-3" key={`${module.slot}-${index}`}>
                                <strong className="text-sm text-foreground">Module {index + 1} · {module.slot}</strong>
                                <span className="text-xs text-muted-foreground">{module.capacityGb} GB · {module.type}</span>
                                <span className="text-xs text-muted-foreground">{module.speedMts === null ? "Speed not available" : `${module.speedMts} MT/s`}</span>
                                <span className="text-xs text-muted-foreground">Manufacturer: Not available · Detected</span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="memory-test-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="memory-test-title">Memory Test</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Simulated progress reflects elapsed time only, not memory coverage.
                            </p>
                        </div>
                        <StatusIndicator status={getItemStatus({ id: "memory", title: "Memory (RAM)", kind: "memory" })} />
                    </div>
                    <fieldset className="border-0 p-0" disabled={!["Ready", "Not Started"].includes(memoryTest.status) || Boolean(skippedDiagnosticTests.memory)}>
                        <legend className="mb-2 text-xs font-semibold text-foreground">Test duration</legend>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                            {memoryTestDurations.map((duration) => (
                                <label className="hardware-diagnostics-choice" key={duration.seconds}>
                                    <input
                                        type="radio"
                                        name="hardware-memory-duration"
                                        value={duration.seconds}
                                        checked={memoryTest.selectedDurationSeconds === duration.seconds}
                                        onChange={() => selectMemoryTestDuration(duration.seconds)}
                                    />
                                    <span>{duration.label}</span>
                                </label>
                            ))}
                        </div>
                    </fieldset>
                    <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-foreground">
                        <input
                            type="checkbox"
                            className="mt-1 accent-primary"
                            checked={memoryTest.durationConfirmed}
                            disabled={memoryTest.status !== "Ready" || Boolean(skippedDiagnosticTests.memory)}
                            onChange={(event) => {
                                if (event.target.checked) confirmMemoryTestDuration();
                                else selectMemoryTestDuration(memoryTest.selectedDurationSeconds);
                            }}
                        />
                        <span>Confirm the selected duration before starting this simulated test.</span>
                    </label>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {[
                            ["Elapsed", formatDuration(memoryTest.elapsedSeconds)],
                            ["Remaining", formatDuration(memoryRemainingSeconds)],
                            ["Memory tested", `${getTotalInstalledRamGb(demoDevice)} GB (demo inventory)`],
                            ["Errors detected", memoryTest.errorsDetected === null ? "Not evaluated" : `${memoryTest.errorsDetected} (demo)`],
                        ].map(([label, value]) => (
                            <div className="rounded-sm border border-border bg-muted/40 p-3" key={label}>
                                <span className="block text-xs text-muted-foreground">{label}</span>
                                <strong className="mt-1 block text-sm tabular-nums text-foreground">{value}</strong>
                            </div>
                        ))}
                    </div>
                    <div className="mt-4">
                        <ProgressBar label="Elapsed-time progress (not memory coverage)" value={memoryProgress} />
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                        Memory temperature unavailable. CPU temperature is not used as a substitute.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
                        <button className="button button-primary" type="button" disabled={memoryTest.status !== "Ready" || !memoryTest.durationConfirmed || Boolean(skippedDiagnosticTests.memory)} onClick={startMemoryTest}>
                            Start Test
                        </button>
                        <button className="button button-secondary" type="button" disabled={!isRunning || Boolean(skippedDiagnosticTests.memory)} onClick={() => stopMemoryTest("manual")}>
                            Stop Test
                        </button>
                        <button className="button button-secondary" type="button" disabled={memoryTest.status === "Finalized" || isRunning || Boolean(skippedDiagnosticTests.memory)} onClick={finalizeCurrentMemoryTest}>
                            Finalize Test
                        </button>
                        {!memoryTest.finalResult && memoryTest.status !== "Finalized" && !skippedDiagnosticTests.memory && (
                            <button
                                className="button button-secondary"
                                type="button"
                                onClick={() => openSkipConfirmation({ key: "memory", name: "Memory Diagnostic", kind: "memory" })}
                            >
                                Skip Test
                            </button>
                        )}
                    </div>
                    {skippedDiagnosticTests.memory && <SkippedTestNotice record={skippedDiagnosticTests.memory} />}
                    {result && <div className="mt-4"><ResultPanel result={result} /></div>}
                    <p className="mt-3 text-xs text-muted-foreground">
                        Stopping early records an incomplete result; it is not shown as a pass.
                    </p>
                </section>
            </div>
        );
    }

    function renderStoragePanel() {
        if (!selectedDrive) {
            return (
                <section className="rounded-md border border-border bg-card p-4 sm:p-5">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground">Physical storage</h3>
                            <p className="mt-1 text-sm text-muted-foreground">No physical drives are available in the demo inventory.</p>
                        </div>
                        <StatusIndicator status="Unsupported" />
                    </div>
                    <p className="m-0 text-sm leading-6 text-muted-foreground">
                        Storage tests cannot be run without a listed drive. No storage device was accessed.
                    </p>
                </section>
            );
        }
        const activeTestIsSelectedDrive = activeStorageTest?.driveId === selectedDrive.id;
        const activeMethod = activeStorageTest
            ? storageTestDefinitions.find((test) => test.id === activeStorageTest.testId)
            : undefined;
        const manufacturer = selectedDrive.model.split(/\s+/)[0] || "Not available";
        const storageResult = createStorageDiagnosticResult(selectedDrive, selectedStorageResults);
        const skippedStorageCount = storageTestDefinitions.filter((test) =>
            skippedDiagnosticTests[getStorageTestKey(selectedDrive.id, test.id)],
        ).length;
        const selectedStorageSkip = skippedDiagnosticTests[getStorageTestKey(selectedDrive.id, selectedStorageMethod.id)];
        const driveMonitoring = storageMonitoring[selectedDrive.id];
        const currentDriveReading = driveMonitoring?.readings[driveMonitoring.readings.length - 1] ?? null;
        const selectedMethodIsWriteRelated = selectedStorageMethod.id === "file-copy-verification"
            || selectedStorageMethod.id === "write-read-back";
        return (
            <div className="space-y-5">
                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="drive-information-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="drive-information-title">
                                {selectedItem.title} — {selectedDrive.model}
                            </h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                This drive has independent results for each test method.
                            </p>
                        </div>
                        <StatusIndicator status={getDriveStatus(selectedDrive)} />
                    </div>
                    <DetailsList details={[
                        { label: "Model", value: selectedDrive.model },
                        { label: "Manufacturer", value: `${manufacturer} (inferred from demo model)` },
                        { label: "Serial number", value: selectedDrive.serialNumber ?? "Not available" },
                        { label: "Interface", value: selectedDrive.interface },
                        { label: "Capacity", value: formatCapacity(selectedDrive.capacityGb) },
                        { label: "Drive type", value: selectedDrive.type },
                        { label: "Firmware version", value: "Not available in demo inventory" },
                        { label: "Health information", value: selectedStorageResults["smart-health"] ? "See SMART Health result" : "Not available until SMART Health is run" },
                        { label: "Temperature", value: "Drive temperature unavailable" },
                    ]} />
                    <div className="mt-4 border-t border-border pt-3">
                        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <span className="text-muted-foreground">Drive summary</span>
                            <span className="font-semibold text-foreground">
                                {skippedStorageCount === storageTestDefinitions.length
                                    ? "All storage test methods were skipped."
                                    : skippedStorageCount > 0
                                        ? `${storageResult.summary} ${skippedStorageCount} method${skippedStorageCount === 1 ? "" : "s"} skipped.`
                                        : storageResult.summary}
                            </span>
                        </div>
                        <div className="mt-2">
                            <StatusIndicator status={getDriveStatus(selectedDrive)} />
                        </div>
                    </div>
                </section>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="drive-monitoring-title">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="drive-monitoring-title">Drive Activity</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Simulated readings and history for {selectedDrive.model} only.
                            </p>
                        </div>
                        <span className="text-xs font-semibold text-information">DEMO MONITORING</span>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                        {[
                            ["Read speed", currentDriveReading ? `${currentDriveReading.readMBps.toFixed(1)} MB/s` : "Unavailable"],
                            ["Write speed", currentDriveReading ? `${currentDriveReading.writeMBps.toFixed(1)} MB/s` : "Unavailable"],
                            ["Active time", currentDriveReading?.activeTimePercent === null || !currentDriveReading ? "Unavailable" : `${currentDriveReading.activeTimePercent}%`],
                            ["Queue depth", currentDriveReading?.queueDepth === null || !currentDriveReading ? "Unavailable" : String(currentDriveReading.queueDepth)],
                            ["Read IOPS", currentDriveReading?.readIops === null || !currentDriveReading ? "Unavailable" : String(currentDriveReading.readIops)],
                            ["Write IOPS", currentDriveReading?.writeIops === null || !currentDriveReading ? "Unavailable" : String(currentDriveReading.writeIops)],
                        ].map(([label, value]) => (
                            <div className="rounded-sm border border-border bg-muted/40 p-3" key={label}>
                                <span className="block text-xs text-muted-foreground">{label}</span>
                                <strong className="mt-1 block text-sm tabular-nums text-foreground">{value}</strong>
                            </div>
                        ))}
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                        Active time, queue depth and IOPS are unavailable in the demo inventory; no unsupported values are substituted.
                    </p>
                    <div className="mt-4">
                        <Suspense fallback={<div className="h-56" aria-label="Loading drive charts" />}>
                            <MemoryStorageMonitoringCharts
                                kind="storage"
                                readings={driveMonitoring?.readings ?? []}
                            />
                        </Suspense>
                    </div>
                    <section className="mt-4 border-t border-border pt-4" aria-labelledby="drive-temperature-title">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <h4 className="text-xs font-bold text-foreground" id="drive-temperature-title">Drive temperature</h4>
                            <span className="text-xs text-muted-foreground">Current / minimum / maximum: unavailable</span>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">Drive temperature unavailable</p>
                    </section>
                    <p className="mt-3 text-xs text-muted-foreground">
                        Read and write throughput are simulated and remain separate from this drive’s test results.
                    </p>
                </section>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="storage-methods-title">
                    <div className="mb-4">
                        <h3 className="m-0 text-base font-bold text-foreground" id="storage-methods-title">Storage test methods</h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Each method result is saved separately for {selectedDrive.model}. One passing method does not pass the drive.
                        </p>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                        {storageTestDefinitions.map((test) => {
                            const result = selectedStorageResults[test.id];
                            const isSelected = selectedStorageTestId === test.id;
                            const isRunning = activeTestIsSelectedDrive && activeStorageTest?.testId === test.id;
                            const key = getStorageTestKey(selectedDrive.id, test.id);
                            const skipped = skippedDiagnosticTests[key];
                            const status = getStorageTestStatus(selectedDrive, test.id);
                            return (
                                <div className="flex min-w-0 items-stretch gap-2" key={test.id}>
                                    <button
                                        className={`hardware-diagnostics-method min-w-0 flex-1${isSelected ? " is-selected" : ""}`}
                                        type="button"
                                        aria-pressed={isSelected}
                                        disabled={activeStorageTest !== null}
                                        onClick={() => setSelectedStorageTestId(test.id)}
                                    >
                                        <span className="flex min-w-0 items-center justify-between gap-2">
                                            <strong className="text-left text-sm text-foreground">{test.name}</strong>
                                            <StatusIndicator status={status} />
                                        </span>
                                        <span className="mt-2 block text-left text-xs leading-5 text-muted-foreground">{test.purpose}</span>
                                        {skipped?.reason && (
                                            <span className="mt-2 block text-left text-[11px] text-muted-foreground">Reason: {skipped.reason}</span>
                                        )}
                                    </button>
                                    {!result && !skipped && !isRunning && (
                                        <button
                                            className="button button-secondary self-start px-2 py-1 text-xs"
                                            type="button"
                                            onClick={() => openSkipConfirmation({
                                                key,
                                                name: `${selectedDrive.model} · ${test.name}`,
                                                kind: "storage",
                                                driveId: selectedDrive.id,
                                                testId: test.id,
                                            })}
                                        >
                                            Skip Test
                                        </button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </section>

                <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-labelledby="selected-storage-method-title">
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground" id="selected-storage-method-title">
                                {selectedStorageMethod.name}
                            </h3>
                            <p className="mt-1 text-sm text-muted-foreground">{selectedStorageMethod.purpose}</p>
                        </div>
                        <span className="text-xs font-semibold text-information">SIMULATED TEST</span>
                    </div>
                    <p className="text-sm leading-6 text-foreground">{selectedStorageMethod.guidance}</p>
                    {selectedMethodIsWriteRelated && (
                        <p className="rounded-sm border border-warning/30 bg-warning/5 p-3 text-xs leading-5 text-foreground">
                            This method models a write/copy operation. Demo only: no files, partitions or physical drive data are written or changed.
                        </p>
                    )}
                    {activeStorageTest && (
                        <div className="mt-4 space-y-3">
                            <p className="text-sm font-medium text-foreground">
                                {activeMethod?.name ?? "Storage test"} is running for {demoStorageDrives.find((drive) => drive.id === activeStorageTest.driveId)?.model ?? "the selected drive"}.
                            </p>
                            <ProgressBar label={`${activeMethod?.name ?? "Storage test"} simulated progress`} value={activeStorageTest.progressPercent} />
                            <div className="flex flex-wrap gap-2">
                                <button className="button button-secondary" type="button" onClick={stopSelectedStorageTest}>Stop Test</button>
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    onClick={() => {
                                        const drive = demoStorageDrives.find((item) => item.id === activeStorageTest.driveId);
                                        const test = storageTestDefinitions.find((item) => item.id === activeStorageTest.testId);
                                        if (!drive || !test) return;
                                        openSkipConfirmation({
                                            key: getStorageTestKey(drive.id, test.id),
                                            name: `${drive.model} · ${test.name}`,
                                            kind: "storage",
                                            driveId: drive.id,
                                            testId: test.id,
                                        });
                                    }}
                                >
                                    Skip Test
                                </button>
                            </div>
                        </div>
                    )}
                    {!activeStorageTest && (
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                            <button
                                className="button button-primary"
                                type="button"
                                disabled={Boolean(selectedStorageResult || selectedStorageSkip)}
                                onClick={startSelectedStorageTest}
                            >
                                Run Selected Test
                            </button>
                            <span className="text-xs text-muted-foreground">
                                No real drive reads, writes, SMART queries or filesystem operations occur.
                            </span>
                        </div>
                    )}
                    {selectedStorageSkip && <SkippedTestNotice record={selectedStorageSkip} />}
                    {selectedStorageResult && (
                        <div className="mt-4">
                            <ResultPanel result={selectedStorageResult} />
                        </div>
                    )}
                </section>
            </div>
        );
    }

    function renderBrowserPerformancePanel() {
        const isRunning = browserPerformanceTest.status === "Running";
        const result = browserPerformanceTest.finalResult;
        const skipRecord = skippedDiagnosticTests["browser-performance"];
        return (
            <div className="space-y-5">
                <section className="rounded-md border border-border bg-card p-4 sm:p-5">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground">Browser Performance (optional)</h3>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Simulated benchmark scores only. No browser tabs or benchmark workloads are launched.
                            </p>
                        </div>
                        <StatusIndicator status={skipRecord ? "Skipped" : isRunning ? "In Progress" : result ? "Completed" : "Ready"} />
                    </div>
                    <div className="grid gap-4 lg:grid-cols-3">
                        <fieldset className="space-y-2 border-0 p-0" disabled={isRunning}>
                            <legend className="mb-2 text-sm font-semibold text-foreground">Benchmarks</legend>
                            {browserBenchmarkOptions.map((option) => (
                                <label className="hardware-diagnostics-choice" key={option.id}>
                                    <input
                                        type="checkbox"
                                        checked={browserPerformanceTest.selectedBenchmarks.includes(option.id)}
                                        onChange={() => toggleBrowserBenchmark(option.id)}
                                    />
                                    <span>
                                        <strong className="block text-xs">{option.label}</strong>
                                        <small className="mt-1 block text-xs text-muted-foreground">{option.description}</small>
                                    </span>
                                </label>
                            ))}
                        </fieldset>
                        <fieldset className="space-y-2 border-0 p-0" disabled={isRunning}>
                            <legend className="mb-2 text-sm font-semibold text-foreground">Simulated tab count</legend>
                            <div className="grid grid-cols-2 gap-2">
                                {browserTabCountOptions.map((count) => (
                                    <label className="hardware-diagnostics-choice" key={count}>
                                        <input
                                            type="radio"
                                            name="hardware-browser-tab-count"
                                            checked={browserPerformanceTest.selectedTabCount === count}
                                            onChange={() => setBrowserPerformanceTabCount(count)}
                                        />
                                        <span>{count} tabs (simulated)</span>
                                    </label>
                                ))}
                            </div>
                        </fieldset>
                        <fieldset className="space-y-2 border-0 p-0" disabled={isRunning}>
                            <legend className="mb-2 text-sm font-semibold text-foreground">Duration</legend>
                            <div className="grid grid-cols-1 gap-2">
                                {browserTestDurationOptions.map((minutes) => (
                                    <label className="hardware-diagnostics-choice" key={minutes}>
                                        <input
                                            type="radio"
                                            name="hardware-browser-duration"
                                            checked={browserPerformanceTest.selectedDurationMinutes === minutes}
                                            onChange={() => setBrowserPerformanceDuration(minutes)}
                                        />
                                        <span>{minutes} minutes</span>
                                    </label>
                                ))}
                            </div>
                        </fieldset>
                    </div>
                    <p className="mt-4 text-xs text-muted-foreground">
                        Optional benchmark results do not affect CPU or GPU diagnostic results and never block Continue.
                    </p>
                </section>

                {(isRunning || (result && !skipRecord)) && (
                    <section className="rounded-md border border-border bg-card p-4 sm:p-5" aria-live="polite">
                        <h3 className="mb-4 text-sm font-bold text-foreground">Benchmark progress and results</h3>
                        {isRunning && (
                            <div className="space-y-3">
                                <div className="flex justify-between gap-2 text-xs text-muted-foreground">
                                    <span>Elapsed {formatDuration(browserPerformanceTest.elapsedSeconds)}</span>
                                    <span>Remaining {formatDuration(browserRemainingSeconds)}</span>
                                </div>
                                <ProgressBar label="Simulated benchmark progress" value={browserProgress} />
                                <button className="button button-secondary" type="button" onClick={() => stopBrowserPerformanceTest()}>
                                    Stop Benchmark
                                </button>
                                {!skipRecord && (
                                    <button
                                        className="button button-secondary"
                                        type="button"
                                        onClick={() => openSkipConfirmation({
                                            key: "browser-performance",
                                            name: "Browser Performance Benchmark",
                                            kind: "browser-performance",
                                        })}
                                    >
                                        Skip Test
                                    </button>
                                )}
                            </div>
                        )}
                        {result && !skipRecord && (
                            <div className="mt-4">
                                <DetailsList details={[
                                    { label: "Overall result", value: result.overallResult },
                                    { label: "Web application score", value: result.webApplicationScore === null ? "Not selected" : `${result.webApplicationScore} / 100 (demo)` },
                                    { label: "JavaScript score", value: result.javascriptScore === null ? "Not selected" : `${result.javascriptScore} / 100 (demo)` },
                                    { label: "Graphics score", value: result.graphicsScore === null ? "Not selected" : `${result.graphicsScore} / 100 (demo)` },
                                    { label: "Multi-tab responsiveness", value: `${result.multiTabResponsiveness} / 100 (demo)` },
                                    { label: "Peak memory usage", value: `${result.peakMemoryUsageMb} MB (demo; not process memory)` },
                                    { label: "Browser crashes", value: `${result.browserCrashes} (not monitored)` },
                                ]} />
                            </div>
                        )}
                    </section>
                )}
                {skipRecord && <SkippedTestNotice record={skipRecord} />}
                <div className="flex flex-wrap items-center gap-2">
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={browserPerformanceTest.selectedBenchmarks.length === 0 || isRunning || Boolean(skipRecord)}
                        onClick={startBrowserPerformanceTest}
                    >
                        {result ? "Run Benchmark Again" : "Start Benchmark"}
                    </button>
                    {!isRunning && !result && !skipRecord && (
                        <button
                            className="button button-secondary"
                            type="button"
                            onClick={() => openSkipConfirmation({
                                key: "browser-performance",
                                name: "Browser Performance Benchmark",
                                kind: "browser-performance",
                            })}
                        >
                            Skip Test
                        </button>
                    )}
                    {browserPerformanceTest.selectedBenchmarks.length === 0 && (
                        <span className="text-xs text-muted-foreground">Select at least one benchmark to begin.</span>
                    )}
                </div>
            </div>
        );
    }

    function renderSensorsPanel() {
        return (
            <div className="space-y-4">
                <section className="rounded-md border border-border bg-card p-4 sm:p-5">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground">Sensor readings</h3>
                            <p className="mt-1 text-sm text-muted-foreground">Sample values only; not live measurements or a functional test.</p>
                        </div>
                        <StatusIndicator status={statusFromDiagnostic(diagnosticResults.sensors.status)} />
                    </div>
                    <div className="divide-y divide-border border-y border-border">
                        {demoSensors.map((sensor) => {
                            const value = sensor.readings?.at(-1);
                            return (
                                <div className="flex flex-wrap items-center justify-between gap-2 py-3" key={sensor.id}>
                                    <span className="text-sm font-medium text-foreground">{sensor.name}</span>
                                    <span className="text-sm tabular-nums text-muted-foreground">
                                        {value === undefined ? "Not available" : `${value} ${sensor.unit} (demo sample)`}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">
                        A reading being present does not mean the sensor or associated hardware passed a functional test.
                    </p>
                </section>
            </div>
        );
    }

    function renderGeneralPanel(id: "graphics" | "display" | "battery" | "network") {
        const definition = findDefinition(id);
        if (!definition) return null;
        const result = diagnosticResults[id];
        const isBattery = id === "battery";
        const isNetwork = id === "network";
        const extraDetails = isBattery
            ? [{ label: "Current charge", value: "Not available in demo inventory" }]
            : isNetwork
                ? [
                    { label: "Connection status", value: "Not tested" },
                    { label: "MAC address", value: "Not available in demo inventory" },
                    { label: "IP address", value: "Not available in demo inventory" },
                    { label: "Link speed", value: "Not available in demo inventory" },
                ]
                : id === "graphics"
                    ? [
                        { label: "Graphics memory", value: "Not available in demo inventory" },
                        { label: "Driver information", value: "Not available in demo inventory" },
                    ]
                    : [];
        const canRun = (isBattery || isNetwork)
            && result.status === "NOT RUN"
            && runningDiagnosticId === null
            && definition.simulatedResult !== null
            && !skippedDiagnosticTests[id];
        const skipRecord = skippedDiagnosticTests[id];
        const canSkip = (isBattery || isNetwork)
            && result.status === "NOT RUN"
            && !skipRecord;
        return (
            <div className="space-y-5">
                <section className="rounded-md border border-border bg-card p-4 sm:p-5">
                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h3 className="m-0 text-base font-bold text-foreground">{definition.testName}</h3>
                            <p className="mt-1 text-sm text-muted-foreground">{definition.hardwareName}</p>
                        </div>
                        <StatusIndicator status={runningDiagnosticId === id ? "In Progress" : getItemStatus({ id, title: definition.category, kind: id })} />
                    </div>
                    <DetailsList details={[...definition.hardwareDetails, ...extraDetails]} />
                    {isBattery && (
                        <p className="mt-4 rounded-sm border border-border bg-muted/50 p-3 text-sm text-foreground">
                            Battery sample information is separate from functional battery testing. No battery telemetry is read.
                        </p>
                    )}
                    {isNetwork && (
                        <p className="mt-4 rounded-sm border border-border bg-muted/50 p-3 text-sm text-foreground">
                            The demo checks adapter inventory only. Network connectivity and internet access are not tested.
                        </p>
                    )}
                    {id === "graphics" && (
                        <p className="mt-4 rounded-sm border border-border bg-muted/50 p-3 text-sm text-foreground">
                            A graphics adapter is present in demo inventory; no functional graphics test is supported.
                        </p>
                    )}
                    {id === "display" && (
                        <p className="mt-4 rounded-sm border border-border bg-muted/50 p-3 text-sm text-foreground">
                            Display details are inventory only. No functional display test is implemented here.
                        </p>
                    )}
                    {canRun && (
                        <div className="mt-4">
                            <button className="button button-primary" type="button" onClick={() => runSimpleDiagnostic(id)}>
                                {isBattery ? "Start Battery Assessment" : "Run Adapter Check"}
                            </button>
                            {canSkip && (
                                <button
                                    className="button button-secondary ml-2"
                                    type="button"
                                    onClick={() => openSkipConfirmation({
                                        key: id,
                                        name: definition.testName,
                                        kind: "diagnostic",
                                        diagnosticId: id,
                                    })}
                                >
                                    Skip Test
                                </button>
                            )}
                        </div>
                    )}
                    {canSkip && !canRun && (
                        <div className="mt-4">
                            <button
                                className="button button-secondary"
                                type="button"
                                onClick={() => openSkipConfirmation({
                                    key: id,
                                    name: definition.testName,
                                    kind: "diagnostic",
                                    diagnosticId: id,
                                })}
                            >
                                Skip Test
                            </button>
                        </div>
                    )}
                    {skipRecord && <SkippedTestNotice record={skipRecord} />}
                    {result.status !== "NOT RUN" && (
                        <div className="mt-4">
                            <ResultPanel result={result} />
                        </div>
                    )}
                </section>
            </div>
        );
    }

    function renderSelectedPanel() {
        switch (selectedKind) {
            case "cpu": return renderCpuPanel();
            case "memory": return renderMemoryPanel();
            case "storage": return renderStoragePanel();
            case "sensors": return renderSensorsPanel();
            case "browser-performance": return renderBrowserPerformancePanel();
            case "graphics":
            case "display":
            case "battery":
            case "network":
                return renderGeneralPanel(selectedKind);
        }
    }

    return (
        <main className="hardware-diagnostics page-flow min-w-0 gap-4" aria-labelledby="hardware-diagnostics-title">
            <div className="space-y-4 border-b border-border pb-4">
                <PageHeader
                    title="Hardware Diagnostics"
                    titleId="hardware-diagnostics-title"
                    description="Run and review automated tests for detected hardware components."
                    eyebrow="DEVICE INSPECTION"
                    actions={<span className="device-id-demo-label">DEMO DATA</span>}
                />
                <dl className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Device</dt>
                        <dd className="mt-1 break-words text-sm font-semibold text-foreground">
                            {demoDevice.manufacturer} {demoDevice.model}
                        </dd>
                    </div>
                    <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Serial number</dt>
                        <dd className="mt-1 break-words text-sm font-semibold text-foreground">
                            {demoDevice.systemSerialNumber ?? "Not available"}
                        </dd>
                    </div>
                    <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Technician</dt>
                        <dd className="mt-1 break-words text-sm font-semibold text-foreground">
                            {technicianName.trim() || "Not provided"}
                        </dd>
                    </div>
                    <div className="min-w-0">
                        <dt className="text-xs text-muted-foreground">Inspection started</dt>
                        <dd className="mt-1 text-sm font-semibold tabular-nums text-foreground">
                            {formatInspectionTimestamp(physicalInspectionStartedAt)}
                        </dd>
                    </div>
                </dl>
            </div>

            <div className="hardware-diagnostics-workspace flex min-w-0 flex-col gap-4 md:flex-row md:gap-0">
                <aside className="hardware-diagnostics-sidebar min-w-0 md:sticky md:top-4 md:max-h-[calc(100vh-2rem)] md:w-[270px] md:shrink-0 md:overflow-y-auto md:self-start md:border-r md:border-border md:pr-4">
                    <div className="hidden md:block">
                        <h2 className="mb-3 text-xs font-bold uppercase tracking-wide text-muted-foreground">
                            Diagnostic Components
                        </h2>
                        <nav aria-label="Diagnostic components" className="space-y-4">
                            {navigationGroups.map((group) => (
                                <section key={group.title}>
                                    <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                                        {group.title}
                                    </h3>
                                    <ul className="space-y-1">
                                        {group.items.map((item) => {
                                            const Icon = componentIcons[item.kind];
                                            const status = getItemStatus(item);
                                            const active = item.id === selectedDiagnosticComponentId;
                                            return (
                                                <li key={item.id}>
                                                    <button
                                                        className={`hardware-diagnostics-nav-item${active ? " is-active" : ""}`}
                                                        type="button"
                                                        onClick={() => selectComponent(item.id)}
                                                        aria-current={active ? "step" : undefined}
                                                    >
                                                        <Icon size={15} aria-hidden="true" />
                                                        <span className="min-w-0 flex-1 text-left">
                                                            <span className="block">{item.title}{item.optional ? " (optional)" : ""}</span>
                                                            {item.detail && <span className="mt-0.5 block text-[10px] font-normal text-muted-foreground">{item.detail}</span>}
                                                        </span>
                                                        <span className={`hardware-diagnostics-nav-status ${statusClass(status)}`} aria-label={status}>
                                                            <span className="hardware-diagnostics-status-dot" aria-hidden="true" />
                                                        </span>
                                                    </button>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </section>
                            ))}
                        </nav>
                    </div>
                    <label className="block text-xs font-semibold text-foreground md:hidden" htmlFor="diagnostic-component-select">
                        Select diagnostic component
                        <select
                            id="diagnostic-component-select"
                            className="hardware-diagnostics-input mt-1 w-full"
                            value={mobileComponentId}
                            onChange={(event) => {
                                const id = event.target.value as DiagnosticWorkspaceId;
                                setMobileComponentId(id);
                                selectComponent(id);
                            }}
                        >
                            {navigationGroups.map((group) => (
                                <optgroup label={group.title} key={group.title}>
                                    {group.items.map((item) => (
                                        <option value={item.id} key={item.id}>
                                            {item.title}{item.optional ? " (optional)" : ""} — {getItemStatus(item)}
                                        </option>
                                    ))}
                                </optgroup>
                            ))}
                        </select>
                    </label>
                </aside>

                <section className="min-w-0 flex-1 md:pl-5" aria-labelledby="selected-diagnostic-title">
                    <div className="mb-4 border-b border-border pb-4">
                        <h2 className="m-0 text-lg font-bold text-foreground" id="selected-diagnostic-title">
                            {selectedDrive
                                ? `${selectedItem.title} — ${selectedDrive.model}`
                                : selectedKind === "browser-performance"
                                    ? "Browser Performance (Optional)"
                                    : selectedDefinition?.testName ?? selectedItem.title}
                        </h2>
                        <p className="mt-1 text-sm leading-6 text-muted-foreground">
                            {selectedKind === "browser-performance"
                                ? "Run an optional simulated benchmark without opening tabs or executing workloads."
                                : selectedKind === "sensors"
                                    ? "Review available sample sensor readings. A reading does not indicate a functional pass."
                                    : selectedKind === "storage"
                                        ? "Select a test method for this physical drive. All operations are simulated."
                                        : selectedKind === "cpu"
                                            ? "Observe a bounded CPU stress-test simulation using predefined demo readings."
                                            : selectedKind === "memory"
                                                ? "Review installed memory and run the simulated memory test."
                                                : selectedDefinition?.hardwareName ?? "Review the diagnostic information for this component."}
                        </p>
                    </div>
                    {renderSelectedPanel()}
                </section>
            </div>

            <footer className="space-y-4 border-t border-border pt-4">
                <section className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs" aria-label="Diagnostic progress summary" aria-live="polite">
                    <strong className="text-foreground">Diagnostic summary · {diagnosticTestStatuses.length} tests</strong>
                    <span className="text-muted-foreground">Resolved: <strong className="text-foreground">{completedCount}</strong></span>
                    <span className="text-muted-foreground">Passed: <strong className="text-success">{passedCount}</strong></span>
                    <span className="text-muted-foreground">Failed: <strong className="text-destructive">{failedCount}</strong></span>
                    <span className="text-muted-foreground">Warnings: <strong className="text-warning">{warningCount}</strong></span>
                    <span className="text-muted-foreground">Skipped: <strong className="text-muted-foreground">{skippedCount}</strong></span>
                    <span className="text-muted-foreground">Pending: <strong className="text-foreground">{pendingCount}</strong></span>
                    <span className="text-muted-foreground">In Progress: <strong className="text-information">{inProgressCount}</strong></span>
                    {(inconclusiveCount + unsupportedCount + cancelledCount) > 0 && (
                        <span className="text-muted-foreground">
                            Other: <strong className="text-foreground">
                                {inconclusiveCount + unsupportedCount + cancelledCount}
                                {unsupportedCount > 0 ? ` (${unsupportedCount} unsupported)` : ""}
                            </strong>
                        </span>
                    )}
                    {skippedTestStatuses.length > 0 && (
                        <div className="basis-full border-t border-border pt-2">
                            <strong className="text-foreground">Skipped tests:</strong>
                            <ul className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-muted-foreground">
                                {skippedTestStatuses.map((test) => (
                                    <li key={test.name}>
                                        {test.name}
                                        {test.skipRecord?.reason ? ` — ${test.skipRecord.reason}` : ""}
                                        {test.skipRecord?.note ? `: ${test.skipRecord.note}` : ""}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </section>
                <div className="flex flex-col gap-3 border-t border-border pt-3 sm:flex-row sm:items-center sm:justify-between">
                    <Link className="button button-secondary w-fit" to="/physical-assessment">
                        Back to Physical Assessment
                    </Link>
                    <div className="flex flex-col items-stretch gap-2 sm:items-end">
                        <p className={`m-0 text-xs ${diagnosticsComplete ? "text-success" : "text-muted-foreground"}`} role="status">
                            {continueMessage}
                        </p>
                        <button
                            className="button button-primary"
                            type="button"
                            disabled={!diagnosticsComplete}
                            onClick={() => navigate("/technician-checks")}
                        >
                            Continue to Technician Checks
                        </button>
                    </div>
                </div>
            </footer>
            <Dialog
                open={skipTarget !== null}
                onOpenChange={(open) => {
                    if (!open) closeSkipConfirmation();
                }}
            >
                <DialogContent className="rounded-md sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>Skip this test?</DialogTitle>
                        <DialogDescription>
                            {skipTarget?.name ? `Test: ${skipTarget.name}` : "This test will not be performed."}
                            {" "}It will be recorded as Skipped, not Passed.
                        </DialogDescription>
                    </DialogHeader>
                    <label className="block text-xs font-semibold text-foreground" htmlFor="diagnostic-skip-reason">
                        Reason (optional)
                        <select
                            id="diagnostic-skip-reason"
                            className="hardware-diagnostics-input mt-1 w-full"
                            value={skipReason}
                            onChange={(event) => setSkipReason(event.target.value as DiagnosticSkipReason | "")}
                        >
                            <option value="">Select a reason (optional)</option>
                            {skipReasonOptions.map((reason) => <option value={reason} key={reason}>{reason}</option>)}
                        </select>
                    </label>
                    {skipReason === "Other" && (
                        <label className="block text-xs font-semibold text-foreground" htmlFor="diagnostic-skip-note">
                            Remark (optional)
                            <textarea
                                id="diagnostic-skip-note"
                                className="hardware-diagnostics-input mt-1 w-full"
                                rows={3}
                                maxLength={240}
                                value={skipNote}
                                onChange={(event) => setSkipNote(event.target.value)}
                                placeholder="Add a short reason"
                            />
                        </label>
                    )}
                    <DialogFooter>
                        <button className="button button-secondary" type="button" onClick={closeSkipConfirmation}>
                            Cancel
                        </button>
                        <button className="button button-primary" type="button" onClick={confirmSkipTest}>
                            Confirm Skip
                        </button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </main>
    );
}
