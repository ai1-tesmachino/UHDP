from uuid import uuid4

from app.reports.report_models import DiagnosticReport


class ReportGenerator:

    def generate(
        self,
        session,
    ) -> DiagnosticReport:

        results = {}

        passed = 0
        failed = 0

        session_results = getattr(
            session,
            "results",
            {},
        )

        for diagnostic_name, result in session_results.items():

            results[diagnostic_name] = result

            status = getattr(
                result,
                "status",
                "",
            )

            if hasattr(
                status,
                "value",
            ):
                status = status.value

            status = str(
                status
            ).upper()

            if status in (
                "PASS",
                "PASSED",
                "SUCCESS",
            ):
                passed += 1

            elif status in (
                "FAIL",
                "FAILED",
                "ERROR",
            ):
                failed += 1

        total = passed + failed

        overall_status = (
            "PASS"
            if failed == 0
            else "FAIL"
        )

        return DiagnosticReport(
            report_id=str(
                uuid4()
            ),
            session_id=session.session_id,
            device_id=session.device_id,
            started_at=getattr(
                session,
                "started_at",
                None,
            ),
            completed_at=getattr(
                session,
                "completed_at",
                None,
            ),
            overall_status=overall_status,
            total_diagnostics=total,
            passed_diagnostics=passed,
            failed_diagnostics=failed,
            results=results,
        )