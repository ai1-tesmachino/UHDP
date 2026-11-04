import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { downloadReportJson, getReport, getReportHtmlUrl } from "../api/reports";
import DiagnosticValues from "../components/DiagnosticValues";
import TestResultsList from "../components/TestResultsList";
import CosmeticAssessmentSummary from "../components/CosmeticAssessmentSummary";
import type { CosmeticInspections } from "../api/cosmeticInspection";
import { EntitySyncStatus, getEntitySyncStatus } from "../api/sync";
import { getEvidenceUrl } from "../api/evidence";
import DisplayDiagnosticSummary from "../diagnostics/display/DisplayDiagnosticSummary";

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
        warnings?: number;
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
    const navigationResult = location.state as ReportData | null;
    const sessionId = params.get("sessionId") || navigationResult?.session_id || "";
    const [report, setReport] = useState<ReportData | null>(
        navigationResult?.report || navigationResult
    );
    const [loading, setLoading] = useState(Boolean(sessionId));
    const [error, setError] = useState("");
    const [downloading, setDownloading] = useState(false);
    const [syncStatus, setSyncStatus] = useState<EntitySyncStatus | null>(null);
    const reportId = report?.session_id || sessionId;

    useEffect(() => {
        if (!reportId) {
            setSyncStatus(null);
            return;
        }
        let active = true;
        getEntitySyncStatus("report", reportId)
            .then((status) => {
                if (active) setSyncStatus(status);
            })
            .catch(() => {
                if (active) setSyncStatus(null);
            });
        return () => {
            active = false;
        };
    }, [reportId]);

    useEffect(() => {
        if (!sessionId) {
            setLoading(false);
            return;
        }

        let active = true;
        setLoading(true);
        setError("");
        setReport(null);
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
                            : "The QC report could not be loaded."
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
    }, [sessionId]);

    function printReport() {
        window.print();
    }

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
                <p>{error || "Complete a QC inspection to generate a report."}</p>
                <button className="button button-primary" type="button" onClick={() => navigate("/")}>
                Start a new QC
                </button>
            </div>
        );
    }

    const allData = report.data || {};
    const diagnostics = Object.fromEntries(
        Object.entries(allData).filter(
            ([key]) => ![
                "diagnostic_summary",
                "test_results",
                "manual_checks",
                "technician_record",
                "intake_record",
                "device_inventory",
                "health_analytics",
                "refurbishment_recommendation",
                "performance_results",
                "evidence",
                "cosmetic_inspections",
                "display_diagnostic",
                "display_diagnostic_result",
            ].includes(key)
        )
    );
    const manualChecks =
        typeof allData.manual_checks === "object" && allData.manual_checks !== null
            ? allData.manual_checks as Record<string, unknown>
            : {};
    const standardizedResults =
        typeof allData.test_results === "object" && allData.test_results !== null
            ? allData.test_results as Record<string, unknown>
            : {};
    const legacyVisibleChecks = [
        ...Object.entries(diagnostics),
        ...Object.entries(manualChecks).map(([key, value]) => [`manual_${key}`, value] as const),
    ];
    const visibleChecks = Object.keys(standardizedResults).length > 0
        ? Object.entries(standardizedResults)
        : legacyVisibleChecks;
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
                    <span className="eyebrow">QC REPORT · SESSION {sessionId || "UNASSIGNED"}</span>
                    <h1 className="page-title">Diagnostic report</h1>
                    <p className="page-description">
                        A shareable record of the hardware checks in this session.
                    </p>
                </div>
                <div className="action-row">
                    <button className="button button-secondary" type="button" onClick={() => navigate(`/results?sessionId=${encodeURIComponent(sessionId)}`)}>
                        Back to review
                    </button>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() => void exportJson()}
                        disabled={downloading || !reportId}
                    >
                        {downloading ? "Preparing…" : "Download JSON"}
                    </button>
                    <button className="button button-secondary" type="button" onClick={printReport}>
                        Print / Save PDF
                    </button>
                </div>
            </div>

            {error && <div className="error-box report-error">{error}</div>}
            {syncStatus && (
                <div className="info-box" role="status">
                    Local report · {syncStatus.state === "Synced"
                        ? "synchronized to cloud"
                        : syncStatus.state === "Needs attention"
                            ? "cloud sync needs attention"
                            : syncStatus.state === "Local only"
                                ? "cloud sync not queued"
                                : `cloud sync ${syncStatus.state.toLowerCase()}`}
                </div>
            )}

            <section className="report-cover">
                <div className="report-cover-top">
                    <span className="report-mark" aria-hidden="true">U</span>
                    <span className={statusClass(report.status)}>
                        {report.status || "Completed"}
                    </span>
                </div>
                <span className="eyebrow">SESSION REPORT</span>
                <h2>{report.device_id || "Hardware QC session"}</h2>
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
                        <h2>Inspection summary</h2>
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
                    <div><span>Warnings</span><strong>{summary?.warnings ?? "—"}</strong></div>
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

            <CosmeticAssessmentSummary
                inspections={(allData.cosmetic_inspections || {}) as CosmeticInspections}
            />

            <DisplayDiagnosticSummary value={allData.display_diagnostic} />

            {typeof allData.performance_results === "object" && allData.performance_results !== null && (
                <section className="results-table-panel">
                    <div className="section-heading">
                        <div>
                            <span className="eyebrow">PERFORMANCE QC</span>
                            <h2>Stress and storage results</h2>
                        </div>
                    </div>
                    <DiagnosticValues
                        diagnosticName="performance_results"
                        value={allData.performance_results as Record<string, unknown>}
                    />
                </section>
            )}

            {Array.isArray(allData.evidence) && (
                <section className="results-table-panel">
                    <div className="section-heading">
                        <div>
                            <span className="eyebrow">PHOTOS AND EVIDENCE</span>
                            <h2>{allData.evidence.length} attached files</h2>
                        </div>
                    </div>
                    {allData.evidence.length ? (
                        <div className="recent-list">
                            {(allData.evidence as Array<Record<string, unknown>>).map((item) => (
                                <a
                                    className="recent-row"
                                    key={String(item.evidence_id)}
                                    href={getEvidenceUrl(String(item.evidence_id))}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    <span className="recent-row-icon" aria-hidden="true">▧</span>
                                    <span className="recent-row-main">
                                        <strong>{String(item.original_filename || "Evidence file")}</strong>
                                        <span>{String(item.media_type || "Unknown type")} · {String(item.size_bytes || 0)} bytes</span>
                                    </span>
                                    <code>{String(item.sha256 || "")}</code>
                                </a>
                            ))}
                        </div>
                    ) : (
                        <p className="empty-state">No evidence files were attached to this session.</p>
                    )}
                </section>
            )}

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
                </section>
            )}

            <section className="results-table-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">TECHNICIAN DISPOSITION</span>
                        <h2>Notes and final decision</h2>
                    </div>
                </div>
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

            <section className="results-table-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">CHECKS</span>
                        <h2>Inspection details</h2>
                    </div>
                    <span className="section-count">{visibleChecks.length} checks</span>
                </div>
                {Object.keys(standardizedResults).length > 0 ? (
                    <TestResultsList records={standardizedResults} />
                ) : visibleChecks.length === 0 ? (
                    <div className="empty-state">No individual check details were included in this report.</div>
                ) : (
                    <div className="diagnostic-values-list">
                        {visibleChecks.map(([name, value]) => {
                            const item =
                                typeof value === "object" && value !== null && !Array.isArray(value)
                                    ? value as Record<string, unknown>
                                    : { value };
                            const status = item.test_status || item.status;
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
