import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { getReport, saveTechnicianRecord } from "../api/reports";
import DiagnosticValues from "../components/DiagnosticValues";

interface DiagnosticResult {
    status?: string;
    message?: string;
    [key: string]: unknown;
}

interface ResultData {
    session_id?: string;
    device_id?: string;
    status?: string;
    workflow_status?: string;
    created_at?: string;
    report?: {
        device_id?: string;
        report_id?: string;
        created_at?: string;
        summary?: {
            total?: number;
            passed?: number;
            failed?: number;
            errors?: number;
            not_applicable?: number;
            unsupported?: number;
        };
        data?: Record<string, unknown>;
        [key: string]: unknown;
    };
    summary?: {
        total?: number;
        passed?: number;
        failed?: number;
        errors?: number;
        not_applicable?: number;
        unsupported?: number;
    };
    data?: Record<string, unknown>;
    [key: string]: unknown;
}

function normalizedStatus(status: unknown) {
    return String(status || "Unknown").toLowerCase();
}

function getStatusClass(status: unknown): string {
    const value = normalizedStatus(status);
    if (["pass", "passed", "success", "ok", "completed"].includes(value)) {
        return "result-badge result-pass";
    }
    if (["fail", "failed", "error"].includes(value)) {
        return "result-badge result-fail";
    }
    return "result-badge result-neutral";
}

function getSummary(data: Record<string, DiagnosticResult> = {}) {
    const values = Object.values(data);
    return values.reduce<{
        total: number;
        passed: number;
        failed: number;
        errors: number;
        not_applicable: number;
        unsupported: number;
    }>(
        (summary, item) => {
            const status = normalizedStatus(item.status);
            summary.total += 1;
            if (["pass", "passed", "success", "ok"].includes(status)) {
                summary.passed += 1;
            } else if (["fail", "failed"].includes(status)) {
                summary.failed += 1;
            } else if (status === "error") {
                summary.errors += 1;
            } else if (status === "not_applicable") {
                summary.not_applicable += 1;
            } else if (status === "unsupported") {
                summary.unsupported += 1;
            }
            return summary;
        },
        { total: 0, passed: 0, failed: 0, errors: 0, not_applicable: 0, unsupported: 0 }
    );
}

function asDiagnosticResult(value: unknown): DiagnosticResult | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return null;
    }
    return value as DiagnosticResult;
}

