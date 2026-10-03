import {
    useEffect,
    useState,
} from "react";

import {
    useLocation,
    useNavigate,
} from "react-router-dom";

import ProgressBar from "../components/ProgressBar";

import {
    createDiagnosticSession,
    runSession,
} from "../api/execution";

interface ExecutionState {
    deviceId: string;
    diagnostics: string[];
}

export default function Execution() {
    const location =
        useLocation();

    const navigate =
        useNavigate();

    const execution =
        location.state as ExecutionState | null;

    const deviceId =
        execution?.deviceId || "";

    const diagnostics =
        execution?.diagnostics || [];

    const [progress, setProgress] =
        useState(0);

    const [current, setCurrent] =
        useState("Preparing diagnostic session...");

    const [error, setError] =
        useState("");

    const [completed, setCompleted] =
        useState<string[]>([]);

    useEffect(() => {
        if (!deviceId || diagnostics.length === 0) {
            setError(
                "No device or diagnostics selected."
            );
            return;
        }

        let cancelled = false;

        async function execute() {
            try {
                setCurrent(
                    "Creating diagnostic session..."
                );
                setProgress(5);

                const session =
                    await createDiagnosticSession();

                if (cancelled) {
                    return;
                }

                const sessionId =
                    session.session_id;

                if (!sessionId) {
                    throw new Error(
                        "Diagnostic session ID was not returned."
                    );
                }

                setCurrent(
                    `Running ${diagnostics.length} diagnostic${
                        diagnostics.length === 1
                            ? ""
                            : "s"
                    }...`
                );
                setProgress(25);

                const results =
                    await runSession(
                        sessionId,
                        deviceId,
                        diagnostics
                    );

                if (cancelled) {
                    return;
                }

                setCompleted([
                    ...diagnostics,
                ]);

                setProgress(100);
                setCurrent(
                    "Diagnostics completed."
                );

                navigate("/results", {
                    state: results,
                    replace: true,
                });
            } catch (err) {
                if (cancelled) {
                    return;
                }

                console.error(
                    "Diagnostic execution failed:",
                    err
                );

                setError(
                    "Diagnostic execution failed. Check the backend logs for details."
                );

                setCurrent(
                    "Execution failed."
                );
            }
        }

        execute();

        return () => {
            cancelled = true;
        };
    }, []);

    if (error && !deviceId) {
        return (
            <div className="card empty-state">
                <div className="empty-state-title">
                    Diagnostic Session
                </div>

                <div
                    className="error-box"
                    style={{
                        marginTop: "16px",
                    }}
                >
                    {error}
                </div>

                <div
                    style={{
                        marginTop: "20px",
                    }}
                >
                    <button
                        className="button button-primary"
                        onClick={() =>
                            navigate("/devices")
                        }
                    >
                        Start Again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Diagnostic Execution
                    </h1>

                    <p className="page-description">
                        UHDP is executing the selected hardware tests.
                    </p>
                </div>
            </div>

            <div className="card execution-card">
                <div className="execution-status">
                    <div className="execution-status-title">
                        {current}
                    </div>

                    <div className="execution-status-detail">
                        Device: {deviceId}
                    </div>
                </div>

                <ProgressBar value={progress} />

                {error && (
                    <div
                        className="error-box"
                        style={{
                            marginTop: "24px",
                        }}
                    >
                        {error}
                    </div>
                )}

                <div className="execution-list">
                    {diagnostics.map(
                        (diagnostic) => (
                            <div
                                className="execution-item"
                                key={diagnostic}
                            >
                                <span>
                                    {diagnostic}
                                </span>

                                {completed.includes(
                                    diagnostic
                                ) ? (
                                    <span className="result-badge result-pass">
                                        Completed
                                    </span>
                                ) : (
                                    <span className="result-badge result-neutral">
                                        Pending
                                    </span>
                                )}
                            </div>
                        )
                    )}
                </div>

                {error && (
                    <div
                        style={{
                            marginTop: "24px",
                            textAlign: "center",
                        }}
                    >
                        <button
                            className="button button-secondary"
                            onClick={() =>
                                navigate(
                                    "/diagnostics",
                                    {
                                        replace: true,
                                    }
                                )
                            }
                        >
                            Return to Diagnostics
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}