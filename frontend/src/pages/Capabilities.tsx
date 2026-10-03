import { useEffect, useState } from "react";

import { CapabilityReport, getCapabilities } from "../api/capabilities";

export default function Capabilities() {
    const [report, setReport] = useState<CapabilityReport | null>(null);
    const [error, setError] = useState("");

    useEffect(() => {
        let active = true;
        getCapabilities()
            .then((data) => {
                if (active) {
                    setReport(data);
                }
            })
            .catch((loadError: unknown) => {
                if (active) {
                    setError(
                        loadError instanceof Error
                            ? loadError.message
                            : "Diagnostic engine capabilities could not be loaded.",
                    );
                }
            });
        return () => {
            active = false;
        };
    }, []);

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">UHDP CORE · OPEN ENGINES · OEM EXTENSIONS</span>
                    <h1 className="page-title">Diagnostic capabilities</h1>
                    <p className="page-description">
                        See which hardware areas are catalogued and which optional engines are available in this runtime.
                        Presence does not mean an engine has been executed or certified.
                    </p>
                </div>
            </div>

            {error && <div className="error-box">{error}</div>}
            {!report && !error && <div className="loading-panel">Checking local diagnostic tools…</div>}
            {report && (
                <>
                    <section className="capabilities-platform">
                        <span>Host platform</span>
                        <strong>{report.platform}</strong>
                    </section>
                    <section className="results-table-panel">
                        <table className="device-table capability-table">
                            <thead>
                                <tr>
                                    <th>Hardware area</th>
                                    <th>Tier</th>
                                    <th>Engine readiness</th>
                                    <th>Optional engines</th>
                                </tr>
                            </thead>
                            <tbody>
                                {report.components.map((component) => (
                                    <tr key={component.id}>
                                        <td>
                                            <strong>{component.name}</strong>
                                            <code className="capability-id">{component.id}</code>
                                        </td>
                                        <td>{component.tier}</td>
                                        <td>
                                            {component.available_engines}/{component.engine_count} engines available
                                        </td>
                                        <td>
                                            <div className="capability-engines">
                                                {component.engines.map((engine) => (
                                                    <span
                                                        key={engine.name}
                                                        className={`capability-engine capability-engine-${engine.status}`}
                                                        title={engine.path || engine.kind}
                                                    >
                                                        {engine.name}: {engine.status.replaceAll("_", " ")}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </section>
                    <section className="technician-record-panel">
                        <h2>OEM extension points</h2>
                        <p>
                            Extension families identified in the product plan: {report.oem_extension_points.join(", ")}.
                            These are not currently represented as certified OEM diagnostic integrations.
                        </p>
                    </section>
                </>
            )}
        </div>
    );
}
