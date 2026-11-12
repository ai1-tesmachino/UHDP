import type { ActiveStorageTestRun, DemoStorageDrive } from "./memoryStorageTests";

export interface StorageMonitoringReading {
    elapsedSeconds: number;
    readMBps: number;
    writeMBps: number;
    activeTimePercent: number | null;
    queueDepth: number | null;
    readIops: number | null;
    writeIops: number | null;
    temperatureC: number | null;
}

export interface StorageDriveMonitoringState {
    readings: StorageMonitoringReading[];
    minimumTemperatureC: number | null;
    maximumTemperatureC: number | null;
}

export type StorageMonitoringState = Record<string, StorageDriveMonitoringState>;

const historyLimit = 300;

function getDriveSeed(driveId: string): number {
    return [...driveId].reduce((total, character) => total + character.charCodeAt(0), 0);
}

function createReading(
    driveId: string,
    elapsedSeconds: number,
    activeTest: ActiveStorageTestRun | null,
): StorageMonitoringReading {
    const seed = getDriveSeed(driveId);
    const idleRead = Math.max(0.2, 1.2 + Math.sin((elapsedSeconds + seed) / 7) * 0.8);
    const idleWrite = Math.max(0.1, 0.6 + Math.cos((elapsedSeconds + seed) / 9) * 0.4);
    let readMBps = idleRead;
    let writeMBps = idleWrite;

    if (activeTest) {
        const phase = Math.max(0, Math.min(1, activeTest.progressPercent / 100));
        const variation = Math.sin((elapsedSeconds + seed) / 3) * 18;
        switch (activeTest.testId) {
            case "read-test":
            case "capacity-verification":
                readMBps = 90 + variation;
                break;
            case "write-read-back":
                if (phase < 0.65) writeMBps = 70 + variation;
                else readMBps = 90 + variation;
                break;
            case "file-copy-verification":
                readMBps = 55 + variation;
                writeMBps = 35 + variation / 2;
                break;
            case "filesystem-check":
                readMBps = 28 + variation / 2;
                break;
            case "smart-health":
                readMBps = idleRead + 2;
                writeMBps = idleWrite;
                break;
        }
    }

    return {
        elapsedSeconds,
        readMBps: Math.max(0, Math.round(readMBps * 10) / 10),
        writeMBps: Math.max(0, Math.round(writeMBps * 10) / 10),
        activeTimePercent: null,
        queueDepth: null,
        readIops: null,
        writeIops: null,
        temperatureC: null,
    };
}

export function createInitialStorageMonitoring(drives: DemoStorageDrive[]): StorageMonitoringState {
    return Object.fromEntries(drives.map((drive) => [
        drive.id,
        {
            readings: [createReading(drive.id, 0, null)],
            minimumTemperatureC: null,
            maximumTemperatureC: null,
        },
    ]));
}

export function advanceStorageMonitoring(
    state: StorageMonitoringState,
    driveId: string,
    activeTest: ActiveStorageTestRun | null,
): StorageMonitoringState {
    const current = state[driveId];
    if (!current) return state;

    const elapsedSeconds = (current.readings[current.readings.length - 1]?.elapsedSeconds ?? 0) + 1;
    return {
        ...state,
        [driveId]: {
            ...current,
            readings: [
                ...current.readings.slice(-(historyLimit - 1)),
                createReading(driveId, elapsedSeconds, activeTest),
            ],
        },
    };
}
