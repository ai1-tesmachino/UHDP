import { useEffect, useState } from "react";
import {
    useNavigate,
    useSearchParams,
} from "react-router-dom";

import { getDiagnostics } from "../api/diagnostics";

export default function DiagnosticSelection() {
    const [params] =
        useSearchParams();

    const navigate =
        useNavigate();

    const deviceId =
        params.get("deviceId") || "";

    const [diagnostics, setDiagnostics] =
        useState<string[]>([]);

    const [selected, setSelected] =
        useState<string[]>([]);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");

    async function loadDiagnostics() {
        setLoading(true);
        setError("");

        try {
            const data =
                await getDiagnostics();

            setDiagnostics(data);
        } catch {
            setError(
                "Failed to load available diagnostics."
            );
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadDiagnostics();
    }, []);

    function toggleDiagnostic(
        diagnostic: string
    ) {
        setSelected((current) =>
            current.includes(diagnostic)
                ? current.filter(
                      (item) => item !== diagnostic
                  )
                : [...current, diagnostic]
        );
    }

    function selectAll() {
        setSelected([...diagnostics]);
    }

    function clearAll() {
        setSelected([]);
    }

    function runSession() {
        if (
            !deviceId ||
            selected.length === 0
        ) {
            return;
        }

        navigate("/execution", {
            state: {
                deviceId,
                diagnostics: selected,
            },
        });
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Diagnostic Selection
                    </h1>

                    <p className="page-description">
                        Choose the automated diagnostics to execute.
                    </p>
                </div>

                <div className="action-row">
                    <button
                        className="button button-secondary"
                        onClick={selectAll}
                        disabled={
                            loading ||
                            diagnostics.length === 0
                        }
                    >
                        Select All
                    </button>

                    <button
                        className="button button-secondary"
                        onClick={clearAll}
                        disabled={
                            selected.length === 0
                        }
                    >
                        Clear
                    </button>
                </div>
            </div>

            <div
                className="card"
                style={{ marginBottom: "20px" }}
            >
                <div className="info-row">
                    <span className="info-label">
                        Device
                    </span>

                    <span className="info-value">
                        {deviceId || "Not selected"}
                    </span>
                </div>

                <div className="info-row">
                    <span className="info-label">
                        Selected
                    </span>

                    <span className="info-value">
                        {selected.length}
                    </span>
                </div>
            </div>

            {error && (
                <div
                    className="error-box"
                    style={{ marginBottom: "20px" }}
                >
                    {error}
                </div>
            )}

            {loading ? (
                <div className="card loading">
                    Loading diagnostics...
                </div>
            ) : (
                <div className="diagnostic-grid">
                    {diagnostics.map((diagnostic) => {
                        const isSelected =
                            selected.includes(
                                diagnostic
                            );

                        return (
                            <label
                                key={diagnostic}
                                className={`diagnostic-option ${
                                    isSelected
                                        ? "selected"
                                        : ""
                                }`}
                            >
                                <input
                                    className="diagnostic-checkbox"
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() =>
                                        toggleDiagnostic(
                                            diagnostic
                                        )
                                    }
                                />

                                <span className="diagnostic-name">
                                    {diagnostic}
                                </span>
                            </label>
                        );
                    })}
                </div>
            )}

            <div className="selection-footer">
                <div>
                    <strong>
                        {selected.length}
                    </strong>{" "}
                    diagnostic
                    {selected.length === 1
                        ? ""
                        : "s"} selected
                </div>

                <div className="action-row">
                    {!deviceId && (
                        <button
                            className="button button-secondary"
                            onClick={() =>
                                navigate("/devices")
                            }
                        >
                            Choose Device
                        </button>
                    )}

                    <button
                        className="button button-primary"
                        onClick={runSession}
                        disabled={
                            !deviceId ||
                            selected.length === 0
                        }
                    >
                        Run Diagnostics
                    </button>
                </div>
            </div>
        </div>
    );
}