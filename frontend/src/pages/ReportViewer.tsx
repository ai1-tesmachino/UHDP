import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { downloadReportJson, getReport, getReportHtmlUrl } from "../api/reports";
import DiagnosticValues from "../components/DiagnosticValues";

interface ReportData {
    report_id?: string;
    session_id?: string;
    device_id?: string;
    status?: string;
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
    report?: ReportData;
    [key: string]: unknown;
}

function statusClass(status: unknown) {
    const value = String(status || "").toLowerCase();
    if (["pass", "passed", "success", "ok", "completed"].includes(value)) {
        return "result-badge result-pass";
    }
    if (["fail", "failed", "error"].includes(value)) {
        return "result-badge result-fail";
    }
    return "result-badge result-neutral";
}

function formatDate(value?: string) {
    if (!value) {
        return "Not available";
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}

export default function ReportViewer() {
    const location = useLocation();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const sessionId = params.get("sessionId") || "";
    const navigationResult = location.state as ReportData | null;
    const [report, setReport] = useState<ReportData | null>(
        navigationResult?.report || navigationResult
    );
    const [loading, setLoading] = useState(!navigationResult && !!sessionId);
    const [error, setError] = useState("");
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        if (!sessionId || navigationResult) {
            setLoading(false);
            return;
        }

        let active = true;
        setLoading(true);
        setError("");
        getReport(sessionId)
            .then((data) => {
                if (active) {
                    setReport(data);
                }
            })
            .catch((err: unknown) => {
                if (active) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "The diagnostic report could not be loaded."
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

    const reportId = report?.session_id || sessionId;

    async function exportJson() {
        if (!reportId) {
            return;
        }

        setDownloading(true);
        setError("");
        try {
            const blob = await downloadReportJson(reportId);
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `uhdp-report-${reportId}.json`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "The JSON report could not be downloaded."
            );
        } finally {
            setDownloading(false);
        }
    }

    if (loading) {
        return <div className="loading-panel">Preparing your report…</div>;
    }

    if (!report) {
        return (
            <div className="empty-panel">
                <span className="empty-panel-icon" aria-hidden="true">▧</span>
                <h2>{error ? "Report unavailable" : "No report to show"}</h2>
                <p>{error || "Complete a diagnostic session to generate a report."}</p>
                <button className="button button-primary" type="button" onClick={() => navigate("/devices")}>
                    Start diagnostics
                </button>
            </div>
        );
    }

    const allData = report.data || {};
    const diagnostics = Object.fromEntries(
        Object.entries(allData).filter(
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
        typeof allData.manual_checks === "object" && allData.manual_checks !== null
            ? allData.manual_checks as Record<string, unknown>
            : {};
    const visibleChecks = [
        ...Object.entries(diagnostics),
        ...Object.entries(manualChecks).map(([key, value]) => [`manual_${key}`, value] as const),
    ];
    const embeddedSummary = allData.diagnostic_summary;
    const summary = report.summary || (
        typeof embeddedSummary === "object" && embeddedSummary !== null
            ? embeddedSummary as ReportData["summary"]
            : undefined
    );

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 6 OF 6 · EXPORT</span>
                    <h1 className="page-title">Diagnostic report</h1>
                    <p className="page-description">
                        A shareable record of the hardware checks in this session.
                    </p>
                </div>
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => navigate(-1)}>
                        Back to results
                    </button>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() => void exportJson()}
                        disabled={downloading || !reportId}
                    >
                        {downloading ? "Preparing…" : "Download JSON"}
                    </button>
                </div>
            </div>

            {error && <div className="error-box report-error">{error}</div>}

            <section className="report-cover">
                <div className="report-cover-top">
                    <span className="report-mark" aria-hidden="true">U</span>
                    <span className={statusClass(report.status)}>
                        {report.status || "Completed"}
                    </span>
                </div>
                <span className="eyebrow">SESSION REPORT</span>
                <h2>{report.device_id || "Hardware diagnostic session"}</h2>
                <p>Generated {formatDate(report.created_at)}</p>
                <div className="report-cover-meta">
                    <div>
                        <span>SESSION ID</span>
                        <code>{report.session_id || sessionId || "Not available"}</code>
                    </div>
                    <div>
                        <span>DEVICE</span>
                        <code>{report.device_id || "Not available"}</code>
                    </div>
                </div>
            </section>

            <section className="results-report-meta">
                <h2>Complete report metadata</h2>
                <div className="results-meta-grid">
                    {Object.entries(report)
                        .filter(([key]) => key !== "data" && key !== "summary")
                        .map(([key, value]) => (
                            <div key={key}>
                                <span>{key.replaceAll("_", " ")}</span>
                                <code>{typeof value === "object" && value !== null
                                    ? JSON.stringify(value, null, 2)
                                    : String(value ?? "null")}</code>
                            </div>
                        ))}
                    {!report.session_id && sessionId && (
                        <div><span>session id</span><code>{sessionId}</code></div>
                    )}
                </div>
            </section>

            <section className="report-summary">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">OUTCOME</span>
                        <h2>Run summary</h2>
                    </div>
                    <a
                        className="button button-secondary"
                        href={getReportHtmlUrl(reportId)}
                        target="_blank"
                        rel="noreferrer"
                    >
                        Open HTML report <span aria-hidden="true">↗</span>
                    </a>
                </div>
                <div className="report-summary-grid">
                    <div><span>Total checks</span><strong>{summary?.total ?? Object.keys(diagnostics).length}</strong></div>
                    <div><span>Passed</span><strong>{summary?.passed ?? "—"}</strong></div>
                    <div><span>Failed</span><strong>{summary?.failed ?? "—"}</strong></div>
                    <div><span>Errors</span><strong>{summary?.errors ?? "—"}</strong></div>
                    <div><span>Not applicable</span><strong>{summary?.not_applicable ?? 0}</strong></div>
                    <div><span>Unsupported</span><strong>{summary?.unsupported ?? 0}</strong></div>
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
                        typeof allData.intake_record === "object" && allData.intake_record !== null
                            ? allData.intake_record as Record<string, unknown>
                            : {}
                    }
                />
                <DiagnosticValues
                    diagnosticName="device_inventory"
                    value={{ devices: allData.device_inventory ?? [] }}
                />
            </section>

            {typeof allData.health_analytics === "object" && allData.health_analytics !== null && (
                <section className="results-table-panel">
                    <div className="section-heading">
                        <div>
                            <span className="eyebrow">HEALTH ANALYTICS</span>
                            <h2>Observed component scores</h2>
                        </div>
                    </div>
                    <DiagnosticValues
                        diagnosticName="health_analytics"
                        value={allData.health_analytics as Record<string, unknown>}
                    />
                    <DiagnosticValues
                        diagnosticName="refurbishment_recommendation"
                        value={
                            typeof allData.refurbishment_recommendation === "object" &&
                            allData.refurbishment_recommendation !== null
                                ? allData.refurbishment_recommendation as Record<string, unknown>
                                : {}
                        }
                    />
                    <DiagnosticValues
                        diagnosticName="technician_record"
                        value={
                            typeof allData.technician_record === "object" &&
                            allData.technician_record !== null
                                ? allData.technician_record as Record<string, unknown>
                                : {}
                        }
                    />
                </section>
            )}

            <section className="results-table-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">CHECKS</span>
                        <h2>Diagnostic details</h2>
                    </div>
                    <span className="section-count">{visibleChecks.length} checks</span>
                </div>
                {visibleChecks.length === 0 ? (
                    <div className="empty-state">No diagnostic details were included in this report.</div>
                ) : (
                    <div className="diagnostic-values-list">
                        {visibleChecks.map(([name, value]) => {
                            const item =
                                typeof value === "object" && value !== null && !Array.isArray(value)
                                    ? value as Record<string, unknown>
                                    : { value };
                            const status = item.status;
                            const message = item.message;
                            return (
                                <div className="diagnostic-result-block" key={name}>
                                    <div className="diagnostic-result-heading">
                                        <span className={statusClass(status)}>{String(status || "Unknown")}</span>
                                        <span>{String(message || "No message returned")}</span>
                                    </div>
                                    <DiagnosticValues diagnosticName={name} value={item} />
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
