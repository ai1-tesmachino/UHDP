import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import {
    createStorageDiagnosticResult,
    createStorageTestResult,
    demoStorageDrives,
    storageTestDefinitions,
    type StorageTestId,
} from "../demo/memoryStorageTests";
import "./memory-storage-tests.css";

function formatCapacity(capacityGb: number): string {
    return capacityGb >= 1000 ? `${(capacityGb / 1000).toFixed(2)} TB` : `${capacityGb} GB`;
}

export default function StorageTest() {
    const navigate = useNavigate();
    const {
        storageTestResults,
        recordStorageTestResult,
        finalizeStorageTest,
    } = useDemoInspection();
    const [selectedDriveId, setSelectedDriveId] = useState(demoStorageDrives[0]?.id ?? "");
    const [selectedMethodId, setSelectedMethodId] = useState<StorageTestId>("smart-health");
    const [activeMethodId, setActiveMethodId] = useState<StorageTestId | null>(null);
    const [progressPercent, setProgressPercent] = useState(0);
    const [confirmFinalize, setConfirmFinalize] = useState(false);
    const [sourceFile, setSourceFile] = useState<{ name: string; size: number } | null>(null);
    const progressTimerRef = useRef<number | null>(null);
    const activeMethodRef = useRef<StorageTestId | null>(null);

    const selectedDrive = demoStorageDrives.find((drive) => drive.id === selectedDriveId) ?? null;
    const driveResults = selectedDrive ? storageTestResults[selectedDrive.id] ?? {} : {};
    const selectedMethod = storageTestDefinitions.find((test) => test.id === selectedMethodId) ?? storageTestDefinitions[0];
    const selectedResult = driveResults[selectedMethod.id];
    const driveDetails = useMemo(() => selectedDrive ? [
        { label: "Model", value: selectedDrive.model },
        { label: "Physical capacity", value: formatCapacity(selectedDrive.capacityGb) },
        { label: "Drive type", value: selectedDrive.type },
        { label: "Interface", value: selectedDrive.interface },
        { label: "Serial number", value: selectedDrive.serialNumber ?? "Not Available" },
    ] : [], [selectedDrive]);

    useEffect(() => () => {
        if (progressTimerRef.current !== null) window.clearInterval(progressTimerRef.current);
    }, []);

    function runSelectedTest() {
        if (!selectedDrive || activeMethodRef.current !== null) return;
        const methodId = selectedMethod.id;
        activeMethodRef.current = methodId;
        setActiveMethodId(methodId);
        setProgressPercent(0);
        let progress = 0;
        progressTimerRef.current = window.setInterval(() => {
            progress = Math.min(progress + 10, 100);
            setProgressPercent(progress);
            if (progress < 100) return;
            if (progressTimerRef.current !== null) window.clearInterval(progressTimerRef.current);
            progressTimerRef.current = null;
            recordStorageTestResult(createStorageTestResult(
                methodId,
                selectedDrive,
                sourceFile ? `${sourceFile.name} (${sourceFile.size} bytes; metadata only)` : undefined,
            ));
            activeMethodRef.current = null;
            setActiveMethodId(null);
        }, 120);
    }

    function finalizeTests() {
        if (!selectedDrive || activeMethodRef.current !== null) return;
        finalizeStorageTest(createStorageDiagnosticResult(selectedDrive, driveResults));
        setConfirmFinalize(false);
        navigate("/hardware-diagnostics");
    }

    return (
        <main className="memory-storage-test page-flow" aria-labelledby="storage-test-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">HARDWARE DIAGNOSTICS</span>
                    <h1 className="page-title" id="storage-test-title">Storage Test</h1>
                    <p className="page-description">Review individual simulated checks for a physical drive. No storage operations are performed.</p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <section className="memory-storage-device-card" aria-labelledby="storage-device-title">
                <header className="memory-storage-section-heading">
                    <div>
                        <h2 id="storage-device-title">Physical Drive</h2>
                        <p>Select a physical device from the Phase 1 inventory. Partitions are not shown.</p>
                    </div>
                    <span className="memory-storage-demo-label">DEMO INVENTORY</span>
                </header>
                {demoStorageDrives.length > 1 && (
                    <div className="storage-test-drive-options" role="radiogroup" aria-label="Select physical drive">
                        {demoStorageDrives.map((drive, index) => (
                            <label key={drive.id} className="memory-storage-duration-option">
                                <input
                                    type="radio"
                                    name="storage-test-drive"
                                    value={drive.id}
                                    checked={selectedDriveId === drive.id}
                                    disabled={activeMethodId !== null}
                                    onChange={() => setSelectedDriveId(drive.id)}
                                />
                                <span>Drive {index + 1}: {drive.model}</span>
                            </label>
                        ))}
                    </div>
                )}
                {selectedDrive
                    ? <dl className="memory-storage-device-summary">{driveDetails.map((detail) => <div key={detail.label}><dt>{detail.label}</dt><dd>{detail.value}</dd></div>)}</dl>
                    : <p className="memory-storage-empty-state">No physical drives are available in the device inventory.</p>}
            </section>

            <aside className="storage-test-guidance">
                <strong>New or empty drive?</strong>
                <span>Use WRITE AND READ-BACK TEST or FILE COPY AND VERIFICATION with generated demo test data. Existing user files are not required.</span>
            </aside>

            <section aria-labelledby="storage-methods-title">
                <header className="memory-storage-section-heading">
                    <div>
                        <h2 id="storage-methods-title">Select a Test Method</h2>
                        <p>Each method is recorded separately for the selected physical drive. A passing method does not pass the whole device.</p>
                    </div>
                </header>
                <div className="storage-test-method-grid">
                    {storageTestDefinitions.map((test) => {
                        const result = driveResults[test.id];
                        const isActive = activeMethodId === test.id;
                        const status = isActive ? "IN PROGRESS" : result?.status ?? "NOT RUN";
                        return (
                            <button
                                className={`storage-test-method-card${selectedMethodId === test.id ? " is-selected" : ""}`}
                                type="button"
                                key={test.id}
                                aria-pressed={selectedMethodId === test.id}
                                disabled={activeMethodId !== null}
                                onClick={() => setSelectedMethodId(test.id)}
                            >
                                <span className="storage-test-method-heading">
                                    <strong>{test.name}</strong>
                                    <span className={`memory-storage-status ${isActive ? "is-running" : result ? `is-result-${result.status.toLowerCase().replaceAll(" ", "-")}` : "is-not-started"}`}>{status}</span>
                                </span>
                                <span className="storage-test-method-purpose">{test.purpose}</span>
                            </button>
                        );
                    })}
                </div>
            </section>

            <section className="memory-storage-control-card" aria-labelledby="storage-selected-method-title">
                <header className="memory-storage-section-heading">
                    <div>
                        <h2 id="storage-selected-method-title">{selectedMethod.name}</h2>
                        <p>{selectedMethod.purpose}</p>
                    </div>
                    <span className="memory-storage-demo-label">SIMULATED TEST — DEMO DATA</span>
                </header>
                <p className="storage-test-guidance-text">{selectedMethod.guidance}</p>

                {selectedMethod.id === "file-copy-verification" && (
                    <div className="storage-test-source">
                        <label className="memory-storage-confirm-duration">
                            <input type="radio" name="copy-source" checked={sourceFile === null} onChange={() => setSourceFile(null)} />
                            Use generated demo test data
                        </label>
                        <label className="storage-test-file-picker">
                            <span>{sourceFile ? "Choose a different source file" : "Choose a source file (demo metadata only)"}</span>
                            <input
                                type="file"
                                aria-label="Choose source file; only its filename and size are used"
                                onChange={(event) => {
                                    const file = event.target.files?.[0];
                                    setSourceFile(file ? { name: file.name, size: file.size } : null);
                                }}
                            />
                        </label>
                        {sourceFile && <p className="storage-test-selected-file">Selected: {sourceFile.name} · {sourceFile.size} bytes (metadata only; contents are not read or uploaded)</p>}
                    </div>
                )}

                {activeMethodId !== null && (
                    <div className="memory-storage-progress">
                        <div className="memory-storage-progress-label">
                            <span>{selectedMethod.name} simulation progress</span>
                            <strong>{progressPercent}%</strong>
                        </div>
                        <div
                            className="memory-storage-progress-track"
                            role="progressbar"
                            aria-label={`${selectedMethod.name} simulation progress`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={progressPercent}
                        >
                            <span style={{ width: `${progressPercent}%` }} />
                        </div>
                    </div>
                )}

                {selectedResult && (
                    <section className="storage-test-result" aria-live="polite">
                        <header>
                            <h3>Recorded Demo Result</h3>
                            <span className={`memory-storage-status is-result-${selectedResult.status.toLowerCase().replaceAll(" ", "-")}`}>{selectedResult.status}</span>
                        </header>
                        <p>{selectedResult.summary}</p>
                        <dl className="memory-storage-device-summary">
                            {[
                                { label: "Test", value: selectedResult.testName },
                                { label: "Drive tested", value: selectedDrive?.model ?? "Not Available" },
                                { label: "Test duration", value: `${selectedResult.durationSeconds} seconds (demo)` },
                                ...selectedResult.measurements,
                            ].map((detail, index) => <div key={`${detail.label}-${index}`}><dt>{detail.label}</dt><dd>{detail.value}</dd></div>)}
                        </dl>
                        {selectedResult.observations.length > 0 && (
                            <ul>{selectedResult.observations.map((observation) => <li key={observation}>{observation}</li>)}</ul>
                        )}
                    </section>
                )}

                <div className="storage-test-method-actions">
                    <span>Results are simulated. No actual drive reads, writes, SMART queries or filesystem operations occur.</span>
                    <button className="button button-primary" type="button" disabled={!selectedDrive || activeMethodId !== null} onClick={runSelectedTest}>
                        {activeMethodId === selectedMethod.id ? "TEST IN PROGRESS" : "RUN SELECTED TEST"}
                    </button>
                </div>
            </section>

            <footer className="memory-storage-actions">
                <Link className="button button-secondary" to="/hardware-diagnostics">BACK TO HARDWARE DIAGNOSTICS</Link>
                <button className="button button-primary" type="button" disabled={!selectedDrive || activeMethodId !== null} onClick={() => setConfirmFinalize(true)}>
                    FINALIZE TEST
                </button>
            </footer>

            <Dialog open={confirmFinalize} onOpenChange={setConfirmFinalize}>
                <DialogContent className="memory-storage-confirmation-dialog">
                    <DialogHeader>
                        <DialogTitle>Finalize storage tests?</DialogTitle>
                        <DialogDescription>
                            Individual method results will be preserved for {selectedDrive?.model ?? "the selected drive"}. The overall storage device will not be marked as passed.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="memory-storage-confirmation-actions">
                        <button className="button button-secondary" type="button" onClick={() => setConfirmFinalize(false)}>CANCEL</button>
                        <button className="button button-primary" type="button" onClick={finalizeTests}>FINALIZE AND RETURN</button>
                    </div>
                </DialogContent>
            </Dialog>
        </main>
    );
}
