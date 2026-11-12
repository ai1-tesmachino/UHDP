import {
    createContext,
    useCallback,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    createInitialPhysicalAssessments,
    type PhysicalAreaAssessment,
    type PhysicalAssessmentRecord,
    type PhysicalInspectionAreaId,
} from "./physicalAssessment";
import {
    createInitialDiagnosticResults,
    type DiagnosticId,
    type DiagnosticResult,
    type DiagnosticResultRecord,
} from "./hardwareDiagnostics";
import {
    createInitialCpuStressTest,
    createCpuTemperatureReading,
    type CpuStressTestState,
    type CpuTemperatureReading,
} from "./cpuStressTest";
import {
    createInitialMemoryTest,
    createInitialStorageTestResults,
    type MemoryTestState,
    type StorageTestResult,
    type StorageTestResults,
} from "./memoryStorageTests";
import {
    createDemoBrowserPerformanceResult,
    createInitialBrowserPerformanceTest,
    type BrowserBenchmarkId,
    type BrowserPerformanceTestState,
    type BrowserTabCount,
    type BrowserTestDuration,
} from "./browserPerformanceTest";
import {
    createInitialManualFunctionalChecks,
    type ManualCheckCategoryId,
    type ManualCheckRecord,
    type ManualFunctionalChecksState,
    type PortCheckRecord,
    type PortCheckOutcome,
} from "./technicianFunctionalChecks";

interface DemoInspectionState {
    assetTag: string;
    setAssetTag: (value: string) => void;
    technicianName: string;
    setTechnicianName: (value: string) => void;
    deviceConfirmed: boolean;
    confirmDevice: () => void;
    physicalAssessments: PhysicalAssessmentRecord;
    updatePhysicalAssessment: (areaId: PhysicalInspectionAreaId, assessment: PhysicalAreaAssessment) => void;
    generalObservations: string;
    setGeneralObservations: (value: string) => void;
    diagnosticResults: DiagnosticResultRecord;
    updateDiagnosticResult: (id: DiagnosticId, result: DiagnosticResult) => void;
    cpuStressTest: CpuStressTestState;
    prepareCpuStressTest: () => void;
    startCpuStressTest: () => void;
    appendCpuStressReading: (reading: CpuTemperatureReading) => void;
    stopCpuStressTest: (reason: "manual" | "duration") => void;
    finalizeCpuStressTest: (result: DiagnosticResult) => void;
    memoryTest: MemoryTestState;
    prepareMemoryTest: () => void;
    selectMemoryTestDuration: (seconds: number) => void;
    confirmMemoryTestDuration: () => void;
    startMemoryTest: () => void;
    advanceMemoryTest: (elapsedSeconds: number) => void;
    stopMemoryTest: (reason: "manual" | "duration") => void;
    finalizeMemoryTest: (result: DiagnosticResult) => void;
    storageTestResults: StorageTestResults;
    recordStorageTestResult: (result: StorageTestResult) => void;
    finalizeStorageTest: (result: DiagnosticResult) => void;
    browserPerformanceTest: BrowserPerformanceTestState;
    setBrowserPerformanceBenchmarks: (benchmarks: BrowserBenchmarkId[]) => void;
    setBrowserPerformanceTabCount: (count: BrowserTabCount) => void;
    setBrowserPerformanceDuration: (duration: BrowserTestDuration) => void;
    startBrowserPerformanceTest: () => void;
    advanceBrowserPerformanceTest: (elapsedSeconds: number) => void;
    stopBrowserPerformanceTest: () => void;
    manualFunctionalChecks: ManualFunctionalChecksState;
    updateManualCheck: (category: ManualCheckCategoryId, updates: Partial<ManualCheckRecord>) => void;
    completeManualCheck: (category: ManualCheckCategoryId) => void;
    recordKeyboardKey: (code: string) => void;
    toggleFaultyKeyboardKey: (code: string) => void;
    addManualPort: (type: string, customName?: string) => void;
    updateManualPort: (portId: string, updates: Partial<PortCheckRecord>) => void;
    completeManualPort: (portId: string) => void;
    skipManualPort: (portId: string) => void;
    finalizeManualPorts: () => void;
}

const DemoInspectionContext = createContext<DemoInspectionState | null>(null);

