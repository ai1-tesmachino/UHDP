import { demoDevice, getTotalInstalledRamGb } from "./demoDevice";
import type { DiagnosticResult, DiagnosticStatus } from "./hardwareDiagnostics";

export type MemoryTestStatus =
    | "Not Started"
    | "Ready"
    | "Running"
    | "Stopped"
    | "Finalized";

export interface MemoryTestState {
    status: MemoryTestStatus;
    selectedDurationSeconds: number;
    durationConfirmed: boolean;
    elapsedSeconds: number;
    errorsDetected: number | null;
    temperatureReadings: Array<{ elapsedSeconds: number; temperatureC: number }>;
    currentTemperatureC: number | null;
    maximumTemperatureC: number | null;
    stopReason: "manual" | "duration" | null;
    finalResult: DiagnosticResult | null;
}

export const memoryTestDurations = [
    { label: "5 minutes", seconds: 5 * 60 },
    { label: "10 minutes", seconds: 10 * 60 },
    { label: "15 minutes", seconds: 15 * 60 },
    { label: "30 minutes", seconds: 30 * 60 },
    { label: "1 hour", seconds: 60 * 60 },
    { label: "5 hours", seconds: 5 * 60 * 60 },
] as const;

export const memoryTemperatureSensorAvailable = false;

export function createInitialMemoryTest(): MemoryTestState {
    return {
        status: "Not Started",
        selectedDurationSeconds: memoryTestDurations[0].seconds,
        durationConfirmed: false,
        elapsedSeconds: 0,
        errorsDetected: null,
        temperatureReadings: [],
        currentTemperatureC: null,
        maximumTemperatureC: null,
        stopReason: null,
        finalResult: null,
    };
}

