import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    Activity,
    Battery,
    Cpu,
    Eye,
    Gauge,
    HardDrive,
    MemoryStick,
    Monitor,
    Network,
    Play,
    Thermometer,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "../components/ui/dialog";
import InspectionProgress from "../components/shared/InspectionProgress";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice, getTotalInstalledRamGb, getTotalInstalledStorageGb } from "../demo/demoDevice";
import {
    hardwareDiagnosticDefinitions,
    isHardwareDiagnosticsComplete,
    type DiagnosticId,
    type DiagnosticResult,
    type DiagnosticStatus,
} from "../demo/hardwareDiagnostics";
import { isPhysicalAssessmentComplete } from "../demo/physicalAssessment";
import "./hardware-diagnostics.css";

const categoryIcons: Record<DiagnosticId, LucideIcon> = {
    cpu: Cpu,
    memory: MemoryStick,
    storage: HardDrive,
    graphics: Activity,
    battery: Battery,
    display: Monitor,
    network: Network,
    sensors: Thermometer,
};

const statusClassNames: Record<DiagnosticStatus, string> = {
    PASS: "is-pass",
    FAIL: "is-fail",
    WARNING: "is-warning",
    INCONCLUSIVE: "is-inconclusive",
    UNSUPPORTED: "is-unsupported",
    BLOCKED: "is-blocked",
    CANCELLED: "is-cancelled",
    "NOT RUN": "is-not-run",
};

const statusOrder: DiagnosticStatus[] = [
    "PASS",
    "FAIL",
    "WARNING",
    "INCONCLUSIVE",
    "UNSUPPORTED",
    "BLOCKED",
    "CANCELLED",
    "NOT RUN",
];

function DiagnosticStatusBadge({ status }: { status: DiagnosticStatus }) {
    return (
        <span className={`hardware-diagnostics-status ${statusClassNames[status]}`}>
            {status}
        </span>
    );
}

function DetailsList({ details }: { details: Array<{ label: string; value: string }> }) {
    return (
        <dl className="hardware-diagnostics-details">
            {details.map((detail) => (
                <div key={detail.label}>
                    <dt>{detail.label}</dt>
                    <dd>{detail.value}</dd>
                </div>
            ))}
        </dl>
    );
}

function ResultSummary({
    counts,
}: {
    counts: Record<DiagnosticStatus, number>;
}) {
    const otherCount = counts.INCONCLUSIVE + counts.UNSUPPORTED + counts.BLOCKED + counts.CANCELLED;
    const otherStatuses = statusOrder
        .filter((status) => ["INCONCLUSIVE", "UNSUPPORTED", "BLOCKED", "CANCELLED"].includes(status) && counts[status] > 0)
        .map((status) => `${status} ${counts[status]}`);

    return (
        <section className="hardware-diagnostics-summary" aria-labelledby="diagnostic-summary-title">
            <div className="hardware-diagnostics-section-heading">
                <div>
                    <h2 id="diagnostic-summary-title">Diagnostic Summary</h2>
                    <p>Counts are calculated from the current demo test records.</p>
                </div>
            </div>
            <dl className="hardware-diagnostics-summary-grid">
                <div><dt>Total Tests</dt><dd>{hardwareDiagnosticDefinitions.length}</dd></div>
                <div className="is-pass"><dt>Passed</dt><dd>{counts.PASS}</dd></div>
                <div className="is-fail"><dt>Failed</dt><dd>{counts.FAIL}</dd></div>
                <div className="is-warning"><dt>Warning</dt><dd>{counts.WARNING}</dd></div>
                <div className="is-not-run"><dt>Not Run</dt><dd>{counts["NOT RUN"]}</dd></div>
            </dl>
            {otherCount > 0 && (
                <p className="hardware-diagnostics-other-counts">
                    Other outcomes: {otherStatuses.join(" · ")}
                </p>
            )}
        </section>
    );
}

