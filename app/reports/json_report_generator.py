from app.reports.report_models import DiagnosticReport


class JsonReportGenerator:

    def generate(
        self,
        report: DiagnosticReport,
    ) -> dict:

        results = {}

        for diagnostic_name, result in report.results.items():

            if hasattr(
                result,
                "__dict__",
            ):
                results[diagnostic_name] = vars(result)
            else:
                results[diagnostic_name] = str(result)

        return {
            "report_id": report.report_id,
            "session_id": report.session_id,
            "device_id": report.device_id,
            "started_at": (
                report.started_at.isoformat()
                if report.started_at
                else None
            ),
            "completed_at": (
                report.completed_at.isoformat()
                if report.completed_at
                else None
            ),
            "overall_status": report.overall_status,
            "total_diagnostics": report.total_diagnostics,
            "passed_diagnostics": report.passed_diagnostics,
            "failed_diagnostics": report.failed_diagnostics,
            "results": results,
        }