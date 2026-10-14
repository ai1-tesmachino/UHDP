import { NavLink } from "react-router-dom";

function navClass({ isActive }: { isActive: boolean }) {
    return `sidebar-link${isActive ? " active" : ""}`;
}

export default function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="sidebar-brand">
                <div className="sidebar-brand-title">UHDP</div>
                <div className="sidebar-brand-subtitle">Laptop inspection</div>
            </div>

            <nav className="sidebar-nav" aria-label="Main navigation">
                <NavLink to="/" end className={navClass}>
                    <span aria-hidden="true">⌂</span>
                    <span>Home</span>
                </NavLink>
                <NavLink to="/devices" className={navClass}>
                    <span aria-hidden="true">＋</span>
                    <span>Start inspection</span>
                </NavLink>
                <NavLink to="/setup" className={navClass}>
                    <span aria-hidden="true">⚙</span>
                    <span>Station setup</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
                <span className="sidebar-footer-mark" aria-hidden="true">●</span>
                <span>Follow each step as it appears.</span>
            </div>
        </aside>
    );
}