export default function Results() {
    const location = useLocation();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const sessionId = params.get("sessionId") || "";
    const navigationResult = location.state as ResultData | null;
    const [result, setResult] = useState<ResultData | null>(navigationResult);
    const [loading, setLoading] = useState(!navigationResult && !!sessionId);
    const [error, setError] = useState("");
    const [savingTechnicianRecord, setSavingTechnicianRecord] = useState(false);
    const [technicianRecord, setTechnicianRecord] = useState({
        observed_issue: "",
        repair_performed: "",
        replacement_performed: "",
        customer_notes: "",
        refurbishment_grade: "not_graded",
    });

    useEffect(() => {
        if (!sessionId || navigationResult) {
            setLoading(false);
            return;
        }

        let active = true;
        setLoading(true);
        setError("");
        getReport(sessionId)
            .then((report) => {
                if (active) {
                    setResult(report);
                }
            })
            .catch((err: unknown) => {
                if (active) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "The session results could not be loaded."
                    );
                }
            })
            .finally(() => {
                if (active) {
                    setLoading(false);
                }
            });

        return () => {
            active = false;
        };
    }, [navigationResult, sessionId]);

    const report = result?.report ?? result;
    const reportData = report?.data ?? {};
    useEffect(() => {
        const record = reportData.technician_record;
        if (typeof record === "object" && record !== null) {
            setTechnicianRecord((current) => ({
                ...current,
                ...(record as Partial<typeof current>),
            }));
        }
    }, [reportData.technician_record]);
    const diagnostics = Object.fromEntries(
        Object.entries(reportData).filter(
            ([key]) => ![
                "diagnostic_summary",
                "manual_checks",
                "technician_record",
                "intake_record",
                "device_inventory",
                "health_analytics",
                "refurbishment_recommendation",
            ].includes(key)
        )
    );
    const manualChecks =
        typeof reportData.manual_checks === "object" && reportData.manual_checks !== null
            ? reportData.manual_checks as Record<string, DiagnosticResult>
            : {};
    const visibleChecks = [
        ...Object.entries(diagnostics),
        ...Object.entries(manualChecks).map(([key, value]) => [`manual_${key}`, value] as const),
    ];
    const embeddedSummary = reportData.diagnostic_summary;
    const reportSummary =
        report?.summary ??
        (typeof embeddedSummary === "object" && embeddedSummary !== null
            ? embeddedSummary as ResultData["summary"]
            : undefined);
    const derivedSummary = useMemo(
        () => getSummary(
            Object.fromEntries(
                Object.entries(diagnostics).flatMap(([key, value]) => {
                    const item = asDiagnosticResult(value);
                    return item ? [[key, item]] : [];
                })
            )
        ),
        [reportData]
    );
    const summary = reportSummary ?? derivedSummary;
    const overallStatus =
        result?.workflow_status || result?.status || report?.status || "Unknown";
    const resolvedSessionId = result?.session_id || sessionId;

    async function saveRecord() {
        if (!resolvedSessionId || savingTechnicianRecord) {
            return;
        }
        setSavingTechnicianRecord(true);
        setError("");
        try {
            await saveTechnicianRecord(resolvedSessionId, technicianRecord);
            const refreshed = await getReport(resolvedSessionId);
            setResult(refreshed);
        } catch (saveError) {
            setError(
                saveError instanceof Error
                    ? saveError.message
                    : "Technician record could not be saved.",
            );
        } finally {
            setSavingTechnicianRecord(false);
        }
    }

    if (loading) {
        return <div className="loading-panel">Loading session results…</div>;
    }

    if (!result) {
        return (
            <div className="empty-panel">
                <span className="empty-panel-icon" aria-hidden="true">▤</span>
                <h2>{error ? "Results unavailable" : "No results to show"}</h2>
                <p>{error || "Run a diagnostic session first, then return here to review it."}</p>
                <button className="button button-primary" type="button" onClick={() => navigate("/devices")}>
                    Start diagnostics
                </button>
            </div>
        );
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 5 OF 6 · RUN SUMMARY</span>
                    <h1 className="page-title">Diagnostic results</h1>
                    <p className="page-description">
                        Review the outcome of every check before generating your report.
                    </p>
                </div>
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => navigate("/devices")}>
                        New diagnostic
                    </button>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() =>
                            navigate(`/report?sessionId=${encodeURIComponent(resolvedSessionId || "")}`, {
                                state: result,
                            })
                        }
                        disabled={!resolvedSessionId}
                    >
                        Generate report <span aria-hidden="true">→</span>
                    </button>
                </div>
            </div>

            <section className="results-overview">
                <div className="results-session">
                    <span className="results-session-icon" aria-hidden="true">✓</span>
                    <div>
                        <span className="eyebrow">SESSION</span>
                        <strong>{resolvedSessionId || "Session ID unavailable"}</strong>
                        <span>{result.device_id || report?.device_id || "Device unavailable"}</span>
                    </div>
                </div>
                <div className="results-overall">
                    <span>Overall status</span>
                    <span className={getStatusClass(overallStatus)}>{String(overallStatus)}</span>
                </div>
            </section>

            <section className="results-report-meta">
                <h2>Report metadata</h2>
                <div className="results-meta-grid">
                    <div><span>Report ID</span><code>{String(report?.report_id ?? "Not returned")}</code></div>
                    <div><span>Created</span><code>{String(report?.created_at ?? result?.created_at ?? "Not returned")}</code></div>
                    <div><span>Session ID</span><code>{resolvedSessionId || "Not returned"}</code></div>
                    <div><span>Device ID</span><code>{String(report?.device_id ?? result?.device_id ?? "Not returned")}</code></div>
                </div>
            </section>

            <section className="results-table-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">DEVICE PROFILE</span>
                        <h2>Intake record and discovered inventory</h2>
                    </div>
                </div>
                <DiagnosticValues
                    diagnosticName="intake_record"
                    value={
                        typeof reportData.intake_record === "object" && reportData.intake_record !== null
                            ? reportData.intake_record as Record<string, unknown>
                            : {}
                    }
                />
                <DiagnosticValues
                    diagnosticName="device_inventory"
                    value={{ devices: reportData.device_inventory ?? [] }}
                />
            </section>

            {typeof reportData.health_analytics === "object" && reportData.health_analytics !== null && (
                <section className="results-table-panel">
                    <div className="section-heading">
                        <div>
                            <span className="eyebrow">HEALTH ANALYTICS</span>
                            <h2>Observed component scores</h2>
                        </div>
                    </div>
                    <DiagnosticValues
                        diagnosticName="health_analytics"
                        value={reportData.health_analytics as Record<string, unknown>}
                    />
                    <DiagnosticValues
                        diagnosticName="refurbishment_recommendation"
                        value={
                            typeof reportData.refurbishment_recommendation === "object" &&
                            reportData.refurbishment_recommendation !== null
                                ? reportData.refurbishment_recommendation as Record<string, unknown>
                                : {}
                        }
                    />
                </section>
            )}

            <section className="results-summary">
                <div className="summary-box">
                    <span>Total checks</span>
                    <strong>{summary?.total ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-pass">
                    <span>Passed</span>
                    <strong>{summary?.passed ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-fail">
                    <span>Failed</span>
                    <strong>{summary?.failed ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-neutral">
                    <span>Errors</span>
                    <strong>{summary?.errors ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-neutral">
                    <span>Not applicable</span>
                    <strong>{summary?.not_applicable ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-neutral">
                    <span>Unsupported</span>
                    <strong>{summary?.unsupported ?? 0}</strong>
                </div>
            </section>

            <section className="technician-record-panel">
                <div>
                    <span className="eyebrow">SERVICE / QA RECORD</span>
                    <h2>Technician notes and disposition</h2>
                    <p>Keep observed issues, repairs, replacements, and customer notes with this session.</p>
                </div>
                <label>
                    Observed issue
                    <textarea
                        value={technicianRecord.observed_issue}
                        maxLength={2000}
                        rows={3}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            observed_issue: event.target.value,
                        }))}
                    />
                </label>
                <label>
                    Repair performed
                    <textarea
                        value={technicianRecord.repair_performed}
                        maxLength={2000}
                        rows={3}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            repair_performed: event.target.value,
                        }))}
                    />
                </label>
                <label>
                    Replacement performed
                    <textarea
                        value={technicianRecord.replacement_performed}
                        maxLength={2000}
                        rows={3}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            replacement_performed: event.target.value,
                        }))}
                    />
                </label>
                <label>
                    Customer / QA notes
                    <textarea
                        value={technicianRecord.customer_notes}
                        maxLength={2000}
                        rows={3}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            customer_notes: event.target.value,
                        }))}
                    />
                </label>
                <label>
                    Refurbishment disposition
                    <select
                        value={technicianRecord.refurbishment_grade}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            refurbishment_grade: event.target.value,
                        }))}
                    >
                        <option value="not_graded">Not graded</option>
                        <option value="A">Grade A</option>
                        <option value="B">Grade B</option>
                        <option value="C">Grade C</option>
                        <option value="needs_repair">Needs repair</option>
                    </select>
                </label>
                {typeof reportData.refurbishment_recommendation === "object" &&
                    reportData.refurbishment_recommendation !== null ? (
                    <div className="grade-recommendation">
                        <strong>Evidence-based recommendation</strong>
                        <pre>{JSON.stringify(reportData.refurbishment_recommendation, null, 2)}</pre>
                    </div>
                ) : null}
                {error && <div className="error-box">{error}</div>}
                <button
                    className="button button-primary"
                    type="button"
                    onClick={() => void saveRecord()}
                    disabled={savingTechnicianRecord}
                >
                    {savingTechnicianRecord ? "Saving…" : "Save technician record"}
                </button>
            </section>

            <section className="results-table-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">DETAILS</span>
                        <h2>Diagnostic checks</h2>
                    </div>
                    <span className="section-count">{visibleChecks.length} checks</span>
                </div>
                {visibleChecks.length === 0 ? (
                    <div className="empty-state">
                        No individual diagnostic results were returned for this session.
                    </div>
                ) : (
                    <div className="diagnostic-values-list">
                        {visibleChecks.map(([key, value]) => {
                            const diagnostic = asDiagnosticResult(value);
                            if (!diagnostic) {
                                return (
                                    <DiagnosticValues
                                        key={key}
                                        diagnosticName={key}
                                        value={{ value }}
                                    />
                                );
                            }
                            return (
                                <div className="diagnostic-result-block" key={key}>
                                    <div className="diagnostic-result-heading">
                                        <span className={getStatusClass(diagnostic.status)}>
                                            {String(diagnostic.status || "Unknown")}
                                        </span>
                                        <span>{diagnostic.message || "No message returned"}</span>
                                    </div>
                                    <DiagnosticValues diagnosticName={key} value={diagnostic} />
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
