import { useState } from "react";
import { ArrowLeft, Save, SkipForward } from "lucide-react";
import {
    PortOutcome,
    PortRecord,
    PortType,
    portOutcomes,
    portTypes,
} from "../../technicianChecks/technicianCheckModels";

function portStatus(port: PortRecord): string {
    if (port.skipped) return "Skipped · Not tested";
    if (port.saved) return `Saved · ${port.result ?? "Not tested"}`;
    return port.result ?? "Not tested";
}

export function PortsPanel({
    ports,
    selectedPortId,
    detectorHints,
    disabled = false,
    onAdd,
    onSelect,
    onChange,
    onSave,
    onSkip,
    onFinalize,
}: {
    ports: PortRecord[];
    selectedPortId: string | null;
    detectorHints: { usbDevices: string[]; connectors: Array<{ name: string; status: string }> };
    disabled?: boolean;
    onAdd(type: PortType, customName?: string): void;
    onSelect(id: string): void;
    onChange(id: string, updates: Partial<PortRecord>): void;
    onSave(id: string): Promise<void> | void;
    onSkip(id: string): Promise<void> | void;
    onFinalize(): Promise<void> | void;
}) {
    const [newPortType, setNewPortType] = useState<PortType>(portTypes[0]);
    const [customPortName, setCustomPortName] = useState("");
    const [busy, setBusy] = useState(false);

    const currentPort = ports.find((port) => port.id === selectedPortId) ?? null;
    const currentIndex = currentPort ? ports.findIndex((port) => port.id === currentPort.id) : -1;
    const unreviewedCount = ports.filter((port) => port.result === null && !port.skipped).length;

    function addPort() {
        onAdd(newPortType, newPortType === "Other" ? customPortName.trim() || undefined : undefined);
        setCustomPortName("");
    }

    function nextUnreviewed(fromIndex: number): PortRecord | null {
        return ports.slice(fromIndex + 1).find((port) => !port.saved && !port.skipped)
            ?? ports.slice(0, fromIndex).find((port) => !port.saved && !port.skipped)
            ?? null;
    }

    async function saveAndNext() {
        if (!currentPort || !currentPort.result || disabled) return;
        setBusy(true);
        try {
            await onSave(currentPort.id);
            const next = nextUnreviewed(currentIndex);
            if (next) onSelect(next.id);
        } finally {
            setBusy(false);
        }
    }

    async function skipCurrent() {
        if (!currentPort || disabled) return;
        setBusy(true);
        try {
            await onSkip(currentPort.id);
            const next = nextUnreviewed(currentIndex);
            if (next) onSelect(next.id);
        } finally {
            setBusy(false);
        }
    }

    async function finalize() {
        if (disabled) return;
        setBusy(true);
        try {
            await onFinalize();
        } finally {
            setBusy(false);
        }
    }

    return (
        <div className="technician-workspace-body">
            <p className="technician-instruction">
                Only ports you add here are included in this inspection. No connectivity test is performed automatically.
            </p>
            {(detectorHints.connectors.length > 0 || detectorHints.usbDevices.length > 0) && (
                <div className="technician-check-meta" aria-label="Detected hardware context">
                    {detectorHints.connectors.map((connector) => (
                        <div key={`connector-${connector.name}`}>
                            <span>Connector {connector.name}</span>
                            <strong>{connector.status || "unknown"}</strong>
                        </div>
                    ))}
                    {detectorHints.usbDevices.slice(0, 6).map((device, index) => (
                        <div key={`usb-${index}-${device}`}>
                            <span>USB inventory</span>
                            <strong>{device}</strong>
                        </div>
                    ))}
                </div>
            )}
            <div className="port-selection-row">
                <label>
                    <span>Available port type</span>
                    <select
                        value={newPortType}
                        disabled={disabled || busy}
                        onChange={(event) => setNewPortType(event.target.value as PortType)}
                    >
                        {portTypes.map((type) => <option key={type}>{type}</option>)}
                    </select>
                </label>
                {newPortType === "Other" && (
                    <label>
                        <span>Port name</span>
                        <input
                            value={customPortName}
                            disabled={disabled || busy}
                            onChange={(event) => setCustomPortName(event.target.value)}
                            placeholder="Enter port type"
                        />
                    </label>
                )}
                <button className="button button-secondary" type="button" disabled={disabled || busy} onClick={addPort}>
                    ADD SELECTED PORT
                </button>
            </div>
            {ports.length === 0 ? (
                <div className="technician-empty-ports">No ports selected. Add each physically present port to begin inspection.</div>
            ) : (
                <div className="port-inspection-layout">
                    <nav className="port-inspection-list" aria-label="Selected physical ports">
                        {ports.map((port) => (
                            <button
                                className={selectedPortId === port.id ? "is-current" : ""}
                                type="button"
                                key={port.id}
                                onClick={() => onSelect(port.id)}
                            >
                                <span>{port.label}</span>
                                <small>{portStatus(port)}</small>
                            </button>
                        ))}
                    </nav>
                    {currentPort ? (
                        <section className="port-inspection-detail" aria-labelledby="current-port-title">
                            <h3 id="current-port-title">{currentPort.label}</h3>
                            <p>Connect a known working device and manually verify the connection.</p>
                            <div className="technician-outcome-buttons" role="group" aria-label="Port check result">
                                {portOutcomes.map((option: PortOutcome) => {
                                    const isSelected = currentPort.result === option;
                                    return (
                                        <button
                                            className={`button ${isSelected ? "button-primary" : "button-secondary"}`}
                                            key={option}
                                            type="button"
                                            aria-pressed={isSelected}
                                            disabled={disabled || busy}
                                            onClick={() => onChange(currentPort.id, { result: option })}
                                        >
                                            {option}
                                        </button>
                                    );
                                })}
                            </div>
                            <label className="technician-notes-field">
                                <span>Technician notes</span>
                                <textarea
                                    value={currentPort.notes}
                                    maxLength={1000}
                                    rows={3}
                                    disabled={disabled}
                                    onChange={(event) => onChange(currentPort.id, { notes: event.target.value.slice(0, 1000) })}
                                />
                            </label>
                            <div className="technician-control-row">
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={currentIndex <= 0 || busy}
                                    onClick={() => onSelect(ports[currentIndex - 1]?.id)}
                                >
                                    <ArrowLeft size={14} aria-hidden="true" /> PREVIOUS PORT
                                </button>
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={!currentPort.result || disabled || busy}
                                    onClick={() => void saveAndNext()}
                                >
                                    <Save size={14} aria-hidden="true" /> SAVE &amp; NEXT PORT
                                </button>
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={disabled || busy}
                                    onClick={() => void skipCurrent()}
                                >
                                    <SkipForward size={14} aria-hidden="true" /> SKIP
                                </button>
                            </div>
                            {currentPort.saved && (
                                <span className="technician-check-saved-at">Saved to QC session · {currentPort.result ?? "Not tested"}</span>
                            )}
                        </section>
                    ) : (
                        <div className="technician-empty-ports">Select a port to inspect or add another physical port.</div>
                    )}
                </div>
            )}
            <footer className="port-inspection-footer">
                <span>
                    {unreviewedCount > 0
                        ? `${unreviewedCount} selected port${unreviewedCount === 1 ? "" : "s"} ${unreviewedCount === 1 ? "needs" : "need"} a result, or must be skipped, before finishing.`
                        : "Unselected ports are not tested or included in results."}
                </span>
                <button
                    className="button button-primary"
                    type="button"
                    disabled={disabled || busy || unreviewedCount > 0}
                    onClick={() => void finalize()}
                >
                    {busy ? "SAVING…" : "FINISH PORT INSPECTION"}
                </button>
            </footer>
        </div>
    );
}
