import {
    useLocation,
    useNavigate,
} from "react-router-dom";

interface DiagnosticResult {
    status?: string;
    message?: string;
    [key: string]: unknown;
}

interface ResultData {
    session_id?: string;
    device_id?: string;
    status?: string;
    workflow_status?: string;
    report?: {
        summary?: {
            total?: number;
            passed?: number;
            failed?: number;
            errors?: number;
        };
        data?: Record<
            string,
            DiagnosticResult
        >;
        [key: string]: unknown;
    };
    [key: string]: unknown;
}

function getStatusClass(
    status: unknown
): string {
    const value =
        String(status || "").toLowerCase();

    if (
        value === "pass" ||
        value === "passed" ||
        value === "success" ||
        value === "ok"
    ) {
        return "result-badge result-pass";
    }

    if (
        value === "fail" ||
        value === "failed" ||
        value === "error"
    ) {
        return "result-badge result-fail";
    }

    return "result-badge result-neutral";
}

export default function Results() {
    const location =
        useLocation();

    const navigate =
        useNavigate();

    const result =
        location.state as ResultData | null;

    if (!result) {
        return (
            <div className="card empty-state">
                <div className="empty-state-title">
                    No Results Available
                </div>

                <div>
                    Run a diagnostic session to view results.
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
                        Start Diagnostics
                    </button>
                </div>
            </div>
        );
    }

    const report =
        result.report;

    const summary =
        report?.summary;

    const diagnostics =
        Object.entries(
            report?.data || {}
        );

    const overallStatus =
        result.status ||
        result.workflow_status ||
        "Unknown";

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Diagnostic Results
                    </h1>

                    <p className="page-description">
                        Results from the completed hardware diagnostic session.
                    </p>
                </div>

                <div className="action-row">
                    <button
                        className="button button-secondary"
                        onClick={() =>
                            navigate("/devices")
                        }
                    >
                        New Diagnostic
                    </button>

                    <button
                        className="button button-primary"
                        onClick={() =>
                            navigate("/report", {
                                state: result,
                            })
                        }
                    >
                        View Report
                    </button>
                </div>
            </div>

            <div className="card">
                <div className="info-grid">
                    <div className="info-row">
                        <span className="info-label">
                            Session
                        </span>

                        <span className="info-value">
                            {result.session_id || "-"}
                        </span>
                    </div>

                    <div className="info-row">
                        <span className="info-label">
                            Device
                        </span>

                        <span className="info-value">
                            {result.device_id || "-"}
                        </span>
                    </div>

                    <div className="info-row">
                        <span className="info-label">
                            Status
                        </span>

                        <span className="info-value">
                            <span
                                className={getStatusClass(
                                    overallStatus
                                )}
                            >
                                {overallStatus}
                            </span>
                        </span>
                    </div>

                    <div className="info-row">
                        <span className="info-label">
                            Workflow
                        </span>

                        <span className="info-value">
                            {result.workflow_status ||
                                "-"}
                        </span>
                    </div>
                </div>
            </div>

            {summary && (
                <div
                    className="summary-grid"
                    style={{
                        marginTop: "20px",
                    }}
                >
                    <div className="summary-box">
                        <div className="summary-box-label">
                            Total
                        </div>

                        <div className="summary-box-value">
                            {summary.total ?? 0}
                        </div>
                    </div>

                    <div className="summary-box">
                        <div className="summary-box-label">
                            Passed
                        </div>

                        <div className="summary-box-value">
                            {summary.passed ?? 0}
                        </div>
                    </div>

                    <div className="summary-box">
                        <div className="summary-box-label">
                            Failed
                        </div>

                        <div className="summary-box-value">
                            {summary.failed ?? 0}
                        </div>
                    </div>

                    <div className="summary-box">
                        <div className="summary-box-label">
                            Errors
                        </div>

                        <div className="summary-box-value">
                            {summary.errors ?? 0}
                        </div>
                    </div>
                </div>
            )}

            <div
                className="card"
                style={{
                    marginTop: "20px",
                }}
            >
                <div className="page-header">
                    <div>
                        <h2
                            style={{
                                margin: 0,
                                fontSize: "19px",
                            }}
                        >
                            Diagnostics
                        </h2>

                        <p
                            className="muted"
                            style={{
                                marginBottom: 0,
                            }}
                        >
                            Individual diagnostic results.
                        </p>
                    </div>
                </div>

                {diagnostics.length === 0 ? (
                    <div className="empty-state">
                        No individual diagnostic results were returned.
                    </div>
                ) : (
                    <div className="result-table-wrapper">
                        <table className="result-table">
                            <thead>
                                <tr>
                                    <th>
                                        Diagnostic
                                    </th>

                                    <th>
                                        Status
                                    </th>

                                    <th>
                                        Message
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {diagnostics.map(
                                    ([
                                        key,
                                        value,
                                    ]) => (
                                        <tr
                                            key={key}
                                        >
                                            <td>
                                                <strong>
                                                    {
                                                        key
                                                    }
                                                </strong>
                                            </td>

                                            <td>
                                                <span
                                                    className={getStatusClass(
                                                        value?.status
                                                    )}
                                                >
                                                    {
                                                        value?.status ??
                                                        "-"
                                                    }
                                                </span>
                                            </td>

                                            <td>
                                                {
                                                    value?.message ??
                                                    "-"
                                                }
                                            </td>
                                        </tr>
                                    )
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}