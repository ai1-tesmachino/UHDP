import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    ArrowLeft,
    Check,
    Keyboard,
    Monitor,
    Mouse,
    Plug,
    RotateCcw,
    Save,
    SkipForward,
    Smartphone,
} from "lucide-react";
import InspectionProgress from "../components/shared/InspectionProgress";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice, getTotalInstalledRamGb, getTotalInstalledStorageGb } from "../demo/demoDevice";
import {
    isManualFunctionalChecksComplete,
    keyboardKeyCount,
    portTypes,
    summarizeManualFunctionalChecks,
    usQwertyKeyboardRows,
    type ManualCheckCategoryId,
    type ManualCheckOutcome,
    type PortCheckOutcome,
} from "../demo/technicianFunctionalChecks";
import { isHardwareDiagnosticsComplete } from "../demo/hardwareDiagnostics";
import { isPhysicalAssessmentComplete } from "../demo/physicalAssessment";
import "./technician-checks.css";

type ActiveCategory = ManualCheckCategoryId | "ports";

const categoryDetails: Array<{
    id: ActiveCategory;
    title: string;
    description: string;
    hardware: string;
    icon: typeof Monitor;
}> = [
    { id: "display", title: "Display", description: "Manually inspect colour, pixels and visible damage.", hardware: `${demoDevice.display.screenSizeInches ?? "Unknown"}″ ${demoDevice.display.resolution ?? "resolution unavailable"}`, icon: Monitor },
    { id: "keyboard", title: "Keyboard", description: "Check physical key response and identify faulty keys.", hardware: `${demoDevice.keyboard.layout} · ${demoDevice.keyboard.type}`, icon: Keyboard },
    { id: "touchscreen", title: "Touchscreen", description: "Manual touch-area and edge responsiveness check.", hardware: demoDevice.display.touchscreenPresent ? "Integrated touchscreen" : "Touchscreen not detected", icon: Smartphone },
    { id: "touchpad", title: "Touchpad", description: "Manually verify movement, buttons, scrolling and gestures.", hardware: demoDevice.touchpad.present ? demoDevice.touchpad.type : "Touchpad not detected", icon: Mouse },
    { id: "ports", title: "Ports", description: "Select physically present ports and inspect each one.", hardware: "Technician-selected ports only", icon: Plug },
];

const displayColors = [
    { name: "White", value: "#ffffff" },
    { name: "Black", value: "#111827" },
    { name: "Red", value: "#ef4444" },
    { name: "Green", value: "#22c55e" },
    { name: "Blue", value: "#3b82f6" },
];

const manualOutcomes: ManualCheckOutcome[] = ["Working correctly", "Issues found", "Unable to verify"];
const touchpadOutcomes: ManualCheckOutcome[] = ["Working correctly", "Partially working", "Not working", "Unable to verify"];
const portOutcomes: PortCheckOutcome[] = ["Working", "Not Working", "Intermittent", "Physically Damaged", "Unable to Verify"];

function outcomeLabel(result: string | null, completed: boolean): string {
    if (result === "Not Applicable") return result;
    if (!result) return "Not Tested";
    return completed ? result : `${result} · Not saved`;
}

function FunctionalCheckCard({
    category,
    status,
    onStart,
}: {
    category: (typeof categoryDetails)[number];
    status: string;
    onStart: () => void;
}) {
    const Icon = category.icon;
    const isNotApplicable = category.id === "touchscreen" && !demoDevice.display.touchscreenPresent;
    return (
        <article className="technician-check-card">
            <header>
                <span className="technician-check-icon"><Icon size={17} aria-hidden="true" /></span>
                <span className={`technician-check-status ${isNotApplicable ? "is-na" : ""}`}>{status}</span>
            </header>
            <div>
                <h3>{category.title}</h3>
                <p className="technician-check-hardware">{category.hardware}</p>
                <p>{category.description}</p>
            </div>
            <button className="button button-secondary" type="button" disabled={isNotApplicable} onClick={onStart}>
                {isNotApplicable ? "NOT APPLICABLE" : "START CHECK"}
            </button>
        </article>
    );
}

