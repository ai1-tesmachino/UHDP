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
                >
                    ◈ Dashboard
                </NavLink>

                <NavLink
                    to="/devices"
                    className={navClass}
                >
                    ◉ Devices
                </NavLink>

                <NavLink
                    to="/diagnostics"
                    className={navClass}
                >
                    ✓ Diagnostics
                </NavLink>

                <NavLink
                    to="/results"
                    className={navClass}
                >
                    ▤ Results
                </NavLink>

                <NavLink
                    to="/report"
                    className={navClass}
                >
                    ▧ Report
                </NavLink>
            </nav>
        </aside>
    );
}