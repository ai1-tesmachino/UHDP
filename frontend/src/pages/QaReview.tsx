import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { getReport, saveTechnicianRecord } from "../api/reports";
import { finalizeDiagnosticSession } from "../api/execution";
import { getStationProfile } from "../station";
import type { CosmeticInspections } from "../api/cosmeticInspection";
import FieldLabel from "../components/FieldLabel";

type Disposition =
    | "Ready for resale"
    | "Resale with disclosed issues"
    | "Repair required"
    | "Reject / parts only"
    | "Inspection incomplete / retest required";

interface ReportRecord {
    status?: string;
    data?: Record<string, unknown>;
    summary?: Record<string, number>;
    [key: string]: unknown;
}

function recommendation(report: ReportRecord | null): Disposition {
    if (!report) {
        return "Inspection incomplete / retest required";
    }
    const summary = report.summary || (report.data?.diagnostic_summary as Record<string, number> | undefined);
    if (!summary || !summary.total) {
        return "Inspection incomplete / retest required";
    }
    if ((summary.failed || 0) > 0 || (summary.errors || 0) > 0) {
        return "Repair required";
    }
    if ((summary.warnings || 0) > 0) {
        return "Resale with disclosed issues";
    }
    const intake = report.data?.intake_record as Record<string, unknown> | undefined;
    const plannedCount =
        (Array.isArray(intake?.planned_diagnostics) ? intake.planned_diagnostics.length : 0) +
        (Array.isArray(intake?.planned_manual_checks) ? intake.planned_manual_checks.length : 0);
    if (plannedCount > summary.total) {
        return "Inspection incomplete / retest required";
    }
    if ((summary.blocked || 0) > 0 || (summary.not_run || 0) > 0) {
        return "Inspection incomplete / retest required";
    }
    if ((summary.not_applicable || 0) > 0 || (summary.unsupported || 0) > 0) {
        return "Resale with disclosed issues";
    }
    return (summary.passed || 0) === summary.total
        ? "Ready for resale"
        : "Inspection incomplete / retest required";
}

export default function QaReview() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const sessionId = params.get("sessionId") || "";
    const [report, setReport] = useState<ReportRecord | null>(null);
    const [disposition, setDisposition] = useState<Disposition>("Inspection incomplete / retest required");
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
                        savedDisposition === "Ready for resale" ||
                        savedDisposition === "Resale with disclosed issues" ||
                        savedDisposition === "Repair required" ||
                        savedDisposition === "Reject / parts only" ||
                        savedDisposition === "Inspection incomplete / retest required"
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
    const cosmeticInspections = report?.data?.cosmetic_inspections as CosmeticInspections | undefined;
    const initialCosmeticItems = cosmeticInspections?.initial?.items || {};
    const finalCosmeticItems = cosmeticInspections?.final?.items || {};
    const hasInitialCosmeticAssessment = Object.keys(initialCosmeticItems).length > 0;
    const finalCosmeticComplete = hasInitialCosmeticAssessment && Object.keys(initialCosmeticItems).every((itemId) => {
        const item = finalCosmeticItems[itemId];
        const damageNeedsDetails = item?.condition === "Damaged" || item?.condition === "Missing";
        const damageDetailsComplete = !damageNeedsDetails || Boolean(
            item &&
            item.damage_description.trim() &&
            item.damage_location.trim() &&
            item.severity !== "None",
        );
        return Boolean(item?.condition && item.severity && item.technician_confirmed && damageDetailsComplete);
    });
    const cosmeticVerificationRequired = hasInitialCosmeticAssessment && !finalCosmeticComplete;
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
            await finalizeDiagnosticSession(sessionId);
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
                    <span className="eyebrow">FINAL DISPOSITION</span>
                    <h1 className="page-title">Review and disposition</h1>
                    <p className="page-description">Suggested disposition is derived from recorded results. Review exceptions and make the final decision before export.</p>
                </div>
                <div className="action-row">
                    <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => navigate(`/qc?sessionId=${encodeURIComponent(sessionId)}&stage=cosmetic&phase=final`)}
                    >
                        Final cosmetic verification
                    </button>
                    <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => navigate(`/results?sessionId=${encodeURIComponent(sessionId)}`)}
                    >
                        Back to results
                    </button>
                </div>
            </div>
            <section className="results-overview">
                <div className="results-session"><span className="results-session-icon" aria-hidden="true">✓</span><div><span className="eyebrow">SESSION</span><strong>{sessionId}</strong><span>{String(report.device_id || "Device unavailable")}</span></div></div>
                <div className="results-overall"><span>Suggested disposition</span><span className={`result-badge ${recommendation(report) === "Ready for resale" ? "result-pass" : recommendation(report) === "Repair required" || recommendation(report) === "Reject / parts only" ? "result-fail" : "result-neutral"}`}>{recommendation(report)}</span></div>
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
                {hasInitialCosmeticAssessment && (
                    <div className={`error-box${finalCosmeticComplete ? " qa-cosmetic-complete" : ""}`}>
                        {finalCosmeticComplete
                            ? "Final cosmetic verification is complete. Initial condition remains available in the report."
                            : "Complete final cosmetic verification for every initially inspected item before approving disposition."}
                    </div>
                )}
                <FieldLabel required>Final disposition
                    <select required value={disposition} onChange={(event) => {
                        setApproved(false);
                        setDisposition(event.target.value as Disposition);
                    }}>
                        <option>Ready for resale</option>
                        <option>Resale with disclosed issues</option>
                        <option>Repair required</option>
                        <option>Reject / parts only</option>
                        <option>Inspection incomplete / retest required</option>
                    </select>
                </FieldLabel>
                <FieldLabel required>QA approver
                    <input required maxLength={150} value={approver} onChange={(event) => {
                        setApproved(false);
                        setApprover(event.target.value);
                    }} />
                </FieldLabel>
                {disposition !== recommendation(report) && (
                    <FieldLabel required>Reason for deviating from the suggested disposition
                        <textarea required maxLength={2000} rows={3} value={reason} onChange={(event) => {
                            setApproved(false);
                            setReason(event.target.value);
                        }} />
                    </FieldLabel>
                )}
                <label className="qa-confirmation"><input type="checkbox" required checked={approved} onChange={(event) => setApproved(event.target.checked)} /> I reviewed the report evidence and approve this disposition.<span className="required-field-mark" aria-label="required"> *</span></label>
                {error && <div className="error-box">{error}</div>}
                <button className="button button-primary" type="button" onClick={() => void saveDisposition()} disabled={!approved || !approver.trim() || (disposition !== recommendation(report) && !reason.trim()) || cosmeticVerificationRequired || saving}>
                    {saving ? "Saving QA decision…" : "Save QA disposition"}
                </button>
            </section>
            <div className="inventory-continue">
                <div><strong>{dispositionSaved ? "QC disposition saved and session finalized" : "QC disposition not saved"}</strong><span>Save the reviewed disposition before final report export.</span></div>
                <button className="button button-primary" type="button" disabled={!dispositionSaved} onClick={() => navigate(`/report?sessionId=${encodeURIComponent(sessionId)}`)}>Open report <span aria-hidden="true">→</span></button>
            </div>
        </div>
    );
}
