import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { DiagnosticSession, getDiagnosticSessions } from "../api/execution";
import { useQcSession } from "../session/SessionContext";
import {
    getQcResumePath,
    getSessionDeviceName,
    getSessionSerialNumber,
    isCompletedSession,
} from "../session/workflow";

function formatDate(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
}

export default function QcHistory() {
    const navigate = useNavigate();
    const { activateSession } = useQcSession();
    const [sessions, setSessions] = useState<DiagnosticSession[]>([]);
    const [query, setQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("all");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [openingSession, setOpeningSession] = useState("");

    useEffect(() => {
        let current = true;
        getDiagnosticSessions()
            .then((items) => {
                if (current) setSessions(items);
            })
            .catch((loadError: unknown) => {
                if (current) {
                    setError(loadError instanceof Error ? loadError.message : "QC history could not be loaded.");
                }
            })
            .finally(() => {
                if (current) setLoading(false);
            });
        return () => {
            current = false;
        };
    }, []);

    const filteredSessions = useMemo(() => {
        const normalizedQuery = query.trim().toLowerCase();
        return sessions.filter((session) => {
            const completed = isCompletedSession(session);
            if (statusFilter === "completed" && !completed) return false;
            if (statusFilter === "incomplete" && completed) return false;
            if (!normalizedQuery) return true;
            return [
                session.session_id,
                session.device_id || "",
                getSessionDeviceName(session),
                getSessionSerialNumber(session),
            ].some((value) => value.toLowerCase().includes(normalizedQuery));
        });
    }, [query, sessions, statusFilter]);

    async function resume(session: DiagnosticSession) {
        setOpeningSession(session.session_id);
        setError("");
        try {
            await activateSession(session.session_id);
            navigate(getQcResumePath(session.session_id, session.status, session.device_id));
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "The saved QC session could not be opened.");
        } finally {
            setOpeningSession("");
        }
    }

    return (
        <div className="page-flow">
            <header className="page-header">
                <div>
                    <span className="eyebrow">WORKSPACE / RECORDS</span>
                    <h1 className="page-title">QC History</h1>
                    <p className="page-description">Find saved inspections, resume incomplete work, or open a completed report.</p>
                </div>
                <span className="history-total">{sessions.length} {sessions.length === 1 ? "session" : "sessions"}</span>
            </header>

            <section className="history-panel">
                <div className="history-controls">
                    <label className="history-search">
                        <span>Search inspections</span>
                        <input
                            type="search"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="QC ID, device, or serial number"
                        />
                    </label>
                    <label className="history-filter">
                        <span>Status</span>
                        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                            <option value="all">All sessions</option>
                            <option value="incomplete">In progress</option>
                            <option value="completed">Completed</option>
                        </select>
                    </label>
                </div>

                {error && <div className="error-box" role="alert">{error}</div>}
                {loading ? (
                    <div className="loading-panel">Loading QC history…</div>
                ) : filteredSessions.length === 0 ? (
                    <div className="history-empty">
                        <strong>{sessions.length ? "No matching inspections" : "No QC sessions yet"}</strong>
                        <p>{sessions.length ? "Try another search or status filter." : "Completed and in-progress inspections will appear here."}</p>
                    </div>
                ) : (
                    <div className="history-table-wrap">
                        <table className="history-table">
                            <thead>
                                <tr>
                                    <th>QC ID</th>
                                    <th>Device</th>
                                    <th>Serial number</th>
                                    <th>Started</th>
                                    <th>Technician</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredSessions.map((session) => {
                                    const completed = isCompletedSession(session);
                                    const technician = session.intake_record?.technician;
                                    return (
                                        <tr key={session.session_id}>
                                            <td><strong>{session.session_id}</strong></td>
                                            <td>{getSessionDeviceName(session)}</td>
                                            <td>{getSessionSerialNumber(session)}</td>
                                            <td>{formatDate(session.created_at)}</td>
                                            <td>{typeof technician === "string" && technician ? technician : "Not recorded"}</td>
                                            <td>
                                                <span className={`history-status ${completed ? "is-complete" : "is-progress"}`}>
                                                    {completed ? "Completed" : session.status.replaceAll("_", " ")}
                                                </span>
                                            </td>
                                            <td>
                                                {completed ? (
                                                    <button
                                                        className="button button-secondary"
                                                        type="button"
                                                        onClick={() => navigate(`/report?sessionId=${encodeURIComponent(session.session_id)}`)}
                                                    >
                                                        Open report
                                                    </button>
                                                ) : (
                                                    <button
                                                        className="button button-primary"
                                                        type="button"
                                                        disabled={openingSession === session.session_id}
                                                        onClick={() => void resume(session)}
                                                    >
                                                        {openingSession === session.session_id ? "Opening…" : "Resume"}
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </div>
    );
}
