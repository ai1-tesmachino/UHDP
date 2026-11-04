import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EvidenceMetadata, getEvidenceUrl, getSessionEvidence, uploadEvidence } from "../api/evidence";
import { useQcSession } from "../session/SessionContext";

export default function Photos() {
    const [params] = useSearchParams();
    const { activeSessionId } = useQcSession();
    const sessionId = params.get("sessionId") || activeSessionId;
    const [items, setItems] = useState<EvidenceMetadata[]>([]);
    const [file, setFile] = useState<File | null>(null);
    const [confirmed, setConfirmed] = useState(false);
    const [loading, setLoading] = useState(Boolean(sessionId));
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");

    const refresh = useCallback(async () => {
        if (!sessionId) {
            setItems([]);
            setLoading(false);
            return;
        }
        try {
            setItems(await getSessionEvidence(sessionId));
            setError("");
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Session evidence could not be loaded.");
        } finally {
            setLoading(false);
        }
    }, [sessionId]);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    async function saveEvidence() {
        if (!sessionId || !file || !confirmed || saving) return;
        if (file.size > 100 * 1024 * 1024) {
            setError("Evidence files must be 100 MiB or smaller.");
            return;
        }
        setSaving(true);
        setError("");
        try {
            const metadata = await uploadEvidence(sessionId, file);
            setItems((current) => [...current, metadata]);
            setFile(null);
            setConfirmed(false);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Evidence could not be saved.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">PHOTOS AND EVIDENCE</span>
                    <h1 className="page-title">Session evidence</h1>
                    <p className="page-description">QC session {sessionId || "not selected"}. Evidence is stored on the appliance and indexed against this session.</p>
                </div>
                <div className="photo-page-actions">
                    <Link className="button button-secondary" to={sessionId ? `/results?sessionId=${encodeURIComponent(sessionId)}` : "/"}>
                        Review results
                    </Link>
                    {sessionId && (
                        <Link className="button button-primary" to={`/qa?sessionId=${encodeURIComponent(sessionId)}`}>
                            Continue to final QC <span aria-hidden="true">→</span>
                        </Link>
                    )}
                </div>
            </div>

            {!sessionId ? (
                <div className="empty-panel">
                    <h2>No QC session selected</h2>
                    <p>Start or resume an inspection before adding evidence.</p>
                    <Link className="button button-primary" to="/">Return to dashboard</Link>
                </div>
            ) : (
                <>
                    <section className="manual-check-panel evidence-capture-panel">
                        <label>
                            Select photo, log, or attachment
                            <input
                                type="file"
                                accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,text/plain,text/csv,application/json,application/pdf,application/octet-stream"
                                disabled={saving}
                                onChange={(event) => {
                                    setFile(event.target.files?.[0] || null);
                                    setConfirmed(false);
                                }}
                            />
                        </label>
                        {file && (
                            <>
                                <span>{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MiB</span>
                                <label className="storage-confirmation">
                                    <input
                                        type="checkbox"
                                        checked={confirmed}
                                        onChange={(event) => setConfirmed(event.target.checked)}
                                    />
                                    I confirm this file is relevant to this QC session.
                                </label>
                                <button
                                    className="button button-primary"
                                    type="button"
                                    disabled={saving || !confirmed}
                                    onClick={() => void saveEvidence()}
                                >
                                    {saving ? "Saving evidence…" : "Save evidence locally"}
                                </button>
                            </>
                        )}
                        {error && <div className="error-box">{error}</div>}
                    </section>

                    <section className="results-table-panel">
                        <div className="section-heading">
                            <div>
                                <span className="eyebrow">SAVED LOCALLY</span>
                                <h2>Evidence files</h2>
                            </div>
                            <button className="button button-quiet" type="button" onClick={() => void refresh()} disabled={loading}>
                                {loading ? "Loading…" : "Refresh"}
                            </button>
                        </div>
                        {loading ? (
                            <div className="loading-panel">Loading evidence metadata…</div>
                        ) : items.length ? (
                            <div className="recent-list">
                                {items.map((item) => (
                                    <a className="recent-row" href={getEvidenceUrl(item.evidence_id)} target="_blank" rel="noreferrer" key={item.evidence_id}>
                                        <span className="recent-row-icon" aria-hidden="true">▧</span>
                                        <span className="recent-row-main">
                                            <strong>{item.original_filename}</strong>
                                            <span>{item.media_type} · {(item.size_bytes / 1024 / 1024).toFixed(2)} MiB · {new Date(item.created_at).toLocaleString()}</span>
                                        </span>
                                        <code>{item.sha256.slice(0, 16)}…</code>
                                    </a>
                                ))}
                            </div>
                        ) : (
                            <p className="empty-state">No evidence has been saved for this inspection yet.</p>
                        )}
                    </section>
                </>
            )}
        </div>
    );
}
