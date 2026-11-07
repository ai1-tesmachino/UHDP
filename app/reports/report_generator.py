from uuid import NAMESPACE_URL, uuid5

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
        if not isinstance(session_results, dict):
            session_results = {}

        for diagnostic_name, result in session_results.items():

            results[diagnostic_name] = result

            status = self._result_status(result)

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

        statuses = [self._result_status(result) for result in results.values()]
        if failed:
            overall_status = "FAIL"
        elif not statuses:
            overall_status = "INCOMPLETE"
        elif all(status in {"NOT_APPLICABLE", "NA"} for status in statuses):
            overall_status = "NOT_APPLICABLE"
        elif all(
            status in {"PASS", "PASSED", "SUCCESS", "NOT_APPLICABLE", "NA"}
            for status in statuses
        ):
            overall_status = "PASS"
        elif "WARNING" in statuses:
            overall_status = "WARNING"
        else:
            overall_status = "INCOMPLETE"

        session_id = str(session.session_id)
        report_id = str(uuid5(NAMESPACE_URL, f"uhdp-report:{session_id}"))

        return DiagnosticReport(
            report_id=report_id,
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
            total_diagnostics=len(statuses),
            passed_diagnostics=passed,
            failed_diagnostics=failed,
            results=results,
        )

    @staticmethod
    def _result_status(result) -> str:
        if isinstance(result, dict):
            evaluation = result.get("evaluation")
            status = (
                evaluation.get("status")
                if isinstance(evaluation, dict)
                else result.get("status", "")
            )
        else:
            evaluation = getattr(result, "evaluation", None)
            status = (
                getattr(evaluation, "status", None)
                if evaluation is not None
                else getattr(result, "status", "")
            )
        return str(getattr(status, "value", status)).upper()