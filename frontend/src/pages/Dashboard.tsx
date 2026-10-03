import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getDevices } from "../api/devices";
import { getDiagnostics } from "../api/diagnostics";
import { getHealth } from "../api/health";
import { getReports, RecentReport } from "../api/reports";

function formatDate(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
        ? "Date unavailable"
        : date.toLocaleString();
}

function statusLabel(status: string) {
    return status.replaceAll("_", " ").toLowerCase();
}

export default function Dashboard() {
    const [online, setOnline] = useState<boolean | null>(null);
    const [systemAvailable, setSystemAvailable] = useState<boolean | null>(null);
    const [diagnosticCount, setDiagnosticCount] = useState<number | null>(null);
    const [recentReports, setRecentReports] = useState<RecentReport[]>([]);
    const [activityError, setActivityError] = useState("");
    const [loading, setLoading] = useState(true);

    const loadDashboard = useCallback(async () => {
        setLoading(true);
        setActivityError("");

        const [healthResult, devicesResult, diagnosticsResult, reportsResult] =
            await Promise.allSettled([
                getHealth(),
                getDevices(),
                getDiagnostics(),
                getReports(),
            ]);

        setOnline(healthResult.status === "fulfilled");
        setSystemAvailable(
            devicesResult.status === "fulfilled"
                ? devicesResult.value.some(
                    (device) => device.device_type.toLowerCase() === "system"
                )
                : null
        );
        setDiagnosticCount(
            diagnosticsResult.status === "fulfilled"
                ? diagnosticsResult.value.length
                : null
        );

        if (reportsResult.status === "fulfilled") {
            setRecentReports(
                [...reportsResult.value]
                    .sort(
                        (left, right) =>
                            new Date(right.created_at).getTime() -
                            new Date(left.created_at).getTime()
                    )
                    .slice(0, 5)
            );
        } else {
            setActivityError("Recent diagnostic sessions could not be loaded.");
        }

        setLoading(false);
    }, []);

    useEffect(() => {
        void loadDashboard();
    }, [loadDashboard]);

    return (
        <div className="dashboard-page">
            <section className="dashboard-hero">
                <div className="dashboard-hero-copy">
                    <span className="eyebrow">UNIVERSAL HARDWARE DIAGNOSTICS</span>
                    <h1>Know your hardware is ready.</h1>
                    <p>
                        Review the detected hardware, choose your diagnostics, and
                        check the health of this system.
                    </p>
                    <Link to="/devices" className="button button-primary hero-cta">
                        Discover devices <span aria-hidden="true">→</span>
                    </Link>
                </div>
                <div className="hero-illustration" aria-hidden="true">
                    <div className="hero-orbit hero-orbit-outer" />
                    <div className="hero-orbit hero-orbit-inner" />
                    <div className="hero-chip">
                        <span className="hero-chip-mark">U</span>
                        <span className="hero-chip-caption">SYSTEM<br />READY</span>
                    </div>
                    <span className="hero-spark hero-spark-one">✦</span>
                    <span className="hero-spark hero-spark-two">✦</span>
                </div>
            </section>

            <section className="dashboard-metrics" aria-label="System status">
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-green" aria-hidden="true">●</span>
                        <span className="metric-label">Backend</span>
                    </div>
                    <strong className="metric-value">
                        {online === null ? "Checking" : online ? "Connected" : "Offline"}
                    </strong>
                    <span className="metric-footnote">FastAPI service</span>
                </article>
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-blue" aria-hidden="true">◉</span>
                        <span className="metric-label">Diagnostic target</span>
                    </div>
                    <strong className="metric-value">
                        {systemAvailable === null
                            ? "—"
                            : systemAvailable
                              ? "Ready"
                              : "Unavailable"}
                    </strong>
                    <span className="metric-footnote">Diagnostics run across this machine</span>
                </article>
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-purple" aria-hidden="true">⌁</span>
                        <span className="metric-label">Available checks</span>
                    </div>
                    <strong className="metric-value">
                        {diagnosticCount === null ? "—" : diagnosticCount}
                    </strong>
                    <span className="metric-footnote">Ready to run</span>
                </article>
            </section>

            <section className="dashboard-section">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">GET STARTED</span>
                        <h2>Choose your next step</h2>
                    </div>
                    <button
                        className="button button-quiet"
                        type="button"
                        onClick={() => void loadDashboard()}
                        disabled={loading}
                    >
                        {loading ? "Refreshing…" : "Refresh status"}
                    </button>
                </div>
                <div className="action-cards">
                    <Link to="/devices" className="action-card action-card-featured">
                        <span className="action-card-icon" aria-hidden="true">⌕</span>
                        <span className="action-card-copy">
                            <strong>Discover devices</strong>
                            <span>Find hardware connected to this system.</span>
                        </span>
                        <span className="action-card-arrow" aria-hidden="true">→</span>
                    </Link>
                    <a href="#recent-activity" className="action-card">
                        <span className="action-card-icon action-card-icon-purple" aria-hidden="true">▤</span>
                        <span className="action-card-copy">
                            <strong>View reports</strong>
                            <span>Review outcomes from recent sessions.</span>
                        </span>
                        <span className="action-card-arrow" aria-hidden="true">→</span>
                    </a>
                </div>
            </section>

            <section className="dashboard-section" id="recent-activity">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">HISTORY</span>
                        <h2>Recent sessions</h2>
                    </div>
                    <span className="section-count">
                        {recentReports.length} {recentReports.length === 1 ? "session" : "sessions"}
                    </span>
                </div>

                {activityError ? (
                    <div className="error-box">{activityError}</div>
                ) : recentReports.length === 0 && !loading ? (
                    <div className="recent-empty">
                        <span className="recent-empty-icon" aria-hidden="true">◷</span>
                        <div>
                            <strong>No diagnostic sessions yet</strong>
                            <p>Your completed checks will appear here.</p>
                        </div>
                        <Link to="/devices" className="button button-secondary">
                            Start your first check
                        </Link>
                    </div>
                ) : (
                    <div className="recent-list">
                        {recentReports.map((report) => (
                            <Link
                                key={report.session_id}
                                className="recent-row"
                                to={`/results?sessionId=${encodeURIComponent(report.session_id)}`}
                            >
                                <span className="recent-row-icon" aria-hidden="true">▤</span>
                                <span className="recent-row-main">
                                    <strong>{report.device_id || "Unknown device"}</strong>
                                    <span>{formatDate(report.created_at)}</span>
                                </span>
                                <span className={`status-pill status-${statusLabel(report.status).replaceAll(" ", "-")}`}>
                                    {statusLabel(report.status)}
                                </span>
                                <span className="recent-row-arrow" aria-hidden="true">→</span>
                            </Link>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
