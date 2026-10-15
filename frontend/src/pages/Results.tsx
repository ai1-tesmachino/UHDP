import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { getReport, saveTechnicianRecord } from "../api/reports";
import DiagnosticValues from "../components/DiagnosticValues";
import TestResultsList from "../components/TestResultsList";

interface DiagnosticResult {
    status?: string;
    test_status?: string;
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
            warnings?: number;
            errors?: number;
            not_applicable?: number;
            unsupported?: number;
            blocked?: number;
            not_run?: number;
        };
        data?: Record<string, unknown>;
        [key: string]: unknown;
    };
    summary?: {
        total?: number;
        passed?: number;
        failed?: number;
        warnings?: number;
        errors?: number;
        not_applicable?: number;
        unsupported?: number;
        blocked?: number;
        not_run?: number;
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
        warnings: number;
        errors: number;
        not_applicable: number;
        unsupported: number;
        blocked: number;
        not_run: number;
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
            } else if (status === "warning") {
                summary.warnings += 1;
            } else if (status === "not_applicable") {
                summary.not_applicable += 1;
            } else if (status === "unsupported") {
                summary.unsupported += 1;
            } else if (status === "blocked") {
                summary.blocked += 1;
            } else if (status === "not_run") {
                summary.not_run += 1;
            }
            return summary;
        },
        { total: 0, passed: 0, failed: 0, warnings: 0, errors: 0, not_applicable: 0, unsupported: 0, blocked: 0, not_run: 0 }
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
        fault_code: "",
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
                "test_results",
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
    const standardizedResults =
        typeof reportData.test_results === "object" && reportData.test_results !== null
            ? reportData.test_results as Record<string, DiagnosticResult>
            : {};
    const legacyVisibleChecks = [
        ...Object.entries(diagnostics),
        ...Object.entries(manualChecks).map(([key, value]) => [`manual_${key}`, value] as const),
    ];
    const visibleChecks = Object.keys(standardizedResults).length > 0
        ? Object.entries(standardizedResults)
        : legacyVisibleChecks;
    const intakeRecord =
        typeof reportData.intake_record === "object" && reportData.intake_record !== null
            ? reportData.intake_record as Record<string, string | undefined>
            : {};
    const failedAutomated = Object.entries(diagnostics).flatMap(([key, value]) => {
        const item = asDiagnosticResult(value);
        const status = normalizedStatus(item?.status);
        return item && ["failed", "fail", "error"].includes(status)
            ? [key.replace(/_result$/, "")]
            : [];
    });
    const failedManual = Object.entries(manualChecks).flatMap(([key, value]) =>
        ["failed", "fail", "error"].includes(normalizedStatus(value.status)) ? [key] : []
    );
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

    function retest(checkIds: string[], mode: "automated" | "manual") {
        const deviceId = result?.device_id || report?.device_id || "";
        if (!deviceId || !resolvedSessionId || checkIds.length === 0) {
            return;
        }
        const query = new URLSearchParams({
            deviceId,
            mode,
            retestOf: resolvedSessionId,
            assetTag: intakeRecord.asset_tag || "",
            technician: intakeRecord.technician || "",
            stationId: intakeRecord.station_id || "",
            customerReference: intakeRecord.customer_reference || "",
            workflowType: intakeRecord.workflow_type || "service_center",
            profileName: "retest",
        });
        query.set(mode === "manual" ? "manualChecks" : "selected", checkIds.join(","));
        navigate(`/diagnostics?${query.toString()}`);
    }

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
                    <span className="eyebrow">STEP 7 OF 9 · RUN SUMMARY</span>
                    <h1 className="page-title">Diagnostic results</h1>
                    <p className="page-description">
                        Review the outcome of every check before generating your report.
                    </p>
                </div>
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => navigate("/devices")}>
                        New diagnostic
                    </button>
                    {failedAutomated.length > 0 && (
                        <button className="button button-secondary" type="button" onClick={() => retest(failedAutomated, "automated")}>
                            Retest failed automated checks
                        </button>
                    )}
                    {failedManual.length > 0 && (
                        <button className="button button-secondary" type="button" onClick={() => retest(failedManual, "manual")}>
                            Retest failed manual checks
                        </button>
                    )}
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() =>
                            navigate(`/qa?sessionId=${encodeURIComponent(resolvedSessionId || "")}`, {
                                state: result,
                            })
                        }
                        disabled={!resolvedSessionId}
                    >
                        Final QA review <span aria-hidden="true">→</span>
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
                    <span>Warnings</span>
                    <strong>{summary?.warnings ?? 0}</strong>
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
                <div className="summary-box summary-box-neutral">
                    <span>Blocked</span>
                    <strong>{summary?.blocked ?? 0}</strong>
                </div>
                <div className="summary-box summary-box-neutral">
                    <span>Not run</span>
                    <strong>{summary?.not_run ?? 0}</strong>
                </div>
            </section>

            <section className="technician-record-panel">
                <div>
                    <span className="eyebrow">SERVICE / QA RECORD</span>
                    <h2>Technician notes and disposition</h2>
                    <p>Keep observed issues, repairs, replacements, and customer notes with this session.</p>
                </div>
                <label>
                    Fault code
                    <input
                        value={technicianRecord.fault_code}
                        maxLength={100}
                        onChange={(event) => setTechnicianRecord((current) => ({
                            ...current,
                            fault_code: event.target.value,
                        }))}
                    />
                </label>
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
                {Object.keys(standardizedResults).length > 0 ? (
                    <TestResultsList records={standardizedResults} />
                ) : visibleChecks.length === 0 ? (
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
                            const status = diagnostic.test_status || diagnostic.status;
                            return (
                                <div className="diagnostic-result-block" key={key}>
                                    <div className="diagnostic-result-heading">
                                        <span className={getStatusClass(status)}>
                                            {String(status || "Unknown")}
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
