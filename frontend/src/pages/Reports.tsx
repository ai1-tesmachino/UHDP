import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getReports, RecentReport } from "../api/reports";

function formatDate(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
}

export default function Reports() {
    const navigate = useNavigate();
    const [reports, setReports] = useState<RecentReport[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let current = true;
        getReports()
            .then((items) => {
                if (current) setReports([...items].sort(
                    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
                ));
            })
            .catch((loadError: unknown) => {
                if (current) setError(loadError instanceof Error ? loadError.message : "Saved reports could not be loaded.");
            })
            .finally(() => {
                if (current) setLoading(false);
            });
        return () => {
            current = false;
        };
    }, []);

    return (
        <div className="page-flow">
            <header className="page-header">
                <div>
                    <span className="eyebrow">DOCUMENTATION</span>
                    <h1 className="page-title">QC Reports</h1>
                    <p className="page-description">Review saved inspection reports and open a report for print or export.</p>
                </div>
                <span className="history-total">{reports.length} {reports.length === 1 ? "report" : "reports"}</span>
            </header>

            <section className="history-panel">
                {error && <div className="error-box" role="alert">{error}</div>}
                {loading ? (
                    <div className="loading-panel">Loading saved reports…</div>
                ) : reports.length === 0 ? (
                    <div className="history-empty">
                        <strong>No saved reports yet</strong>
                        <p>Reports become available when an inspection is completed.</p>
                    </div>
                ) : (
                    <div className="history-table-wrap">
                        <table className="history-table">
                            <thead>
                                <tr>
                                    <th>QC ID</th>
                                    <th>Device</th>
                                    <th>Generated</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((report) => (
                                    <tr key={report.session_id}>
                                        <td><strong>{report.session_id}</strong></td>
                                        <td>{report.device_id || "Device not identified"}</td>
                                        <td>{formatDate(report.created_at)}</td>
                                        <td><span className="history-status is-complete">{report.status.replaceAll("_", " ")}</span></td>
                                        <td>
                                            <button
                                                className="button button-secondary"
                                                type="button"
                                                onClick={() => navigate(`/report?sessionId=${encodeURIComponent(report.session_id)}`)}
                                            >
                                                Preview report
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    );
}
