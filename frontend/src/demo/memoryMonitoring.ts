export interface MemoryMonitoringReading {
    elapsedSeconds: number;
    usedGb: number;
    availableGb: number;
    freeGb: number;
    cachedGb: number;
    bufferedGb: number;
}

export interface MemoryMonitoringState {
    totalGb: number;
    readings: MemoryMonitoringReading[];
    swap: null;
}

const historyLimit = 300;

function createReading(totalGb: number, elapsedSeconds: number, testRunning: boolean): MemoryMonitoringReading {
    const variation = Math.sin(elapsedSeconds / 11) * 0.035 + Math.cos(elapsedSeconds / 19) * 0.018;
    const stressLoad = testRunning ? 0.15 + Math.sin(elapsedSeconds / 8) * 0.025 : 0;
    const usedHundredths = Math.round(totalGb * Math.min(0.88, Math.max(0.2, 0.46 + variation + stressLoad)) * 100);
    const totalHundredths = Math.round(totalGb * 100);
    const availableHundredths = totalHundredths - usedHundredths;
    const freeHundredths = Math.round(availableHundredths * (0.28 + Math.sin(elapsedSeconds / 17) * 0.025));
    const cachedHundredths = Math.round(availableHundredths * 0.42);

    return {
        elapsedSeconds,
        usedGb: usedHundredths / 100,
        availableGb: availableHundredths / 100,
        freeGb: freeHundredths / 100,
        cachedGb: cachedHundredths / 100,
        bufferedGb: (availableHundredths - freeHundredths - cachedHundredths) / 100,
    };
}

export function createInitialMemoryMonitoring(totalGb: number): MemoryMonitoringState {
    return {
        totalGb,
        readings: [createReading(totalGb, 0, false)],
        swap: null,
    };
}

export function advanceMemoryMonitoring(
    state: MemoryMonitoringState,
    testRunning: boolean,
): MemoryMonitoringState {
    const elapsedSeconds = (state.readings[state.readings.length - 1]?.elapsedSeconds ?? 0) + 1;
    return {
        ...state,
        readings: [
            ...state.readings.slice(-(historyLimit - 1)),
            createReading(state.totalGb, elapsedSeconds, testRunning),
        ],
    };
}
