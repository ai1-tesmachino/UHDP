interface TestResultsListProps {
    records: Record<string, unknown>;
}

interface TestResultRecord {
    test_id?: unknown;
    test_status?: unknown;
    status?: unknown;
    scan_status?: unknown;
    detected_devices?: unknown;
    technician_decision?: unknown;
    technician_notes?: unknown;
    recorded_at?: unknown;
    evidence?: unknown;
    retest_history?: unknown;
}

function asObject(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return null;
    }
    return value as Record<string, unknown>;
}

function asRecord(value: unknown): TestResultRecord {
    return asObject(value) as TestResultRecord | null ?? {};
}

function readable(value: unknown): string {
    if (value === null || value === undefined || value === "") {
        return "Not recorded";
    }
    if (typeof value === "string") {
        return value.replaceAll("_", " ");
    }
    if (typeof value === "object") {
        return JSON.stringify(value, null, 2) ?? String(value);
    }
    return String(value);
}

function titleFor(testId: string, evidence: Record<string, unknown> | null) {
    const name = evidence?.test_name;
    if (typeof name === "string" && name.trim()) {
        return name;
    }
    return testId
        .replace(/_result$/, "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: unknown) {
    if (typeof value !== "string") {
        return "Not recorded";
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function TestResultsList({ records }: TestResultsListProps) {
    const entries = Object.entries(records);
    if (entries.length === 0) {
        return <div className="empty-state">No diagnostic results were recorded.</div>;
    }

    return (
        <div className="test-results-list">
            {entries.map(([key, rawRecord]) => {
                const record = asRecord(rawRecord);
                const evidence = asObject(record.evidence);
                const status = record.test_status ?? record.status;
                const devices = Array.isArray(record.detected_devices)
                    ? record.detected_devices
                    : record.detected_devices === undefined || record.detected_devices === null
                      ? []
                      : [record.detected_devices];
                const history = Array.isArray(record.retest_history)
                    ? record.retest_history
                    : [];
                const title = titleFor(
                    typeof record.test_id === "string" ? record.test_id : key,
                    evidence,
                );
                const normalizedStatus = String(status ?? "not_run").toLowerCase();
                const statusClass = ["pass", "passed"].includes(normalizedStatus)
                    ? "result-pass"
                    : ["fail", "failed", "error"].includes(normalizedStatus)
                      ? "result-fail"
                      : "result-neutral";

                return (
                    <article className="test-result-card" key={key}>
                        <div className="test-result-heading">
                            <h3>{title}</h3>
                            <span className={`result-badge ${statusClass}`}>
                                {readable(status ?? "not_run")}
                            </span>
                        </div>
                        <dl className="test-result-facts">
                            <div>
                                <dt>Scan</dt>
                                <dd>{readable(record.scan_status ?? "not_attempted")}</dd>
                            </div>
                            <div>
                                <dt>Technician</dt>
                                <dd>{readable(record.technician_decision)}</dd>
                            </div>
                            <div>
                                <dt>Detected</dt>
                                <dd>
                                    {devices.length
                                        ? devices.map(readable).join(", ")
                                        : "No device evidence"}
                                </dd>
                            </div>
                            <div>
                                <dt>Recorded</dt>
                                <dd>{formatDate(record.recorded_at)}</dd>
                            </div>
                        </dl>
                        {typeof record.technician_notes === "string" &&
                            record.technician_notes.trim() && (
                                <p className="test-result-notes">{record.technician_notes}</p>
                            )}
                        {(evidence || history.length > 0) && (
                            <details className="test-result-evidence">
                                <summary>
                                    Evidence and history
                                    {history.length > 0 ? ` · ${history.length} prior attempt(s)` : ""}
                                </summary>
                                {evidence && (
                                    <div>
                                        <strong>Evidence</strong>
                                        <pre>{JSON.stringify(evidence, null, 2)}</pre>
                                    </div>
                                )}
                                {history.map((rawAttempt, index) => {
                                    const attempt = asRecord(rawAttempt);
                                    return (
                                        <div className="test-result-prior" key={`${key}-attempt-${index}`}>
                                            <strong>
                                                Attempt {index + 1}: {readable(attempt.test_status ?? attempt.status)}
                                            </strong>
                                            <span>
                                                {readable(attempt.scan_status)} · {formatDate(attempt.recorded_at)}
                                            </span>
                                            {typeof attempt.technician_notes === "string" &&
                                                attempt.technician_notes && (
                                                    <p>{attempt.technician_notes}</p>
                                                )}
                                            {attempt.evidence && (
                                                <pre>{JSON.stringify(attempt.evidence, null, 2)}</pre>
                                            )}
                                        </div>
                                    );
                                })}
                            </details>
                        )}
                    </article>
                );
            })}
        </div>
    );
}
