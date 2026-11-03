import { ReactNode } from "react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import WorkflowSteps from "./WorkflowSteps";
import { useQcSession } from "../session/SessionContext";
import { rememberQcPath, getSessionDeviceName, getSessionSerialNumber } from "../session/workflow";
import { getStationProfile } from "../station";

interface Props {
    children: ReactNode;
}

export default function Layout({ children }: Props) {
    const location = useLocation();
    const { activeSession } = useQcSession();
    const hiddenContextPaths = ["/", "/history", "/reports", "/active-qc", "/setup", "/analytics", "/capabilities"];
    const isNewIntake = new URLSearchParams(location.search).get("new") === "1";
    const showQcContext = Boolean(activeSession && !isNewIntake && !hiddenContextPaths.includes(location.pathname));
    const intake = activeSession?.intake_record || {};
    const technician = typeof intake.technician === "string" && intake.technician
        ? intake.technician
        : getStationProfile()?.technician || "Not assigned";

    useEffect(() => {
        if (activeSession && !isNewIntake) {
            rememberQcPath(
                activeSession.session_id,
                location.pathname,
                location.search,
                location.hash,
            );
        }
    }, [activeSession?.session_id, isNewIntake, location.hash, location.pathname, location.search]);

    return (
        <div className="app-shell">
            <Sidebar />

            <div className="main-shell">
                <Navbar />

                {showQcContext && activeSession && (
                    <section className="qc-context-bar" aria-label="Current QC session">
                        <div className="qc-context-id">
                            <span className="eyebrow">CURRENT QC</span>
                            <strong>{activeSession.session_id}</strong>
                        </div>
                        <div className="qc-context-device">
                            <strong>{getSessionDeviceName(activeSession)}</strong>
                            <span>Serial: {getSessionSerialNumber(activeSession)}</span>
                        </div>
                        <div className="qc-context-meta">
                            <span>Technician: {technician}</span>
                            <span>Started: {new Date(activeSession.created_at).toLocaleString()}</span>
                        </div>
                        <span className={`qc-context-status ${["completed", "complete"].includes(activeSession.status.toLowerCase()) ? "is-complete" : ""}`}>
                            {activeSession.status.replaceAll("_", " ")}
                        </span>
                    </section>
                )}

                <WorkflowSteps />

                <main className="content">
                    {children}
                </main>
            </div>
        </div>
    );
}