export function DemoInspectionProvider({ children }: { children: ReactNode }) {
    const [assetTag, setAssetTag] = useState("");
    const [technicianName, setTechnicianName] = useState("");
    const [deviceConfirmed, setDeviceConfirmed] = useState(false);
    const [physicalAssessments, setPhysicalAssessments] = useState(createInitialPhysicalAssessments);
    const [generalObservations, setGeneralObservations] = useState("");
    const [diagnosticResults, setDiagnosticResults] = useState(createInitialDiagnosticResults);
    const [cpuStressTest, setCpuStressTest] = useState(createInitialCpuStressTest);
    const [memoryTest, setMemoryTest] = useState(createInitialMemoryTest);
    const [storageTestResults, setStorageTestResults] = useState(createInitialStorageTestResults);
    const [browserPerformanceTest, setBrowserPerformanceTest] = useState(createInitialBrowserPerformanceTest);
    const [manualFunctionalChecks, setManualFunctionalChecks] = useState(createInitialManualFunctionalChecks);
    const confirmDevice = useCallback(() => setDeviceConfirmed(true), []);
    const updatePhysicalAssessment = useCallback(
        (areaId: PhysicalInspectionAreaId, assessment: PhysicalAreaAssessment) => {
            setPhysicalAssessments((current) => ({ ...current, [areaId]: assessment }));
        },
        [],
    );
    const updateDiagnosticResult = useCallback(
        (id: DiagnosticId, result: DiagnosticResult) => {
            setDiagnosticResults((current) => ({ ...current, [id]: result }));
        },
        [],
    );
    const prepareCpuStressTest = useCallback(() => {
        setCpuStressTest((current) => current.status === "Not Started"
            ? { ...current, status: "Ready" }
            : current);
    }, []);
    const startCpuStressTest = useCallback(() => {
        setCpuStressTest((current) => {
            if (current.status !== "Ready" && current.status !== "Not Started") return current;
            const initialReading = createCpuTemperatureReading(0);
            return {
                ...current,
                status: "Running",
                elapsedSeconds: 0,
                readings: [initialReading],
                currentTemperatureC: initialReading.temperatureC,
                maximumTemperatureC: initialReading.temperatureC,
                cpuUtilisationPercent: initialReading.cpuUtilisationPercent,
                stopReason: null,
                finalResult: null,
            };
        });
    }, []);
    const appendCpuStressReading = useCallback((reading: CpuTemperatureReading) => {
        setCpuStressTest((current) => {
            if (current.status !== "Running" || reading.elapsedSeconds <= current.elapsedSeconds) {
                return current;
            }
            return {
                ...current,
                elapsedSeconds: reading.elapsedSeconds,
                readings: [...current.readings, reading],
                currentTemperatureC: reading.temperatureC,
                maximumTemperatureC: Math.max(current.maximumTemperatureC ?? reading.temperatureC, reading.temperatureC),
                cpuUtilisationPercent: reading.cpuUtilisationPercent,
            };
        });
    }, []);
    const stopCpuStressTest = useCallback((reason: "manual" | "duration") => {
        setCpuStressTest((current) => current.status === "Running"
            ? { ...current, status: "Stopped", stopReason: reason }
            : current);
    }, []);
    const finalizeCpuStressTest = useCallback((result: DiagnosticResult) => {
        setCpuStressTest((current) => ({
            ...current,
            status: "Finalized",
            finalResult: result,
        }));
        setDiagnosticResults((current) => ({ ...current, cpu: result }));
    }, []);
    const prepareMemoryTest = useCallback(() => {
        setMemoryTest((current) => current.status === "Not Started"
            ? { ...current, status: "Ready" }
            : current);
    }, []);
    const selectMemoryTestDuration = useCallback((seconds: number) => {
        setMemoryTest((current) => {
            if (current.status !== "Not Started" && current.status !== "Ready") return current;
            return {
                ...current,
                status: "Ready",
                selectedDurationSeconds: seconds,
                durationConfirmed: false,
            };
        });
    }, []);
    const confirmMemoryTestDuration = useCallback(() => {
        setMemoryTest((current) => current.status === "Ready"
            ? { ...current, durationConfirmed: true }
            : current);
    }, []);
    const startMemoryTest = useCallback(() => {
        setMemoryTest((current) => {
            if (current.status !== "Ready" || !current.durationConfirmed) return current;
            return {
                ...current,
                status: "Running",
                elapsedSeconds: 0,
                errorsDetected: 0,
                stopReason: null,
                finalResult: null,
            };
        });
    }, []);
    const advanceMemoryTest = useCallback((elapsedSeconds: number) => {
        setMemoryTest((current) => {
            if (current.status !== "Running" || elapsedSeconds <= current.elapsedSeconds) return current;
            const elapsed = Math.min(elapsedSeconds, current.selectedDurationSeconds);
            const completed = elapsed >= current.selectedDurationSeconds;
            return {
                ...current,
                status: completed ? "Stopped" : current.status,
                elapsedSeconds: elapsed,
                stopReason: completed ? "duration" : current.stopReason,
            };
        });
    }, []);
    const stopMemoryTest = useCallback((reason: "manual" | "duration") => {
        setMemoryTest((current) => current.status === "Running"
            ? { ...current, status: "Stopped", stopReason: reason }
            : current);
    }, []);
    const finalizeMemoryTest = useCallback((result: DiagnosticResult) => {
        setMemoryTest((current) => ({
            ...current,
            status: "Finalized",
            finalResult: result,
        }));
        setDiagnosticResults((current) => ({ ...current, memory: result }));
    }, []);
    const recordStorageTestResult = useCallback((result: StorageTestResult) => {
        setStorageTestResults((current) => ({
            ...current,
            [result.driveId]: {
                ...current[result.driveId],
                [result.testId]: result,
            },
        }));
    }, []);
    const finalizeStorageTest = useCallback((result: DiagnosticResult) => {
        setDiagnosticResults((current) => ({ ...current, storage: result }));
    }, []);
    const setBrowserPerformanceBenchmarks = useCallback((benchmarks: BrowserBenchmarkId[]) => {
        setBrowserPerformanceTest((current) => current.status === "Running"
            ? current
            : {
                ...current,
                selectedBenchmarks: benchmarks,
                status: "Ready",
                elapsedSeconds: 0,
                finalResult: null,
            });
    }, []);
    const setBrowserPerformanceTabCount = useCallback((count: BrowserTabCount) => {
        setBrowserPerformanceTest((current) => current.status === "Running"
            ? current
            : {
                ...current,
                selectedTabCount: count,
                status: "Ready",
                elapsedSeconds: 0,
                finalResult: null,
            });
    }, []);
    const setBrowserPerformanceDuration = useCallback((duration: BrowserTestDuration) => {
        setBrowserPerformanceTest((current) => current.status === "Running"
            ? current
            : {
                ...current,
                selectedDurationMinutes: duration,
                status: "Ready",
                elapsedSeconds: 0,
                finalResult: null,
            });
    }, []);
    const startBrowserPerformanceTest = useCallback(() => {
        setBrowserPerformanceTest((current) => current.status === "Running" || current.selectedBenchmarks.length === 0
            ? current
            : {
                ...current,
                status: "Running",
                elapsedSeconds: 0,
                finalResult: null,
            });
    }, []);
    const advanceBrowserPerformanceTest = useCallback((elapsedSeconds: number) => {
        setBrowserPerformanceTest((current) => {
            if (current.status !== "Running" || elapsedSeconds <= current.elapsedSeconds) return current;
            const durationSeconds = current.selectedDurationMinutes * 60;
            const elapsed = Math.min(elapsedSeconds, durationSeconds);
            const completed = elapsed >= durationSeconds;
            const next = {
                ...current,
                status: completed ? "Completed" as const : current.status,
                elapsedSeconds: elapsed,
            };
            return {
                ...next,
                finalResult: completed ? createDemoBrowserPerformanceResult(next, true) : current.finalResult,
            };
        });
    }, []);
    const stopBrowserPerformanceTest = useCallback(() => {
        setBrowserPerformanceTest((current) => current.status === "Running"
            ? {
                ...current,
                status: "Stopped",
                finalResult: createDemoBrowserPerformanceResult(current, false),
            }
            : current);
    }, []);
    const updateManualCheck = useCallback(
        (category: ManualCheckCategoryId, updates: Partial<ManualCheckRecord>) => {
            setManualFunctionalChecks((current) => ({
                ...current,
                checks: {
                    ...current.checks,
                    [category]: { ...current.checks[category], ...updates, completed: false },
                },
            }));
        },
        [],
    );
    const completeManualCheck = useCallback((category: ManualCheckCategoryId) => {
        setManualFunctionalChecks((current) => {
            const record = current.checks[category];
            if (record.result === null) return current;
            return {
                ...current,
                checks: {
                    ...current.checks,
                    [category]: { ...record, completed: true },
                },
            };
        });
    }, []);
    const recordKeyboardKey = useCallback((code: string) => {
        setManualFunctionalChecks((current) => current.testedKeyCodes.includes(code)
            ? current
            : { ...current, testedKeyCodes: [...current.testedKeyCodes, code] });
    }, []);
    const toggleFaultyKeyboardKey = useCallback((code: string) => {
        setManualFunctionalChecks((current) => ({
            ...current,
            faultyKeyCodes: current.faultyKeyCodes.includes(code)
                ? current.faultyKeyCodes.filter((keyCode) => keyCode !== code)
                : [...current.faultyKeyCodes, code],
        }));
    }, []);
    const addManualPort = useCallback((type: string, customName?: string) => {
        setManualFunctionalChecks((current) => {
            const portNumber = current.ports.filter((port) => port.type === type).length + 1;
            const label = type === "Other"
                ? customName?.trim() || `Other ${portNumber}`
                : `${type} ${portNumber}`;
            const port: PortCheckRecord = {
                id: `manual-port-${current.ports.length + 1}`,
                type,
                label,
                result: null,
                notes: "",
                completed: false,
                skipped: false,
            };
            return {
                ...current,
                ports: [...current.ports, port],
                portsFinalized: false,
            };
        });
    }, []);
    const updateManualPort = useCallback((portId: string, updates: Partial<PortCheckRecord>) => {
        setManualFunctionalChecks((current) => ({
            ...current,
            portsFinalized: false,
            ports: current.ports.map((port) => port.id === portId
                ? { ...port, ...updates, completed: false, skipped: false }
                : port),
        }));
    }, []);
    const completeManualPort = useCallback((portId: string) => {
        setManualFunctionalChecks((current) => ({
            ...current,
            ports: current.ports.map((port) => port.id === portId && port.result !== null
                ? { ...port, completed: true, skipped: false }
                : port),
        }));
    }, []);
    const skipManualPort = useCallback((portId: string) => {
        setManualFunctionalChecks((current) => ({
            ...current,
            portsFinalized: false,
            ports: current.ports.map((port) => port.id === portId
                ? { ...port, result: null, completed: false, skipped: true }
                : port),
        }));
    }, []);
    const finalizeManualPorts = useCallback(() => {
        setManualFunctionalChecks((current) => ({ ...current, portsFinalized: true }));
    }, []);
    const value = useMemo(
        () => ({
            assetTag,
            setAssetTag,
            technicianName,
            setTechnicianName,
            deviceConfirmed,
            confirmDevice,
            physicalAssessments,
            updatePhysicalAssessment,
            generalObservations,
            setGeneralObservations,
            diagnosticResults,
            updateDiagnosticResult,
            cpuStressTest,
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
            finalizeMemoryTest,
            storageTestResults,
            recordStorageTestResult,
            finalizeStorageTest,
            browserPerformanceTest,
            setBrowserPerformanceBenchmarks,
            setBrowserPerformanceTabCount,
            setBrowserPerformanceDuration,
            startBrowserPerformanceTest,
            advanceBrowserPerformanceTest,
            stopBrowserPerformanceTest,
            manualFunctionalChecks,
            updateManualCheck,
            completeManualCheck,
            recordKeyboardKey,
            toggleFaultyKeyboardKey,
            addManualPort,
            updateManualPort,
            completeManualPort,
            skipManualPort,
            finalizeManualPorts,
        }),
        [
            assetTag,
            technicianName,
            deviceConfirmed,
            confirmDevice,
            physicalAssessments,
            updatePhysicalAssessment,
            generalObservations,
            diagnosticResults,
            updateDiagnosticResult,
            cpuStressTest,
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
            finalizeMemoryTest,
            storageTestResults,
            recordStorageTestResult,
            finalizeStorageTest,
            browserPerformanceTest,
            setBrowserPerformanceBenchmarks,
            setBrowserPerformanceTabCount,
            setBrowserPerformanceDuration,
            startBrowserPerformanceTest,
            advanceBrowserPerformanceTest,
            stopBrowserPerformanceTest,
            manualFunctionalChecks,
            updateManualCheck,
            completeManualCheck,
            recordKeyboardKey,
            toggleFaultyKeyboardKey,
            addManualPort,
            updateManualPort,
            completeManualPort,
            skipManualPort,
            finalizeManualPorts,
        ],
    );

    return (
        <DemoInspectionContext.Provider value={value}>
            {children}
        </DemoInspectionContext.Provider>
    );
}

export function useDemoInspection() {
    const context = useContext(DemoInspectionContext);
    if (!context) {
        throw new Error("useDemoInspection must be used within DemoInspectionProvider.");
    }
    return context;
}
