import { demoDevice } from "./demoDevice";

export interface CpuMonitoringReading {
    elapsedSeconds: number;
    threadUtilisationPercent: number[];
    overallUtilisationPercent: number | null;
    currentFrequencyGhz: number | null;
    packageTemperatureC: number | null;
}

export interface CpuMonitoringState {
    elapsedSeconds: number;
    readings: CpuMonitoringReading[];
    minimumPackageTemperatureC: number | null;
    maximumPackageTemperatureC: number | null;
}

export const cpuMonitoringHistoryLimit = 300;

function roundToOneDecimal(value: number): number {
    return Number(value.toFixed(1));
}

function createReading(
    elapsedSeconds: number,
    logicalThreadCount: number,
    stressTestRunning: boolean,
    previousTemperatureC: number | null,
    temperatureAvailable: boolean,
): CpuMonitoringReading {
    const threadUtilisationPercent = Array.from(
        { length: Math.max(0, Math.floor(logicalThreadCount)) },
        (_, threadIndex) => {
            const phase = elapsedSeconds * 0.19 + threadIndex * 0.87;
            const variation = Math.sin(phase) * (stressTestRunning ? 10 : 4)
                + Math.cos(elapsedSeconds * 0.11 + threadIndex * 0.51) * 3;
            const baseline = stressTestRunning
                ? 76 + (threadIndex % 4) * 2
                : 5 + (threadIndex % 3);
            return Math.max(0, Math.min(100, Math.round(baseline + variation)));
        },
    );
    const overallUtilisationPercent = threadUtilisationPercent.length > 0
        ? roundToOneDecimal(threadUtilisationPercent.reduce((total, value) => total + value, 0) / threadUtilisationPercent.length)
        : null;
    const { baseFrequencyGhz, maxFrequencyGhz } = demoDevice.processor;
    const currentFrequencyGhz = overallUtilisationPercent === null
        || baseFrequencyGhz === null
        || maxFrequencyGhz === null
        ? null
        : roundToOneDecimal(Math.min(
            maxFrequencyGhz,
            Math.max(
                baseFrequencyGhz,
                baseFrequencyGhz
                    + (maxFrequencyGhz - baseFrequencyGhz) * overallUtilisationPercent / 100
                    + Math.sin(elapsedSeconds * 0.13) * 0.04,
            ),
        ));
    const packageTemperatureC = !temperatureAvailable
        ? null
        : roundToOneDecimal(
            (previousTemperatureC ?? 42)
            + ((stressTestRunning ? 76 : 42) - (previousTemperatureC ?? 42))
                * (stressTestRunning ? 0.035 : 0.08)
            + Math.sin(elapsedSeconds * 0.12) * 0.12,
        );

    return {
        elapsedSeconds,
        threadUtilisationPercent,
        overallUtilisationPercent,
        currentFrequencyGhz,
        packageTemperatureC,
    };
}

export function createInitialCpuMonitoring(
    logicalThreadCount: number,
    temperatureAvailable = true,
): CpuMonitoringState {
    const initialReading = createReading(0, logicalThreadCount, false, 42, temperatureAvailable);
    return {
        elapsedSeconds: 0,
        readings: [initialReading],
        minimumPackageTemperatureC: initialReading.packageTemperatureC,
        maximumPackageTemperatureC: initialReading.packageTemperatureC,
    };
}

export function advanceCpuMonitoring(
    current: CpuMonitoringState,
    logicalThreadCount: number,
    stressTestRunning: boolean,
): CpuMonitoringState {
    const elapsedSeconds = current.elapsedSeconds + 1;
    const previousReading = current.readings[current.readings.length - 1];
    const reading = createReading(
        elapsedSeconds,
        logicalThreadCount,
        stressTestRunning,
        previousReading?.packageTemperatureC ?? null,
        previousReading?.packageTemperatureC !== null && previousReading?.packageTemperatureC !== undefined,
    );
    const temperature = reading.packageTemperatureC;

    return {
        elapsedSeconds,
        readings: [...current.readings, reading].slice(-cpuMonitoringHistoryLimit),
        minimumPackageTemperatureC: temperature === null
            ? current.minimumPackageTemperatureC
            : Math.min(current.minimumPackageTemperatureC ?? temperature, temperature),
        maximumPackageTemperatureC: temperature === null
            ? current.maximumPackageTemperatureC
            : Math.max(current.maximumPackageTemperatureC ?? temperature, temperature),
    };
}
