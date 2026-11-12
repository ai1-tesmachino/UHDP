import {
    demoDevice,
    getTotalInstalledRamGb,
    getTotalInstalledStorageGb,
} from "./demoDevice";

export type DiagnosticStatus =
    | "PASS"
    | "FAIL"
    | "WARNING"
    | "INCONCLUSIVE"
    | "UNSUPPORTED"
    | "BLOCKED"
    | "CANCELLED"
    | "NOT RUN";

export interface DiagnosticDetail {
    label: string;
    value: string;
}

export interface DiagnosticResult {
    status: DiagnosticStatus;
    summary: string;
    measurements: DiagnosticDetail[];
    observations: string[];
    isDemoData: boolean;
}

export interface HardwareDiagnosticDefinition {
    id: string;
    category: string;
    testName: string;
    hardwareName: string;
    hardwareDetails: DiagnosticDetail[];
    initialResult: DiagnosticResult;
    simulatedResult: DiagnosticResult | null;
}

function demoResult(
    status: DiagnosticStatus,
    summary: string,
    measurements: DiagnosticDetail[] = [],
    observations: string[] = [],
): DiagnosticResult {
    return { status, summary, measurements, observations, isDemoData: true };
}

const totalRamGb = getTotalInstalledRamGb(demoDevice);
const totalStorageGb = getTotalInstalledStorageGb(demoDevice);
const memoryModules = demoDevice.memory.modules;
const storageDrives = demoDevice.storage.drives;
const formatFrequency = (frequencyGhz: number | null) =>
    frequencyGhz === null ? "Not Available" : `${frequencyGhz} GHz`;

