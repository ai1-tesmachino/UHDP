import html
import json

from app.reports.json_report_generator import JsonReportGenerator
from app.reports.report_models import DiagnosticReport


class HtmlReportGenerator:

    def generate(
        self,
        report: DiagnosticReport,
    ) -> str:

        rows = []

        serialized_report = JsonReportGenerator().generate(report)
        for diagnostic_name, result in serialized_report["results"].items():
            evaluation = result.get("evaluation") if isinstance(result, dict) else None
            status = (
                evaluation.get("status")
                if isinstance(evaluation, dict)
                else result.get("status", "UNKNOWN")
                if isinstance(result, dict)
                else "UNKNOWN"
            )
            rows.append(
                f"""
                <tr>
                    <td>{html.escape(str(diagnostic_name))}</td>
                    <td>{html.escape(str(status))}</td>
                    <td><pre>{html.escape(json.dumps(result, ensure_ascii=False, indent=2))}</pre></td>
                </tr>
                """
            )

        results_table = "\n".join(rows)
        asset_id = getattr(report, "asset_id", None)

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>UHDP Diagnostic Report</title>
</head>
<body>

    <h1>UHDP Diagnostic Report</h1>

    <h2>Session Information</h2>

    <p><strong>Report ID:</strong> {html.escape(str(report.report_id))}</p>
    <p><strong>Session ID:</strong> {html.escape(str(report.session_id))}</p>
    <p><strong>Asset ID:</strong> {html.escape(str(asset_id or ""))}</p>
    <p><strong>Device ID:</strong> {html.escape(str(report.device_id))}</p>

    <h2>Summary</h2>

    <p><strong>Status:</strong> {html.escape(str(report.overall_status))}</p>
    <p><strong>Total Diagnostics:</strong> {report.total_diagnostics}</p>
    <p><strong>Passed:</strong> {report.passed_diagnostics}</p>
    <p><strong>Failed:</strong> {report.failed_diagnostics}</p>

    <h2>Timestamps</h2>

    <p><strong>Started:</strong> {html.escape(str(report.started_at))}</p>
    <p><strong>Completed:</strong> {html.escape(str(report.completed_at))}</p>

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