import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getHealth } from "../api/health";
import { getDevices } from "../api/devices";
import { getDiagnostics } from "../api/diagnostics";

export default function Dashboard() {
    const [online, setOnline] =
        useState<boolean | null>(null);

    const [deviceCount, setDeviceCount] =
        useState(0);

    const [diagnosticCount, setDiagnosticCount] =
        useState(0);

    const [loading, setLoading] =
        useState(true);

    async function loadDashboard() {
        setLoading(true);

        try {
            const [
                healthResult,
                devicesResult,
                diagnosticsResult,
            ] = await Promise.allSettled([
                getHealth(),
                getDevices(),
                getDiagnostics(),
            ]);

            setOnline(
                healthResult.status === "fulfilled"
            );

            if (
                devicesResult.status === "fulfilled"
            ) {
                setDeviceCount(
                    devicesResult.value.length
                );
            }

            if (
                diagnosticsResult.status === "fulfilled"
            ) {
                setDiagnosticCount(
                    diagnosticsResult.value.length
                );
            }
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadDashboard();
    }, []);

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Dashboard
                    </h1>

                    <p className="page-description">
                        Hardware diagnostics and system overview.
                    </p>
                </div>

                <button
                    className="button button-secondary"
                    onClick={loadDashboard}
                    disabled={loading}
                >
                    {loading ? "Refreshing..." : "Refresh"}
                </button>
            </div>

            <div className="card-grid">
                <div className="status-card">
                    <div className="status-card-label">
                        Backend
                    </div>

                    <div className="status-card-value">
                        {online === null
                            ? "..."
                            : online
                              ? "Online"
                              : "Offline"}
                    </div>

                    <div className="status-card-detail">
                        FastAPI service
                    </div>
                </div>

                <div className="status-card">
                    <div className="status-card-label">
                        Devices
                    </div>

                    <div className="status-card-value">
                        {deviceCount}
                    </div>

                    <div className="status-card-detail">
                        Discovered hardware
                    </div>
                </div>

                <div className="status-card">
                    <div className="status-card-label">
                        Diagnostics
                    </div>

                    <div className="status-card-value">
                        {diagnosticCount}
                    </div>

                    <div className="status-card-detail">
                        Available tests
                    </div>
                </div>

                <div className="status-card">
                    <div className="status-card-label">
                        Mode
                    </div>

                    <div className="status-card-value">
                        QA
                    </div>

                    <div className="status-card-detail">
                        Non-destructive testing
                    </div>
                </div>
            </div>

            <div
                style={{
                    marginTop: "24px",
                }}
                className="card"
            >
                <h2 style={{ marginTop: 0 }}>
                    Start Diagnostics
                </h2>

                <p className="muted">
                    Discover the machine hardware and select
                    the diagnostics you want to run.
                </p>

                <div className="action-row">
                    <Link
                        to="/devices"
                        className="button button-primary"
                    >
                        Discover Device
                    </Link>

                    <Link
                        to="/diagnostics"
                        className="button button-secondary"
                    >
                        Select Diagnostics
                    </Link>
                </div>
            </div>
        </div>
    );
}