export const hardwareDiagnosticDefinitions = [
    {
        id: "cpu",
        category: "CPU",
        testName: "CPU Stress Test",
        hardwareName: `${demoDevice.processor.manufacturer} ${demoDevice.processor.model}`,
        hardwareDetails: [
            { label: "Manufacturer", value: demoDevice.processor.manufacturer },
            { label: "Processor", value: demoDevice.processor.model },
            { label: "Physical cores", value: String(demoDevice.processor.physicalCores) },
            { label: "Logical threads", value: String(demoDevice.processor.logicalThreads) },
            { label: "Base frequency", value: formatFrequency(demoDevice.processor.baseFrequencyGhz) },
            { label: "Maximum frequency", value: formatFrequency(demoDevice.processor.maxFrequencyGhz) },
        ],
        initialResult: demoResult("NOT RUN", "The simulated CPU stress test has not been run."),
        simulatedResult: null,
    },
    {
        id: "memory",
        category: "Memory",
        testName: "Memory Functional Test",
        hardwareName: `${totalRamGb} GB installed RAM`,
        hardwareDetails: [
            { label: "Total installed RAM", value: `${totalRamGb} GB` },
            { label: "Installed modules", value: `${memoryModules.length}` },
            { label: "Memory type", value: [...new Set(memoryModules.map((module) => module.type))].join(", ") || "Not Available" },
            ...memoryModules.map((module, index) => ({
                label: `Module ${index + 1}`,
                value: `${module.capacityGb} GB · ${module.speedMts === null ? "Not Available" : `${module.speedMts} MT/s`}`,
            })),
        ],
        initialResult: demoResult("NOT RUN", "The simulated memory test has not been run."),
        simulatedResult: demoResult(
            "PASS",
            "Demo memory test completed successfully; no actual memory test was performed.",
            [
                { label: "Installed memory", value: `${totalRamGb} GB` },
                { label: "Modules identified", value: `${memoryModules.length}` },
            ],
        ),
    },
    {
        id: "storage",
        category: "Storage",
        testName: "Storage Health Check",
        hardwareName: storageDrives.length > 0
            ? storageDrives.map((drive) => drive.model).join(", ")
            : "Not Available",
        hardwareDetails: [
            { label: "Total physical capacity", value: `${totalStorageGb} GB` },
            ...(storageDrives.length > 0
                ? storageDrives.flatMap((drive, index) => [
                    { label: `Drive ${index + 1}`, value: drive.model },
                    { label: `Drive ${index + 1} capacity`, value: `${drive.capacityGb} GB` },
                    { label: `Drive ${index + 1} type`, value: drive.type },
                    { label: `Drive ${index + 1} interface`, value: drive.interface },
                    { label: `Drive ${index + 1} serial number`, value: drive.serialNumber ?? "Not Available" },
                ])
                : [{ label: "Physical drives", value: "Not Available" }]),
        ],
        initialResult: demoResult(
            "NOT RUN",
            "No storage test has been run for the individual physical drives.",
            [
                { label: "Physical drives", value: `${storageDrives.length}` },
                { label: "Total capacity", value: `${totalStorageGb} GB` },
            ],
        ),
        simulatedResult: null,
    },
    {
        id: "graphics",
        category: "Graphics",
        testName: "Graphics Functional Check",
        hardwareName: demoDevice.graphicsAdapter,
        hardwareDetails: [
            { label: "GPU manufacturer", value: "Intel" },
            { label: "GPU model", value: demoDevice.graphicsAdapter },
            { label: "Functional test", value: "Unsupported in this prototype" },
        ],
        initialResult: demoResult(
            "UNSUPPORTED",
            "Graphics adapter identification is shown as demo inventory only; no functional test is available.",
        ),
        simulatedResult: null,
    },
    {
        id: "battery",
        category: "Battery",
        testName: "Battery Health Assessment",
        hardwareName: "Lenovo battery (demo sample)",
        hardwareDetails: [
            { label: "Battery manufacturer", value: "Lenovo (demo sample)" },
            { label: "Design capacity", value: "48 Wh (demo value)" },
            { label: "Full-charge capacity", value: "41 Wh (demo value)" },
            { label: "Voltage", value: "11.4 V (demo value)" },
            { label: "Battery health", value: "85% (demo estimate)" },
        ],
        initialResult: demoResult("NOT RUN", "The simulated battery assessment has not been run."),
        simulatedResult: demoResult(
            "INCONCLUSIVE",
            "Demo sample values are available, but they do not represent a measured battery-health test.",
            [
                { label: "Design capacity", value: "48 Wh (demo value)" },
                { label: "Full-charge capacity", value: "41 Wh (demo value)" },
                { label: "Voltage", value: "11.4 V (demo value)" },
            ],
            ["No actual battery telemetry was read."],
        ),
    },
    {
        id: "display",
        category: "Display",
        testName: "Display Identification Check",
        hardwareName: demoDevice.display.manufacturer ?? "Display manufacturer not available",
        hardwareDetails: [
            { label: "Display manufacturer", value: demoDevice.display.manufacturer ?? "Not Available" },
            { label: "Physical size", value: demoDevice.display.screenSizeInches === null ? "Not Available" : `${demoDevice.display.screenSizeInches} inches` },
            { label: "Resolution", value: demoDevice.display.resolution ?? "Not Available" },
            { label: "Functional test", value: "Not implemented in this prototype" },
        ],
        initialResult: demoResult(
            "UNSUPPORTED",
            "Display details are demo inventory only; no display functional test is implemented.",
            [],
            ["Manual visual display inspection belongs to a separate workflow stage."],
        ),
        simulatedResult: null,
    },
    {
        id: "network",
        category: "Network",
        testName: "Network Adapter Identification",
        hardwareName: "Wi-Fi and Ethernet adapters (demo inventory)",
        hardwareDetails: [
            { label: "Wi-Fi adapter", value: "Intel Dual Band Wireless-AC 8265 (demo sample)" },
            { label: "Ethernet adapter", value: "Intel Ethernet Connection I219-LM (demo sample)" },
            { label: "Adapter identification", value: "Listed in demo inventory" },
        ],
        initialResult: demoResult("NOT RUN", "The simulated adapter identification test has not been run."),
        simulatedResult: demoResult(
            "WARNING",
            "Demo adapter identification completed with a warning; no network or internet connection was tested.",
            [
                { label: "Wi-Fi adapter", value: "Available in demo inventory" },
                { label: "Ethernet adapter", value: "Available in demo inventory" },
            ],
            ["Network connectivity is not required or tested in this prototype."],
        ),
    },
    {
        id: "sensors",
        category: "Sensors",
        testName: "Sensor Availability Check",
        hardwareName: "Temperature and fan sensors",
        hardwareDetails: [
            { label: "CPU temperature", value: "Not Available" },
            { label: "GPU temperature", value: "Not Available" },
            { label: "Fan speed", value: "Not Available" },
            { label: "Battery temperature", value: "Not Available" },
        ],
        initialResult: demoResult(
            "UNSUPPORTED",
            "Sensor readings are unavailable in this demo; unavailable sensors are not treated as failures.",
        ),
        simulatedResult: null,
    },
] as const satisfies readonly HardwareDiagnosticDefinition[];

export type DiagnosticId = (typeof hardwareDiagnosticDefinitions)[number]["id"];
export type DiagnosticWorkspaceId = DiagnosticId | `storage:${string}` | "browser-performance";
export type DiagnosticResultRecord = Record<DiagnosticId, DiagnosticResult>;

export function createInitialDiagnosticResults(): DiagnosticResultRecord {
    return {
        cpu: hardwareDiagnosticDefinitions[0].initialResult,
        memory: hardwareDiagnosticDefinitions[1].initialResult,
        storage: hardwareDiagnosticDefinitions[2].initialResult,
        graphics: hardwareDiagnosticDefinitions[3].initialResult,
        battery: hardwareDiagnosticDefinitions[4].initialResult,
        display: hardwareDiagnosticDefinitions[5].initialResult,
        network: hardwareDiagnosticDefinitions[6].initialResult,
        sensors: hardwareDiagnosticDefinitions[7].initialResult,
    };
}

export function getSimulatedDiagnosticResult(id: DiagnosticId): DiagnosticResult | null {
    return hardwareDiagnosticDefinitions.find((definition) => definition.id === id)?.simulatedResult ?? null;
}

export function isHardwareDiagnosticsComplete(results: DiagnosticResultRecord): boolean {
    return hardwareDiagnosticDefinitions.every((definition) => results[definition.id].status !== "NOT RUN");
}
