import {
    useLocation,
    useNavigate,
} from "react-router-dom";

export default function ReportViewer() {
    const location =
        useLocation();

    const navigate =
        useNavigate();

    const report =
        location.state;

    if (!report) {
        return (
            <div className="card empty-state">
                <div className="empty-state-title">
                    No Report Available
                </div>

                <div>
                    Complete a diagnostic session first.
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

    function downloadReport() {
        const blob =
            new Blob(
                [
                    JSON.stringify(
                        report,
                        null,
                        2
                    ),
                ],
                {
                    type: "application/json",
                }
            );

        const url =
            URL.createObjectURL(blob);

        const anchor =
            document.createElement("a");

        anchor.href = url;
        anchor.download =
            `uhdp-report-${
                report.session_id || "session"
            }.json`;

        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();

        URL.revokeObjectURL(url);
    }

    return (
        <div>
            <div className="page-header">
                <div>
                    <h1 className="page-title">
                        Report Viewer
                    </h1>

                    <p className="page-description">
                        Diagnostic session report.
                    </p>
                </div>

                <div className="action-row">
                    <button
                        className="button button-secondary"
                        onClick={() =>
                            navigate(-1)
                        }
                    >
                        Back
                    </button>

                    <button
                        className="button button-primary"
                        onClick={downloadReport}
                    >
                        Export JSON
                    </button>
                </div>
            </div>

            <div className="card">
                <h2
                    style={{
                        marginTop: 0,
                    }}
                >
                    Session Information
                </h2>

                <div className="info-grid">
                    <div className="info-row">
                        <span className="info-label">
                            Session ID
                        </span>

                        <span className="info-value">
                            {report.session_id ||
                                "-"}
                        </span>
                    </div>

                    <div className="info-row">
                        <span className="info-label">
                            Device ID
                        </span>

                        <span className="info-value">
                            {report.device_id ||
                                "-"}
                        </span>
                    </div>

                    <div className="info-row">
                        <span className="info-label">
                            Status
                        </span>

                        <span className="info-value">
                            {report.status ||
                                report.workflow_status ||
                                "-"}
                        </span>
                    </div>
                </div>
            </div>

            <div
                className="card"
                style={{
                    marginTop: "20px",
                }}
            >
                <h2
                    style={{
                        marginTop: 0,
                    }}
                >
                    Raw Report
                </h2>

                <pre className="report-json">
                    {JSON.stringify(
                        report,
                        null,
                        2
                    )}
                </pre>
            </div>
        </div>
    );
}