function DiagnosticDetails({
    definition,
    result,
    onClose,
}: {
    definition: (typeof hardwareDiagnosticDefinitions)[number];
    result: DiagnosticResult;
    onClose: () => void;
}) {
    return (
        <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
            <DialogContent className="hardware-diagnostics-dialog">
                <DialogHeader>
                    <DialogTitle>{definition.testName}</DialogTitle>
                    <DialogDescription>
                        Demo result only. No actual hardware test or sensor reading was performed.
                    </DialogDescription>
                </DialogHeader>

                <div className="hardware-diagnostics-dialog-body">
                    <section className="hardware-diagnostics-result-heading">
                        <div>
                            <span>Test status</span>
                            <DiagnosticStatusBadge status={result.status} />
                        </div>
                        <strong>{definition.hardwareName}</strong>
                    </section>

                    <section className="hardware-diagnostics-dialog-section">
                        <h3>Hardware information</h3>
                        <DetailsList details={definition.hardwareDetails} />
                    </section>

                    <section className="hardware-diagnostics-dialog-section">
                        <h3>Result summary</h3>
                        <p>{result.summary}</p>
                    </section>

                    {result.measurements.length > 0 && (
                        <section className="hardware-diagnostics-dialog-section">
                            <h3>Demo measurements</h3>
                            <DetailsList details={result.measurements} />
                        </section>
                    )}

                    {result.observations.length > 0 && (
                        <section className="hardware-diagnostics-observations">
                            <h3>Warnings and observations</h3>
                            <ul>{result.observations.map((observation) => <li key={observation}>{observation}</li>)}</ul>
                        </section>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}

export default function HardwareDiagnostics() {
    const navigate = useNavigate();
    const {
        deviceConfirmed,
        physicalAssessments,
        diagnosticResults,
        updateDiagnosticResult,
        cpuStressTest,
        memoryTest,
    } = useDemoInspection();
    const [runningDiagnosticId, setRunningDiagnosticId] = useState<DiagnosticId | null>(null);
    const [selectedDiagnosticId, setSelectedDiagnosticId] = useState<DiagnosticId | null>(null);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const totalRamGb = getTotalInstalledRamGb(demoDevice);
    const totalStorageGb = getTotalInstalledStorageGb(demoDevice);
    const diagnosticComplete = isHardwareDiagnosticsComplete(diagnosticResults);
    const counts: Record<DiagnosticStatus, number> = {
        PASS: 0,
        FAIL: 0,
        WARNING: 0,
        INCONCLUSIVE: 0,
        UNSUPPORTED: 0,
        BLOCKED: 0,
        CANCELLED: 0,
        "NOT RUN": 0,
    };
    for (const definition of hardwareDiagnosticDefinitions) {
        counts[diagnosticResults[definition.id].status] += 1;
    }
    const selectedDefinition = hardwareDiagnosticDefinitions.find(
        (definition) => definition.id === selectedDiagnosticId,
    );

    useEffect(() => () => {
        if (timerRef.current !== null) clearTimeout(timerRef.current);
    }, []);

    function runTest(definition: (typeof hardwareDiagnosticDefinitions)[number]) {
        const simulatedResult = definition.simulatedResult;
        if (!simulatedResult || runningDiagnosticId !== null) return;

        setRunningDiagnosticId(definition.id);
        timerRef.current = setTimeout(() => {
            updateDiagnosticResult(definition.id, simulatedResult);
            setRunningDiagnosticId(null);
            timerRef.current = null;
            setSelectedDiagnosticId(definition.id);
        }, 700);
    }

    return (
        <main className="hardware-diagnostics page-flow" aria-labelledby="hardware-diagnostics-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">DEVICE INSPECTION</span>
                    <h1 className="page-title" id="hardware-diagnostics-title">Hardware Diagnostics</h1>
                    <p className="page-description">
                        Run automated tests to assess the functional condition of the device hardware.
                    </p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <InspectionProgress
                activeStage={2}
                deviceConfirmed={deviceConfirmed}
                physicalAssessmentComplete={isPhysicalAssessmentComplete(physicalAssessments)}
                diagnosticsComplete={diagnosticComplete}
            />

            <section className="hardware-diagnostics-device-summary" aria-label="Current device summary">
                <strong>{demoDevice.manufacturer} {demoDevice.model}</strong>
                <span>{demoDevice.processor.manufacturer} {demoDevice.processor.model}</span>
                <span>{totalRamGb} GB RAM</span>
                <span>{totalStorageGb} GB storage</span>
            </section>

            <section className="browser-performance-entry" aria-labelledby="browser-performance-entry-title">
                <div>
                    <span className="browser-performance-entry-icon"><Gauge size={17} aria-hidden="true" /></span>
                    <div>
                        <h2 id="browser-performance-entry-title">Browser Performance Test</h2>
                        <p>Run a separate, frontend-only demo with deterministic sample scores. It does not affect hardware diagnostic results.</p>
                    </div>
                </div>
                <Link className="button button-secondary" to="/browser-performance-test">
                    OPEN BROWSER PERFORMANCE TEST
                </Link>
            </section>

            <ResultSummary counts={counts} />

            <section aria-labelledby="hardware-category-title">
                <div className="hardware-diagnostics-section-heading hardware-diagnostics-category-heading">
                    <div>
                        <h2 id="hardware-category-title">Hardware Categories</h2>
                        <p>Simulated results are predefined demo values, not actual device tests.</p>
                    </div>
                </div>

                <div className="hardware-diagnostics-card-grid">
                    {hardwareDiagnosticDefinitions.map((definition) => {
                        const Icon = categoryIcons[definition.id];
                        const result = diagnosticResults[definition.id];
                        const isRunning = runningDiagnosticId === definition.id;
                        const isCpu = definition.id === "cpu";
                        const isMemory = definition.id === "memory";
                        const isStorage = definition.id === "storage";
                        const cpuTestFinalized = cpuStressTest.status === "Finalized";
                        const memoryTestFinalized = memoryTest.status === "Finalized";
                        const storageTestFinalized = result.status === "INCONCLUSIVE" || result.status === "NOT RUN";
                        const canRun = result.status === "NOT RUN" && definition.simulatedResult !== null;
                        const cpuTestAction = isCpu && !cpuTestFinalized;
                        const memoryTestAction = isMemory && !memoryTestFinalized;
                        const storageTestAction = isStorage && !storageTestFinalized;
                        const hasDedicatedTestAction = cpuTestAction || memoryTestAction || storageTestAction;
                        const actionLabel = isCpu
                            ? cpuTestAction ? "RUN CPU STRESS TEST" : "View Details"
                            : isMemory
                                ? memoryTestFinalized ? "View Memory Test" : "RUN MEMORY TEST"
                                : isStorage
                                    ? storageTestFinalized ? "View Storage Tests" : "RUN STORAGE TEST"
                                    : canRun ? "Run Test" : "View Details";

                        return (
                            <article className="hardware-diagnostics-card" key={definition.id}>
                                <header className="hardware-diagnostics-card-heading">
                                    <div className="hardware-diagnostics-category">
                                        <Icon size={17} aria-hidden="true" />
                                        <div>
                                            <h3>{definition.category}</h3>
                                            <span>{definition.testName}</span>
                                        </div>
                                    </div>
                                    {isRunning
                                        ? <span className="hardware-diagnostics-status is-in-progress">IN PROGRESS</span>
                                        : <DiagnosticStatusBadge status={result.status} />}
                                </header>

                                <p className="hardware-diagnostics-hardware-name">{definition.hardwareName}</p>
                                <DetailsList details={definition.hardwareDetails} />
                                {((isCpu && cpuTestFinalized)
                                    || (isMemory && memoryTestFinalized)
                                    || (isStorage && storageTestFinalized))
                                    && result.measurements.length > 0 && (
                                    <DetailsList details={result.measurements} />
                                )}

                                <p className="hardware-diagnostics-result-summary">
                                    {isRunning ? "Test in Progress — preparing the deterministic demo result." : result.summary}
                                </p>

                                <footer className="hardware-diagnostics-card-footer">
                                    <span>Demo data</span>
                                    <button
                                        className={`button ${canRun || hasDedicatedTestAction ? "button-primary" : "button-secondary"} hardware-diagnostics-action`}
                                        type="button"
                                        disabled={isRunning || (runningDiagnosticId !== null && (canRun || hasDedicatedTestAction))}
                                        onClick={() => {
                                            if (isCpu && !cpuTestFinalized) {
                                                navigate("/cpu-stress-test");
                                            } else if (isMemory) {
                                                navigate("/memory-test");
                                            } else if (isStorage) {
                                                navigate("/storage-test");
                                            } else if (canRun) {
                                                runTest(definition);
                                            } else {
                                                setSelectedDiagnosticId(definition.id);
                                            }
                                        }}
                                    >
                                        {isRunning ? <Activity size={14} aria-hidden="true" /> : canRun || hasDedicatedTestAction ? <Play size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
                                        {isRunning ? "Test in Progress" : actionLabel}
                                    </button>
                                </footer>
                            </article>
                        );
                    })}
                </div>
            </section>

            <footer className="hardware-diagnostics-actions">
                <Link className="button button-secondary" to="/physical-assessment">
                    BACK TO PHYSICAL ASSESSMENT
                </Link>
                <div>
                    {!diagnosticComplete && (
                        <span className="hardware-diagnostics-completion-hint">
                            Run each available test to complete this stage.
                        </span>
                    )}
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={!diagnosticComplete}
                        onClick={() => navigate("/technician-checks")}
                    >
                        CONTINUE TO TECHNICIAN CHECKS
                    </button>
                </div>
            </footer>

            {selectedDefinition && (
                <DiagnosticDetails
                    definition={selectedDefinition}
                    result={diagnosticResults[selectedDefinition.id]}
                    onClose={() => setSelectedDiagnosticId(null)}
                />
            )}
        </main>
    );
}
