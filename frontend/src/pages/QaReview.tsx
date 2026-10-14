import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { getReport, saveTechnicianRecord } from "../api/reports";
import { getStationProfile } from "../station";

type Disposition = "PASS" | "FAIL" | "CONDITIONAL PASS" | "INCOMPLETE";

interface ReportRecord {
    status?: string;
    data?: Record<string, unknown>;
    summary?: Record<string, number>;
    [key: string]: unknown;
}

function recommendation(report: ReportRecord | null): Disposition {
    if (!report) {
        return "INCOMPLETE";
    }
    const summary = report.summary || (report.data?.diagnostic_summary as Record<string, number> | undefined);
    if (!summary || !summary.total) {
        return "INCOMPLETE";
    }
    if ((summary.failed || 0) > 0 || (summary.errors || 0) > 0) {
        return "FAIL";
    }
    const intake = report.data?.intake_record as Record<string, unknown> | undefined;
    const plannedCount =
        (Array.isArray(intake?.planned_diagnostics) ? intake.planned_diagnostics.length : 0) +
        (Array.isArray(intake?.planned_manual_checks) ? intake.planned_manual_checks.length : 0);
    if (plannedCount > summary.total) {
        return "INCOMPLETE";
    }
    if ((summary.blocked || 0) > 0 || (summary.not_run || 0) > 0) {
        return "INCOMPLETE";
    }
    if ((summary.not_applicable || 0) > 0 || (summary.unsupported || 0) > 0) {
        return "CONDITIONAL PASS";
    }
    return (summary.passed || 0) === summary.total ? "PASS" : "INCOMPLETE";
}

export default function QaReview() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const sessionId = params.get("sessionId") || "";
    const [report, setReport] = useState<ReportRecord | null>(null);
    const [disposition, setDisposition] = useState<Disposition>("INCOMPLETE");
    const [approver, setApprover] = useState(getStationProfile()?.technician || "");
    const [reason, setReason] = useState("");
    const [approved, setApproved] = useState(false);
    const [loading, setLoading] = useState(Boolean(sessionId));
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!sessionId) {
            setError("A session ID is required for final QA review.");
            setLoading(false);
            return;
        }
        let active = true;
        getReport(sessionId)
            .then((loaded) => {
                if (active) {
                    setReport(loaded);
                    const record = loaded.data?.technician_record as Record<string, string | null> | undefined;
                    const savedDisposition = record?.final_disposition;
                    setDisposition(
                        savedDisposition === "PASS" ||
                        savedDisposition === "FAIL" ||
                        savedDisposition === "CONDITIONAL PASS" ||
                        savedDisposition === "INCOMPLETE"
                            ? savedDisposition
                            : recommendation(loaded),
                    );
                    if (record?.qa_approver) {
                        setApprover(record.qa_approver);
                    }
                    setReason(record?.final_disposition_reason || "");
                }
            })
            .catch((loadError: unknown) => {
                if (active) {
                    setError(loadError instanceof Error ? loadError.message : "The session report could not be loaded.");
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

    const summary = useMemo(
        () => report?.summary || (report?.data?.diagnostic_summary as Record<string, number> | undefined),
        [report],
    );
    const technicianRecord = report?.data?.technician_record as Record<string, string | null> | undefined;
    const dispositionSaved =
        technicianRecord?.final_disposition === disposition &&
        technicianRecord?.qa_approver === approver.trim() &&
        technicianRecord?.final_disposition_reason === reason.trim();

    async function saveDisposition() {
        if (
            !sessionId ||
            !approved ||
            !approver.trim() ||
            (disposition !== recommendation(report) && !reason.trim()) ||
            saving
        ) {
            return;
        }
        setSaving(true);
        setError("");
        try {
            await saveTechnicianRecord(sessionId, {
                final_disposition: disposition,
                qa_approver: approver.trim(),
                final_disposition_reason: reason.trim(),
            });
            const refreshed = await getReport(sessionId);
            setReport(refreshed);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "The QA disposition could not be saved.");
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return <div className="loading-panel">Loading QA evidence…</div>;
    }

    if (!report) {
        return <div className="empty-panel"><h2>QA review unavailable</h2><p>{error || "The report was not found."}</p></div>;
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 8 OF 9 · FINAL QUALITY REVIEW</span>
                    <h1 className="page-title">Review and disposition</h1>
                    <p className="page-description">Suggested disposition is derived from recorded results. Review exceptions and make the final decision before export.</p>
                </div>
                <button className="button button-secondary" type="button" onClick={() => navigate(`/results?sessionId=${encodeURIComponent(sessionId)}`)}>Back to results</button>
            </div>
            <section className="results-overview">
                <div className="results-session"><span className="results-session-icon" aria-hidden="true">✓</span><div><span className="eyebrow">SESSION</span><strong>{sessionId}</strong><span>{String(report.device_id || "Device unavailable")}</span></div></div>
                <div className="results-overall"><span>Suggested disposition</span><span className={`result-badge ${recommendation(report) === "PASS" ? "result-pass" : recommendation(report) === "FAIL" ? "result-fail" : "result-neutral"}`}>{recommendation(report)}</span></div>
            </section>
            <section className="results-summary">
                {["total", "passed", "failed", "errors", "not_applicable", "unsupported", "blocked", "not_run"].map((key) => (
                    <div className="summary-box" key={key}><span>{key.replaceAll("_", " ")}</span><strong>{summary?.[key] ?? 0}</strong></div>
                ))}
            </section>
            <section className="qa-review-panel">
                <span className="eyebrow">QA APPROVAL</span>
                <h2>Record final disposition</h2>
                <p>Use the recorded check evidence and unresolved exceptions. This approval name is a station record, not an authenticated identity.</p>
                <label>Final disposition
                    <select value={disposition} onChange={(event) => {
                        setApproved(false);
                        setDisposition(event.target.value as Disposition);
                    }}>
                        <option>PASS</option><option>FAIL</option><option>CONDITIONAL PASS</option><option>INCOMPLETE</option>
                    </select>
                </label>
                <label>QA approver
                    <input maxLength={150} value={approver} onChange={(event) => {
                        setApproved(false);
                        setApprover(event.target.value);
                    }} />
                </label>
                {disposition !== recommendation(report) && (
                    <label>Reason for deviating from the suggested disposition
                        <textarea maxLength={2000} rows={3} value={reason} onChange={(event) => {
                            setApproved(false);
                            setReason(event.target.value);
                        }} />
                    </label>
                )}
                <label className="qa-confirmation"><input type="checkbox" checked={approved} onChange={(event) => setApproved(event.target.checked)} /> I reviewed the report evidence and approve this disposition.</label>
                {error && <div className="error-box">{error}</div>}
                <button className="button button-primary" type="button" onClick={() => void saveDisposition()} disabled={!approved || !approver.trim() || (disposition !== recommendation(report) && !reason.trim()) || saving}>
                    {saving ? "Saving QA decision…" : "Save QA disposition"}
                </button>
            </section>
            <div className="inventory-continue">
                <div><strong>{dispositionSaved ? "QA decision saved to the backend report" : "QA disposition not saved"}</strong><span>Save the reviewed disposition before final report export.</span></div>
                <button className="button button-primary" type="button" disabled={!dispositionSaved} onClick={() => navigate(`/report?sessionId=${encodeURIComponent(sessionId)}`)}>Open report <span aria-hidden="true">→</span></button>
            </div>
        </div>
    );
}
