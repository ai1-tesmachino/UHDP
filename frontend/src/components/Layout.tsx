import { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import WorkflowSteps from "./WorkflowSteps";
import { useQcSession } from "../session/SessionContext";
import { rememberQcPath, getSessionDeviceName, getSessionSerialNumber } from "../session/workflow";
import { getStationProfile } from "../station";
import { useTheme } from "../theme/ThemeProvider";
import { PageContainer } from "./shared/PageContainer";

interface Props {
    children: ReactNode;
}

export default function Layout({ children }: Props) {
    const location = useLocation();
    const { activeSession } = useQcSession();
    const { theme, toggleTheme } = useTheme();
    const [collapsed, setCollapsed] = useState(() => localStorage.getItem("uhdp.sidebar.collapsed") === "true");
    const [mobileOpen, setMobileOpen] = useState(false);
    const closeMobile = useCallback(() => setMobileOpen(false), []);
    const toggleSidebar = useCallback(() => {
        if (window.matchMedia("(max-width: 800px)").matches) {
            setMobileOpen((open) => !open);
        } else {
            setCollapsed((value) => !value);
        }
    }, []);
    const toggleSidebarCollapse = useCallback(() => {
        if (window.matchMedia("(max-width: 800px)").matches) {
            setMobileOpen(false);
        } else {
            setCollapsed((value) => !value);
        }
    }, []);
    const hiddenContextPaths = ["/", "/sessions", "/history", "/reports", "/active-qc", "/setup", "/settings"];
    const isNewIntake = new URLSearchParams(location.search).get("new") === "1";
    const showQcContext = Boolean(
        activeSession &&
        !isNewIntake &&
        !hiddenContextPaths.some((path) =>
            path === "/settings"
                ? location.pathname.startsWith("/settings/")
                : location.pathname === path,
        ),
    );
    const intake = activeSession?.intake_record || {};
    const technician = typeof intake.technician === "string" && intake.technician
        ? intake.technician
        : getStationProfile()?.technician || "Not assigned";

    useEffect(() => {
        localStorage.setItem("uhdp.sidebar.collapsed", String(collapsed));
    }, [collapsed]);

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

    if (location.pathname.startsWith("/quality-control/")) {
        return <>{children}</>;
    }

    return (
        <div className={`app-shell${collapsed ? " sidebar-collapsed" : ""}`}>
            <a className="skip-link" href="#main-content">Skip to content</a>
            <Sidebar
                collapsed={collapsed}
                mobileOpen={mobileOpen}
                onToggleCollapsed={toggleSidebarCollapse}
                onCloseMobile={closeMobile}
            />

            <div className="main-shell">
                <Navbar onToggleSidebar={toggleSidebar} onToggleTheme={toggleTheme} theme={theme} />

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

                <PageContainer className="content" id="main-content" tabIndex={-1}>
                    {children}
                </PageContainer>
            </div>
        </div>
    );
}