function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    if (hours > 0) {
        return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
    }
    return `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

export function createMemoryTestResult(state: MemoryTestState): DiagnosticResult {
    const completedDuration = state.stopReason === "duration"
        && state.elapsedSeconds >= state.selectedDurationSeconds;
    const wasStarted = state.errorsDetected !== null;
    const status: DiagnosticStatus = completedDuration
        ? "PASS"
        : wasStarted
            ? "CANCELLED"
            : "INCONCLUSIVE";
    const summary = completedDuration
        ? "Simulated memory test completed successfully; no actual memory test was performed."
        : wasStarted
            ? `The simulated memory test stopped at ${formatDuration(state.elapsedSeconds)} and is incomplete; no pass/fail conclusion was made.`
            : "The memory test was finalized without being started. No memory test result is available.";

    return {
        status,
        summary,
        measurements: [
            { label: "Memory under test", value: `${getTotalInstalledRamGb(demoDevice)} GB (${demoDevice.memory.modules.length} modules)` },
            { label: "Selected duration", value: memoryTestDurations.find((duration) => duration.seconds === state.selectedDurationSeconds)?.label ?? formatDuration(state.selectedDurationSeconds) },
            { label: "Elapsed time", value: formatDuration(state.elapsedSeconds) },
            { label: "Errors detected", value: state.errorsDetected === null ? "Not evaluated" : String(state.errorsDetected) },
            { label: "Memory temperature", value: "Not Available" },
        ],
        observations: [
            "All results are simulated demo data; no memory coverage or actual hardware result is claimed.",
            "Memory temperature is unavailable. CPU temperature was not used as a substitute.",
        ],
        isDemoData: true,
    };
}

export type StorageTestId =
    | "smart-health"
    | "read-test"
    | "file-copy-verification"
    | "write-read-back"
    | "capacity-verification"
    | "filesystem-check";

export interface DemoStorageDrive {
    id: string;
    model: string;
    capacityGb: number;
    type: string;
    interface: string;
    serialNumber: string | null;
}

export interface StorageTestResult extends DiagnosticResult {
    testId: StorageTestId;
    testName: string;
    driveId: string;
    durationSeconds: number;
}

export interface ActiveStorageTestRun {
    driveId: string;
    testId: StorageTestId;
    progressPercent: number;
}

export type StorageTestResults = Record<string, Partial<Record<StorageTestId, StorageTestResult>>>;

export interface StorageTestDefinition {
    id: StorageTestId;
    name: string;
    purpose: string;
    guidance: string;
    demoResult: {
        status: DiagnosticStatus;
        summary: string;
        measurements: Array<{ label: string; value: string }>;
        observations: string[];
        durationSeconds: number;
    };
}

export const demoStorageDrives: DemoStorageDrive[] = demoDevice.storage.drives.map((drive, index) => ({
    id: `drive-${index + 1}`,
    model: drive.model,
    capacityGb: drive.capacityGb,
    type: drive.type,
    interface: drive.interface,
    serialNumber: drive.serialNumber,
}));

export const storageTestDefinitions: StorageTestDefinition[] = [
    {
        id: "smart-health",
        name: "SMART Health",
        purpose: "Display drive-reported health information.",
        guidance: "SMART availability and attributes below are predefined demo values, not drive readings.",
        demoResult: {
            status: "WARNING",
            summary: "Demo SMART warning recorded; no SMART query was made.",
            measurements: [
                { label: "SMART availability", value: "Available (demo sample)" },
                { label: "Health status", value: "Warning (demo sample)" },
                { label: "Power-on hours", value: "12,345 (demo value)" },
                { label: "Unsafe shutdowns", value: "3 (demo value)" },
            ],
            observations: ["Predefined demo warning only; drive attributes were not read."],
            durationSeconds: 3,
        },
    },
    {
        id: "read-test",
        name: "Read Test",
        purpose: "Read existing data and show read progress, data read, speed and errors.",
        guidance: "A real read test requires suitable existing readable data. No data will be accessed in this demo.",
        demoResult: {
            status: "PASS",
            summary: "Simulated read-only test completed; no drive data was read.",
            measurements: [
                { label: "Data read", value: "512 MB (demo value)" },
                { label: "Read speed", value: "256 MB/s (demo value)" },
                { label: "Errors", value: "0 (demo value)" },
            ],
            observations: ["This result is simulated; no physical drive was accessed."],
            durationSeconds: 5,
        },
    },
    {
        id: "file-copy-verification",
        name: "File Copy and Verification",
        purpose: "Simulate copying a test file and verifying its contents.",
        guidance: "Use generated demo data or select a source-file label. No file contents are read, copied or changed.",
        demoResult: {
            status: "PASS",
            summary: "Simulated copy verification completed; no files were written or moved.",
            measurements: [
                { label: "Data copied", value: "128 MB (demo value)" },
                { label: "Transfer speed", value: "80 MB/s (demo value)" },
                { label: "Verification", value: "Demo checksum matched" },
            ],
            observations: ["The original source file remains unchanged; no destination file was created."],
            durationSeconds: 6,
        },
    },
    {
        id: "write-read-back",
        name: "Write and Read-back Test",
        purpose: "Simulate writing a temporary test file, reading it back and verifying integrity.",
        guidance: "The test file, writes and checksum below are simulated. No file or raw-device writes occur.",
        demoResult: {
            status: "PASS",
            summary: "Simulated write and read-back verification completed; no test file was created.",
            measurements: [
                { label: "Test file size", value: "64 MB (demo value)" },
                { label: "Write speed", value: "72 MB/s (demo value)" },
                { label: "Read speed", value: "160 MB/s (demo value)" },
                { label: "Checksum verification", value: "Matched (demo result)" },
            ],
            observations: ["No drive writes, raw-device access or temporary files were performed."],
            durationSeconds: 8,
        },
    },
    {
        id: "capacity-verification",
        name: "Capacity Verification",
        purpose: "Compare reported physical capacity with filesystem capacity where available.",
        guidance: "Drive capacity is physical-device information; available filesystem capacity requires a real filesystem query.",
        demoResult: {
            status: "INCONCLUSIVE",
            summary: "Physical capacity is shown from demo inventory; filesystem capacity is unavailable in this prototype.",
            measurements: [
                { label: "Reported drive capacity", value: "From selected drive demo inventory" },
                { label: "Available filesystem capacity", value: "Not Available" },
            ],
            observations: ["No partitions or filesystem capacity were queried."],
            durationSeconds: 2,
        },
    },
    {
        id: "filesystem-check",
        name: "Filesystem Check",
        purpose: "Show whether a safe, non-repairing filesystem check is available.",
        guidance: "Future checks should be non-repairing by default. Automatic repair is not implemented.",
        demoResult: {
            status: "UNSUPPORTED",
            summary: "Filesystem checks are not available in this frontend-only demo.",
            measurements: [
                { label: "Check mode", value: "Non-repairing by default (future integration)" },
                { label: "Filesystem status", value: "Not Available" },
            ],
            observations: ["No filesystem was inspected or repaired."],
            durationSeconds: 1,
        },
    },
];

export function createStorageTestResult(
    testId: StorageTestId,
    drive: DemoStorageDrive,
    sourceFileLabel?: string,
): StorageTestResult {
    const definition = storageTestDefinitions.find((test) => test.id === testId);
    if (!definition) throw new Error(`Unknown storage test: ${testId}`);

    const measurements = definition.demoResult.measurements.map((measurement) => {
        if (testId !== "capacity-verification" || measurement.label !== "Reported drive capacity") {
            return measurement;
        }
        return { ...measurement, value: `${drive.capacityGb} GB (physical drive)` };
    });
    if (testId === "file-copy-verification") {
        measurements.unshift(
            { label: "Source", value: sourceFileLabel || "Generated UHDP demo test data" },
            { label: "Destination", value: "Demo placeholder only; no file was written" },
        );
    }

    return {
        testId,
        testName: definition.name,
        driveId: drive.id,
        durationSeconds: definition.demoResult.durationSeconds,
        status: definition.demoResult.status,
        summary: definition.demoResult.summary,
        measurements: [
            { label: "Drive tested", value: drive.model },
            ...measurements,
        ],
        observations: definition.demoResult.observations,
        isDemoData: true,
    };
}

export function createInitialStorageTestResults(): StorageTestResults {
    return {};
}

export function createStorageDiagnosticResult(
    drive: DemoStorageDrive,
    results: Partial<Record<StorageTestId, StorageTestResult>>,
): DiagnosticResult {
    const recordedResults = Object.values(results);
    const allMethodsRecorded = storageTestDefinitions.every((test) => results[test.id] !== undefined);
    const status = getStorageResultStatus(recordedResults, allMethodsRecorded);
    return {
        status,
        summary: recordedResults.length > 0
            ? allMethodsRecorded
                ? `All ${storageTestDefinitions.length} simulated methods were recorded for this drive; see individual outcomes.`
                : `${recordedResults.length} of ${storageTestDefinitions.length} simulated methods were recorded; no overall pass was assigned.`
            : "No storage test was run; no physical drive verdict is available.",
        measurements: [
            { label: "Drive", value: drive.model },
            { label: "Simulated methods recorded", value: `${recordedResults.length} of ${storageTestDefinitions.length}` },
        ],
        observations: [
            "No storage reads, writes, filesystem checks, repairs or destructive operations were performed.",
            ...(recordedResults.length > 0
                ? recordedResults.map((result) => `${result.testName}: ${result.status}`)
                : []),
        ],
        isDemoData: true,
    };
}

function getStorageResultStatus(results: StorageTestResult[], allMethodsRecorded: boolean): DiagnosticStatus {
    if (results.length === 0) return "NOT RUN";
    if (results.some((result) => result.status === "FAIL")) return "FAIL";
    if (allMethodsRecorded && results.every((result) => result.status === "PASS")) return "PASS";
    if (results.some((result) => result.status === "WARNING")) return "WARNING";
    if (results.some((result) => result.status === "BLOCKED")) return "BLOCKED";
    if (allMethodsRecorded && results.every((result) => result.status === "UNSUPPORTED")) return "UNSUPPORTED";
    if (allMethodsRecorded && results.some((result) => result.status === "CANCELLED")) return "CANCELLED";
    return "INCONCLUSIVE";
}

export function createOverallStorageDiagnosticResult(
    drives: DemoStorageDrive[],
    results: StorageTestResults,
): DiagnosticResult {
    const driveResults = drives.map((drive) => ({
        drive,
        results: results[drive.id] ?? {},
    }));
    const recordedResults = driveResults.flatMap(({ results: driveTests }) => Object.values(driveTests));
    const allMethodsRecorded = drives.length > 0 && driveResults.every(({ results: driveTests }) =>
        storageTestDefinitions.every((test) => driveTests[test.id] !== undefined));
    const status = drives.length === 0
        ? "UNSUPPORTED"
        : getStorageResultStatus(recordedResults, allMethodsRecorded);

    return {
        status,
        summary: recordedResults.length === 0
            ? drives.length > 0
                ? "No storage tests have been run for the detected physical drives."
                : "No physical drives are available in the demo inventory."
            : allMethodsRecorded
                ? `All ${storageTestDefinitions.length} methods were recorded for each of ${drives.length} drive(s); review individual outcomes.`
                : `${recordedResults.length} simulated result(s) recorded across ${drives.length} drive(s); incomplete coverage is not a pass.`,
        measurements: [
            { label: "Physical drives", value: String(drives.length) },
            { label: "Test results recorded", value: String(recordedResults.length) },
            { label: "Methods per drive", value: String(storageTestDefinitions.length) },
        ],
        observations: [
            "Each result is kept separate by drive and test method.",
            "No storage reads, writes, filesystem checks, repairs or destructive operations were performed.",
            ...driveResults.map(({ drive, results: driveTests }) =>
                `${drive.model}: ${Object.keys(driveTests).length} of ${storageTestDefinitions.length} methods recorded.`),
        ],
        isDemoData: true,
    };
}
