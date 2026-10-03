import { NavLink } from "react-router-dom";

function navClass({
    isActive,
}: {
    isActive: boolean;
}) {
    return `sidebar-link${isActive ? " active" : ""}`;
}

export default function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="sidebar-brand">
                <div className="sidebar-brand-title">
                    UHDP
                </div>

                <div className="sidebar-brand-subtitle">
                    Hardware Diagnostics
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="sidebar-section-title">
                    Platform
                </div>

                <NavLink
                    to="/"
                    end
                    className={navClass}
                    aria-label="Dashboard"
                >
                    <span aria-hidden="true">◈</span>
                    <span>Dashboard</span>
                </NavLink>

                <NavLink
                    to="/devices"
                    className={navClass}
                    aria-label="Devices"
                >
                    <span aria-hidden="true">◉</span>
                    <span>Devices</span>
                </NavLink>

                <NavLink
                    to="/diagnostics"
                    className={navClass}
                    aria-label="Diagnostics"
                >
                    <span aria-hidden="true">✓</span>
                    <span>Diagnostics</span>
                </NavLink>

                <NavLink
                    to="/stress-testing"
                    className={navClass}
                    aria-label="CPU stress testing"
                >
                    <span aria-hidden="true">◷</span>
                    <span>Stress Testing</span>
                </NavLink>

                <NavLink
                    to="/diagnostic-jobs"
                    className={navClass}
                    aria-label="Other long-running diagnostic jobs"
                >
                    <span aria-hidden="true">◴</span>
                    <span>Test Jobs</span>
                </NavLink>

                <NavLink
                    to="/capabilities"
                    className={navClass}
                    aria-label="Diagnostic capabilities"
                >
                    <span aria-hidden="true">▦</span>
                    <span>Capabilities</span>
                </NavLink>

                <NavLink
                    to="/results"
                    className={navClass}
                    aria-label="Results"
                >
                    <span aria-hidden="true">▤</span>
                    <span>Results</span>
                </NavLink>

                <NavLink
                    to="/report"
                    className={navClass}
                    aria-label="Report"
                >
                    <span aria-hidden="true">▧</span>
                    <span>Report</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
                <span className="sidebar-footer-mark" aria-hidden="true">●</span>
                <span>Hardware health, clearly.</span>
            </div>
        </aside>
    );
}