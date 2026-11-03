import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getDevices } from "../api/devices";
import { getDiagnostics } from "../api/diagnostics";
import { DiagnosticSession, getDiagnosticSessions } from "../api/execution";
import { getHealth } from "../api/health";
import { getReports, RecentReport } from "../api/reports";
import { useQcSession } from "../session/SessionContext";
import { getQcResumePath } from "../session/workflow";
import { getStationProfile } from "../station";

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
    const navigate = useNavigate();
    const { activeSession, activateSession, deactivateSession, loading: sessionLoading } = useQcSession();
    const [online, setOnline] = useState<boolean | null>(null);
    const [systemAvailable, setSystemAvailable] = useState<boolean | null>(null);
    const [diagnosticCount, setDiagnosticCount] = useState<number | null>(null);
    const [deviceCount, setDeviceCount] = useState<number | null>(null);
    const [allReports, setAllReports] = useState<RecentReport[]>([]);
    const [recentReports, setRecentReports] = useState<RecentReport[]>([]);
    const [incompleteSessions, setIncompleteSessions] = useState<DiagnosticSession[]>([]);
    const [activityError, setActivityError] = useState("");
    const [loading, setLoading] = useState(true);
    const stationId = getStationProfile()?.station_id || "";

    const loadDashboard = useCallback(async () => {
        setLoading(true);
        setActivityError("");

        const [healthResult, devicesResult, diagnosticsResult, reportsResult, sessionsResult] =
            await Promise.allSettled([
                getHealth(),
                getDevices(),
                getDiagnostics(),
                getReports(),
                getDiagnosticSessions(),
            ]);

        setOnline(healthResult.status === "fulfilled");
        setSystemAvailable(
            devicesResult.status === "fulfilled"
                ? devicesResult.value.some(
                    (device) => device.device_type.toLowerCase() === "system"
                )
                : null
        );
        setDeviceCount(devicesResult.status === "fulfilled" ? devicesResult.value.length : null);
        setDiagnosticCount(
            diagnosticsResult.status === "fulfilled"
                ? diagnosticsResult.value.length
                : null
        );

        if (reportsResult.status === "fulfilled") {
            const stationReports = reportsResult.value.filter(
                (report) => report.station_id === stationId
            );
            setAllReports(stationReports);
            setRecentReports(
                [...stationReports]
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
        if (sessionsResult.status === "fulfilled") {
            setIncompleteSessions(
                sessionsResult.value.filter(
                    (session) => !["completed", "complete"].includes(session.status.toLowerCase()),
                ),
            );
        } else {
            setIncompleteSessions([]);
        }

        setLoading(false);
    }, [stationId]);

    useEffect(() => {
        void loadDashboard();
    }, [loadDashboard]);

    function startInspection() {
        if (sessionLoading) return;
        if (
            activeSession &&
            !["completed", "complete"].includes(activeSession.status.toLowerCase()) &&
            !window.confirm(
                `QC session ${activeSession.session_id} is still in progress. Start a new session? The current session will remain saved and can be resumed from QC History.`,
            )
        ) {
            return;
        }
        if (activeSession) deactivateSession();
        navigate("/devices?new=1");
    }

    async function resumeInspection(sessionId: string) {
        try {
            const session = await activateSession(sessionId);
            navigate(getQcResumePath(session.session_id, session.status, session.device_id));
        } catch {
            setActivityError("The saved inspection could not be resumed.");
        }
    }

    return (
        <div className="dashboard-page">
            <section className="dashboard-hero">
                <div className="dashboard-hero-copy">
                    <span className="eyebrow">READY WHEN YOU ARE</span>
                    <h1>Let’s inspect this device.</h1>
                    <p>
                        Start an inspection. UHDP will guide you through the checks
                        and record your results as you go.
                    </p>
                    <button
                        type="button"
                        className="button button-primary hero-cta"
                        onClick={() => void startInspection()}
                        disabled={sessionLoading}
                    >
                        {sessionLoading ? "Starting…" : "START NEW QC"} <span aria-hidden="true">→</span>
                    </button>
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
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-blue" aria-hidden="true">▦</span>
                        <span className="metric-label">Detected components</span>
                    </div>
                    <strong className="metric-value">{deviceCount === null ? "—" : deviceCount}</strong>
                    <span className="metric-footnote">Reported by current hardware discovery</span>
                </article>
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-purple" aria-hidden="true">▤</span>
                        <span className="metric-label">Saved inspections</span>
                    </div>
                    <strong className="metric-value">{allReports.length}</strong>
                    <span className="metric-footnote">Reports currently loaded from backend</span>
                </article>
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-green" aria-hidden="true">%</span>
                        <span className="metric-label">Pass rate</span>
                    </div>
                    <strong className="metric-value">
                        {(() => {
                            const decided = allReports.filter((report) =>
                                ["passed", "pass", "failed", "fail", "error"].includes(report.status.toLowerCase())
                            );
                            if (!decided.length) return "—";
                            const passed = decided.filter((report) =>
                                ["passed", "pass"].includes(report.status.toLowerCase())
                            ).length;
                            return `${Math.round((passed / decided.length) * 100)}%`;
                        })()}
                    </strong>
                    <span className="metric-footnote">Based on saved reports with explicit outcomes</span>
                </article>
                <article className="metric-card">
                    <div className="metric-topline">
                        <span className="metric-icon metric-icon-purple" aria-hidden="true">!</span>
                        <span className="metric-label">Failed inspections</span>
                    </div>
                    <strong className="metric-value">
                        {allReports.filter((report) =>
                            ["failed", "fail", "error"].includes(report.status.toLowerCase())
                        ).length}
                    </strong>
                    <span className="metric-footnote">Backend reports with a failed/error status</span>
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
                    <button
                        type="button"
                        className="action-card action-card-featured"
                        onClick={() => void startInspection()}
                        disabled={sessionLoading}
                    >
                        <span className="action-card-icon" aria-hidden="true">⌕</span>
                        <span className="action-card-copy">
                            <strong>Discover devices</strong>
                            <span>Find hardware connected to this system.</span>
                        </span>
                        <span className="action-card-arrow" aria-hidden="true">→</span>
                    </button>
                    <a href="#recent-activity" className="action-card">
                        <span className="action-card-icon action-card-icon-purple" aria-hidden="true">▤</span>
                        <span className="action-card-copy">
                            <strong>View reports</strong>
                            <span>Review outcomes from recent sessions.</span>
                        </span>
                        <span className="action-card-arrow" aria-hidden="true">→</span>
                    </a>
                    <Link to="/analytics" className="action-card">
                        <span className="action-card-icon" aria-hidden="true">▥</span>
                        <span className="action-card-copy">
                            <strong>Production analytics</strong>
                            <span>Review station throughput and saved failure distribution.</span>
                        </span>
                        <span className="action-card-arrow" aria-hidden="true">→</span>
                    </Link>
                </div>
            </section>

            <section className="dashboard-section" id="recent-activity">
                {incompleteSessions.length > 0 && (
                    <section className="resume-inspections" aria-label="Incomplete inspections">
                        <div className="section-heading">
                            <div>
                                <span className="eyebrow">IN PROGRESS</span>
                                <h2>Resume inspection</h2>
                            </div>
                            <span className="section-count">{incompleteSessions.length}</span>
                        </div>
                        {incompleteSessions.slice(0, 5).map((session) => (
                            <button
                                key={session.session_id}
                                type="button"
                                className="recent-row resume-session-row"
                                onClick={() => void resumeInspection(session.session_id)}
                            >
                                <span className="recent-row-icon" aria-hidden="true">◷</span>
                                <span className="recent-row-main">
                                    <strong>{session.intake_record?.asset_tag as string || session.device_id || "Inspection in progress"}</strong>
                                    <span>Session {session.session_id} · {formatDate(session.created_at)}</span>
                                </span>
                                <span className={`status-pill status-${statusLabel(session.status).replaceAll(" ", "-")}`}>
                                    {statusLabel(session.status)}
                                </span>
                                <span className="recent-row-arrow" aria-hidden="true">→</span>
                            </button>
                        ))}
                    </section>
                )}
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">HISTORY</span>
                        <h2>Recent sessions</h2>
                    </div>
                    <Link className="button button-secondary" to="/history">
                        View QC History
                    </Link>
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
                        <button className="button button-secondary" type="button" onClick={() => void startInspection()}>
                            Start your first check
                        </button>
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
