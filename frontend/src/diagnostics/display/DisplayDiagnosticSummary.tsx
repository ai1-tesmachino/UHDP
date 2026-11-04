import "./displayDiagnostic.css";

interface DisplayDiagnosticSummaryProps {
    value: unknown;
}

function asRecord(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
}

function formatStatus(value: unknown) {
    if (typeof value !== "string" || !value) return "In progress";
    return value.replaceAll("_", " ");
}

function metadataValue(metadata: Record<string, unknown>, key: string) {
    const value = metadata[key];
    if (value === undefined || value === null || value === "") return "Not available";
    if (key === "refresh_rate_hz" && typeof value === "number") return `${value} Hz`;
    return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export default function DisplayDiagnosticSummary({ value }: DisplayDiagnosticSummaryProps) {
    const diagnostic = asRecord(value);
    if (!diagnostic) return null;
    const tests = asRecord(diagnostic.tests) || {};
    const results = Object.values(tests)
        .map((test) => asRecord(test)?.latest_result)
        .filter((result) => asRecord(result) !== null);
    const metadata = asRecord(diagnostic.display_metadata) || {};
    const outcome = diagnostic.overall_status || diagnostic.status;

    return (
        <section className="display-report-summary" aria-label="Display diagnostic summary">
            <header>
                <div>
                    <span className="eyebrow">DISPLAY DIAGNOSTICS</span>
                    <h2>Technician panel assessment</h2>
                </div>
                <span className={`display-report-status ${String(outcome || "in_progress").replaceAll("_", "-")}`}>
                    {formatStatus(outcome)}
                </span>
            </header>
            <div className="display-report-facts">
                <div><span>Visual checks with results</span><strong>{results.length} / 8</strong></div>
                <div><span>Resolution</span><strong>{metadataValue(metadata, "resolution")}</strong></div>
                <div><span>Refresh rate</span><strong>{metadataValue(metadata, "refresh_rate_hz")}</strong></div>
                <div><span>Display model</span><strong>{metadataValue(metadata, "model")}</strong></div>
            </div>
            <p>
                Each individual technician decision, defect, note, and retest attempt is included in the inspection details below.
            </p>
        </section>
    );
}