function OutcomeButtons({
    options,
    selected,
    onSelect,
}: {
    options: string[];
    selected: string | null;
    onSelect: (value: string) => void;
}) {
    return (
        <div className="technician-outcome-buttons" role="group" aria-label="Manual check result">
            {options.map((option) => (
                <button
                    className={`button ${selected === option ? "button-primary" : "button-secondary"}`}
                    key={option}
                    type="button"
                    aria-pressed={selected === option}
                    onClick={() => onSelect(option)}
                >
                    {option}
                </button>
            ))}
        </div>
    );
}

export default function TechnicianChecks() {
    const {
        deviceConfirmed,
        physicalAssessments,
        diagnosticResults,
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
    } = useDemoInspection();
    const [activeCategory, setActiveCategory] = useState<ActiveCategory | null>(null);
    const [activeColor, setActiveColor] = useState(displayColors[0]);
    const [selectedKeyboardKey, setSelectedKeyboardKey] = useState<string | null>(null);
    const [selectedPortId, setSelectedPortId] = useState<string | null>(null);
    const [newPortType, setNewPortType] = useState<string>(portTypes[0]);
    const [customPortName, setCustomPortName] = useState("");

    const summary = useMemo(() => summarizeManualFunctionalChecks(manualFunctionalChecks), [manualFunctionalChecks]);
    const manualChecksComplete = isManualFunctionalChecksComplete(manualFunctionalChecks);
    const currentPort = manualFunctionalChecks.ports.find((port) => port.id === selectedPortId) ?? null;
    const mappedCodes = useMemo(
        () => new Set(usQwertyKeyboardRows.flatMap((row) => row.map((key) => key.code))),
        [],
    );
    const testedKeys = manualFunctionalChecks.testedKeyCodes.filter((code) => mappedCodes.has(code)).length;
    const faultyKeys = manualFunctionalChecks.faultyKeyCodes.filter((code) => mappedCodes.has(code)).length;

    useEffect(() => {
        if (activeCategory !== "keyboard") return;
        function handleKeyDown(event: KeyboardEvent) {
            const target = event.target;
            if (target instanceof HTMLElement
                && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
            const keyExists = mappedCodes.has(event.code);
            if (!keyExists) return;
            event.preventDefault();
            setSelectedKeyboardKey(event.code);
            recordKeyboardKey(event.code);
        }
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [activeCategory, mappedCodes, recordKeyboardKey]);

    function openCheck(category: ActiveCategory) {
        setActiveCategory(category);
        if (category === "ports") {
            const nextPort = manualFunctionalChecks.ports.find((port) => !port.completed);
            setSelectedPortId(nextPort?.id ?? manualFunctionalChecks.ports[0]?.id ?? null);
        }
    }

    function savePortAndNext() {
        if (!currentPort?.result) return;
        completeManualPort(currentPort.id);
        const ports = manualFunctionalChecks.ports;
        const currentIndex = ports.findIndex((port) => port.id === currentPort.id);
        const nextPort = ports.slice(currentIndex + 1).find((port) => !port.completed);
        setSelectedPortId(nextPort?.id ?? null);
    }

    function skipCurrentPort() {
        if (!currentPort) return;
        skipManualPort(currentPort.id);
        const currentIndex = manualFunctionalChecks.ports.findIndex((port) => port.id === currentPort.id);
        const nextPort = manualFunctionalChecks.ports.slice(currentIndex + 1).find((port) => !port.completed);
        setSelectedPortId(nextPort?.id ?? null);
    }

    function addPort() {
        addManualPort(newPortType, newPortType === "Other" ? customPortName : undefined);
        setCustomPortName("");
    }

    const focusedRecord = activeCategory && activeCategory !== "ports"
        ? manualFunctionalChecks.checks[activeCategory]
        : null;

    return (
        <main className="hardware-diagnostics page-flow technician-checks-page" aria-labelledby="technician-checks-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">DEVICE INSPECTION</span>
                    <h1 className="page-title" id="technician-checks-title">Technician Functional Checks</h1>
                    <p className="page-description">Manually verify the operation of the device components and connections.</p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <InspectionProgress
                activeStage={3}
                deviceConfirmed={deviceConfirmed}
                physicalAssessmentComplete={isPhysicalAssessmentComplete(physicalAssessments)}
                diagnosticsComplete={isHardwareDiagnosticsComplete(diagnosticResults)}
                technicianChecksComplete={manualChecksComplete}
            />

            <section className="hardware-diagnostics-device-summary" aria-label="Current device summary">
                <strong>{demoDevice.manufacturer} {demoDevice.model}</strong>
                <span>{demoDevice.processor.manufacturer} {demoDevice.processor.model}</span>
                <span>{getTotalInstalledRamGb(demoDevice)} GB RAM</span>
                <span>{getTotalInstalledStorageGb(demoDevice)} GB storage</span>
            </section>

            <section className="technician-check-summary" aria-labelledby="technician-summary-title">
                <div className="hardware-diagnostics-section-heading">
                    <div>
                        <h2 id="technician-summary-title">Manual Check Summary</h2>
                        <p>Counts reflect saved technician results and selected physical ports.</p>
                    </div>
                </div>
                <dl>
                    <div><dt>Total selected checks</dt><dd>{summary.totalSelected}</dd></div>
                    <div><dt>Completed</dt><dd>{summary.completed}</dd></div>
                    <div className="is-pass"><dt>Passed</dt><dd>{summary.passed}</dd></div>
                    <div className="is-fail"><dt>Failed</dt><dd>{summary.failed}</dd></div>
                    <div><dt>Unable to verify</dt><dd>{summary.unableToVerify}</dd></div>
                    <div><dt>Not applicable</dt><dd>{summary.notApplicable}</dd></div>
                    <div><dt>Not tested</dt><dd>{summary.notTested}</dd></div>
                </dl>
            </section>

            {activeCategory === null ? (
                <>
                    <section aria-labelledby="technician-checks-heading">
                        <div className="hardware-diagnostics-section-heading">
                            <div>
                                <h2 id="technician-checks-heading">Functional Checks</h2>
                                <p>Opening a check does not record a result. Each outcome is technician-entered.</p>
                            </div>
                        </div>
                        <div className="technician-check-grid">
                            {categoryDetails.map((category) => {
                                const record = category.id === "ports" ? null : manualFunctionalChecks.checks[category.id];
                                const status = category.id === "ports"
                                    ? manualFunctionalChecks.ports.length === 0
                                        ? "Not selected"
                                        : manualFunctionalChecks.portsFinalized
                                            ? "Inspection saved"
                                            : `${manualFunctionalChecks.ports.length} selected`
                                    : outcomeLabel(record?.result ?? null, record?.completed ?? false);
                                return (
                                    <FunctionalCheckCard
                                        key={category.id}
                                        category={category}
                                        status={status}
                                        onStart={() => openCheck(category.id)}
                                    />
                                );
                            })}
                        </div>
                    </section>
                    <footer className="hardware-diagnostics-actions">
                        <Link className="button button-secondary" to="/hardware-diagnostics">BACK TO HARDWARE DIAGNOSTICS</Link>
                        <div>
                            {!manualChecksComplete && <span className="hardware-diagnostics-completion-hint">Complete and save each applicable check before continuing.</span>}
                            <Link
                                className={`button ${manualChecksComplete ? "button-primary" : "button-secondary"} ${manualChecksComplete ? "" : "is-disabled"}`}
                                aria-disabled={!manualChecksComplete}
                                tabIndex={manualChecksComplete ? undefined : -1}
                                to={manualChecksComplete ? "/review-results" : "#"}
                                onClick={(event) => { if (!manualChecksComplete) event.preventDefault(); }}
                            >
                                CONTINUE TO REVIEW RESULTS
                            </Link>
                        </div>
                    </footer>
                </>
            ) : (
                <section className="technician-check-workspace" aria-label={`${activeCategory} manual check`}>
                    <header className="technician-workspace-heading">
                        <button className="button button-secondary" type="button" onClick={() => setActiveCategory(null)}>
                            <ArrowLeft size={14} aria-hidden="true" /> BACK TO FUNCTIONAL CHECKS
                        </button>
                        <div>
                            <h2>{categoryDetails.find((category) => category.id === activeCategory)?.title} Check</h2>
                            <span>Manual technician verification · Demo data</span>
                        </div>
                    </header>

                    {activeCategory === "display" && focusedRecord && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">Inspect the screen for dead pixels, colour irregularities, lines, flickering and visible damage.</p>
                            <div className="display-test-surface" style={{ backgroundColor: activeColor.value }} role="img" aria-label={`${activeColor.name} display inspection screen`} />
                            <div className="technician-control-row" aria-label="Display test colours">
                                {displayColors.map((color) => (
                                    <button
                                        className={`button ${activeColor.name === color.name ? "button-primary" : "button-secondary"}`}
                                        key={color.name}
                                        type="button"
                                        aria-pressed={activeColor.name === color.name}
                                        onClick={() => setActiveColor(color)}
                                    >
                                        {color.name} screen
                                    </button>
                                ))}
                            </div>
                            <OutcomeButtons
                                options={manualOutcomes}
                                selected={focusedRecord.result}
                                onSelect={(value) => updateManualCheck("display", { result: value as ManualCheckOutcome })}
                            />
                            <label className="technician-notes-field">
                                <span>Technician notes</span>
                                <textarea value={focusedRecord.notes} onChange={(event) => updateManualCheck("display", { notes: event.target.value })} rows={3} />
                            </label>
                            <button className="button button-primary" type="button" disabled={!focusedRecord.result} onClick={() => completeManualCheck("display")}>
                                <Check size={14} aria-hidden="true" /> SAVE DISPLAY RESULT
                            </button>
                        </div>
                    )}

                    {activeCategory === "keyboard" && focusedRecord && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">Press physical keys to record responses. Select a key below to mark a reported fault. Key presses do not determine the result.</p>
                            <div className="keyboard-test-layout" aria-label="US QWERTY keyboard">
                                {usQwertyKeyboardRows.map((row, rowIndex) => (
                                    <div className="keyboard-test-row" key={`row-${rowIndex}`}>
                                        {row.map((key) => {
                                            const tested = manualFunctionalChecks.testedKeyCodes.includes(key.code);
                                            const faulty = manualFunctionalChecks.faultyKeyCodes.includes(key.code);
                                            const selected = selectedKeyboardKey === key.code;
                                            return (
                                                <button
                                                    className={[
                                                        "keyboard-test-key",
                                                        key.width ? `is-${key.width}` : "",
                                                        tested ? "is-tested" : "",
                                                        faulty ? "is-faulty" : "",
                                                        selected ? "is-selected" : "",
                                                    ].filter(Boolean).join(" ")}
                                                    key={key.code}
                                                    type="button"
                                                    aria-pressed={selected}
                                                    aria-label={`${key.label}${faulty ? ", marked faulty" : ""}${tested ? ", key response detected" : ""}`}
                                                    onClick={() => setSelectedKeyboardKey(key.code)}
                                                >
                                                    {key.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                            <div className="keyboard-test-stats">
                                <span>Keys tested <strong>{testedKeys}</strong></span>
                                <span>Faulty keys <strong>{faultyKeys}</strong></span>
                                <span>Untested keys <strong>{keyboardKeyCount - testedKeys}</strong></span>
                                <span>Detected response <strong>{selectedKeyboardKey ?? "None"}</strong></span>
                            </div>
                            <div className="technician-control-row">
                                <button className="button button-secondary" type="button" disabled={!selectedKeyboardKey} onClick={() => selectedKeyboardKey && toggleFaultyKeyboardKey(selectedKeyboardKey)}>
                                    {selectedKeyboardKey && manualFunctionalChecks.faultyKeyCodes.includes(selectedKeyboardKey) ? "UNMARK SELECTED KEY FAULTY" : "MARK SELECTED KEY AS FAULTY"}
                                </button>
                                <button className="button button-secondary" type="button" onClick={() => setSelectedKeyboardKey(null)}>
                                    <RotateCcw size={14} aria-hidden="true" /> CLEAR SELECTION
                                </button>
                            </div>
                            <OutcomeButtons
                                options={manualOutcomes}
                                selected={focusedRecord.result}
                                onSelect={(value) => updateManualCheck("keyboard", { result: value as ManualCheckOutcome })}
                            />
                            <label className="technician-notes-field">
                                <span>Technician notes</span>
                                <textarea value={focusedRecord.notes} onChange={(event) => updateManualCheck("keyboard", { notes: event.target.value })} rows={3} />
                            </label>
                            <button className="button button-primary" type="button" disabled={!focusedRecord.result} onClick={() => completeManualCheck("keyboard")}>
                                <Check size={14} aria-hidden="true" /> FINISH KEYBOARD CHECK
                            </button>
                        </div>
                    )}

                    {activeCategory === "touchscreen" && focusedRecord && (
                        demoDevice.display.touchscreenPresent ? (
                            <div className="technician-workspace-body">
                                <p className="technician-instruction">Tap different screen areas, including corners, centre and edges. Test multi-touch where supported.</p>
                                <div className="touchscreen-test-area">Use the device touchscreen to inspect this area</div>
                                <OutcomeButtons
                                    options={manualOutcomes}
                                    selected={focusedRecord.result}
                                    onSelect={(value) => updateManualCheck("touchscreen", { result: value as ManualCheckOutcome })}
                                />
                                <label className="technician-notes-field">
                                    <span>Technician notes</span>
                                    <textarea value={focusedRecord.notes} onChange={(event) => updateManualCheck("touchscreen", { notes: event.target.value })} rows={3} />
                                </label>
                                <button className="button button-primary" type="button" disabled={!focusedRecord.result} onClick={() => completeManualCheck("touchscreen")}>SAVE TOUCHSCREEN RESULT</button>
                            </div>
                        ) : (
                            <div className="touchscreen-not-detected" role="status">Touchscreen not detected — Not Applicable.</div>
                        )
                    )}

                    {activeCategory === "touchpad" && focusedRecord && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">Manually perform each step on the device touchpad:</p>
                            <ol className="touchpad-instructions">
                                <li>Move the pointer across the touchpad.</li>
                                <li>Test single-finger movement.</li>
                                <li>Test left click.</li>
                                <li>Test right click.</li>
                                <li>Test scrolling.</li>
                                <li>Test multi-touch gestures, if supported.</li>
                            </ol>
                            <OutcomeButtons
                                options={touchpadOutcomes}
                                selected={focusedRecord.result}
                                onSelect={(value) => updateManualCheck("touchpad", { result: value as ManualCheckOutcome })}
                            />
                            <label className="technician-notes-field">
                                <span>Technician notes</span>
                                <textarea value={focusedRecord.notes} onChange={(event) => updateManualCheck("touchpad", { notes: event.target.value })} rows={3} />
                            </label>
                            <button className="button button-primary" type="button" disabled={!focusedRecord.result} onClick={() => completeManualCheck("touchpad")}>SAVE TOUCHPAD RESULT</button>
                        </div>
                    )}

                    {activeCategory === "ports" && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">Only ports you add here are included in this inspection. No connectivity test is performed automatically.</p>
                            <div className="port-selection-row">
                                <label>
                                    <span>Available port type</span>
                                    <select value={newPortType} onChange={(event) => setNewPortType(event.target.value)}>
                                        {portTypes.map((type) => <option key={type}>{type}</option>)}
                                    </select>
                                </label>
                                {newPortType === "Other" && (
                                    <label>
                                        <span>Port name</span>
                                        <input value={customPortName} onChange={(event) => setCustomPortName(event.target.value)} placeholder="Enter port type" />
                                    </label>
                                )}
                                <button className="button button-secondary" type="button" onClick={addPort}>ADD SELECTED PORT</button>
                            </div>
                            {manualFunctionalChecks.ports.length === 0 ? (
                                <div className="technician-empty-ports">No ports selected. Add each physically present port to begin inspection.</div>
                            ) : (
                                <div className="port-inspection-layout">
                                    <nav className="port-inspection-list" aria-label="Selected physical ports">
                                        {manualFunctionalChecks.ports.map((port) => (
                                            <button
                                                className={selectedPortId === port.id ? "is-current" : ""}
                                                type="button"
                                                key={port.id}
                                                onClick={() => setSelectedPortId(port.id)}
                                            >
                                                <span>{port.label}</span>
                                                <small>{port.completed ? port.result : port.skipped ? "Skipped · Not Tested" : outcomeLabel(port.result, false)}</small>
                                            </button>
                                        ))}
                                    </nav>
                                    {currentPort ? (
                                        <section className="port-inspection-detail" aria-labelledby="current-port-title">
                                            <h3 id="current-port-title">{currentPort.label}</h3>
                                            <p>Connect a known working device and manually verify the connection.</p>
                                            <OutcomeButtons
                                                options={portOutcomes}
                                                selected={currentPort.result}
                                                onSelect={(value) => updateManualPort(currentPort.id, { result: value as PortCheckOutcome })}
                                            />
                                            <label className="technician-notes-field">
                                                <span>Technician notes</span>
                                                <textarea value={currentPort.notes} onChange={(event) => updateManualPort(currentPort.id, { notes: event.target.value })} rows={3} />
                                            </label>
                                            <div className="technician-control-row">
                                                <button
                                                    className="button button-secondary"
                                                    type="button"
                                                    disabled={manualFunctionalChecks.ports.findIndex((port) => port.id === currentPort.id) <= 0}
                                                    onClick={() => {
                                                        const index = manualFunctionalChecks.ports.findIndex((port) => port.id === currentPort.id);
                                                        setSelectedPortId(manualFunctionalChecks.ports[index - 1]?.id ?? null);
                                                    }}
                                                >
                                                    <ArrowLeft size={14} aria-hidden="true" /> PREVIOUS PORT
                                                </button>
                                                <button className="button button-secondary" type="button" disabled={!currentPort.result} onClick={savePortAndNext}>
                                                    <Save size={14} aria-hidden="true" /> SAVE &amp; NEXT PORT
                                                </button>
                                                <button className="button button-secondary" type="button" onClick={skipCurrentPort}>
                                                    <SkipForward size={14} aria-hidden="true" /> SKIP
                                                </button>
                                            </div>
                                        </section>
                                    ) : (
                                        <div className="technician-empty-ports">Select a port to inspect or add another physical port.</div>
                                    )}
                                </div>
                            )}
                            <footer className="port-inspection-footer">
                                <span>Unselected ports are not tested or included in results.</span>
                                <button className="button button-primary" type="button" onClick={() => { finalizeManualPorts(); setActiveCategory(null); }}>
                                    FINISH PORT INSPECTION
                                </button>
                            </footer>
                        </div>
                    )}
                </section>
            )}
        </main>
    );
}
