from app.reports.report_models import DiagnosticReport


class HtmlReportGenerator:

    def generate(
        self,
        report: DiagnosticReport,
    ) -> str:

        rows = []

        for diagnostic_name, result in report.results.items():

            status = getattr(
                result,
                "status",
                "UNKNOWN",
            )

            details = getattr(
                result,
                "details",
                "",
            )

            rows.append(
                f"""
                <tr>
                    <td>{diagnostic_name}</td>
                    <td>{status}</td>
                    <td>{details}</td>
                </tr>
                """
            )

        results_table = "\n".join(rows)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>UHDP Diagnostic Report</title>
</head>
<body>

    <h1>UHDP Diagnostic Report</h1>

    <h2>Session Information</h2>

    <p><strong>Report ID:</strong> {report.report_id}</p>
    <p><strong>Session ID:</strong> {report.session_id}</p>
    <p><strong>Device ID:</strong> {report.device_id}</p>

    <h2>Summary</h2>

    <p><strong>Status:</strong> {report.overall_status}</p>
    <p><strong>Total Diagnostics:</strong> {report.total_diagnostics}</p>
    <p><strong>Passed:</strong> {report.passed_diagnostics}</p>
    <p><strong>Failed:</strong> {report.failed_diagnostics}</p>

    <h2>Timestamps</h2>

    <p><strong>Started:</strong> {report.started_at}</p>
    <p><strong>Completed:</strong> {report.completed_at}</p>

    <h2>Diagnostic Results</h2>

    <table border="1">
        <thead>
            <tr>
                <th>Diagnostic</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
        </thead>

        <tbody>
            {results_table}
        </tbody>

    </table>

</body>
</html>
"""