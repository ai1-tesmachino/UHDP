import math
from numbers import Real

from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.diagnostics.display_tests import DISPLAY_TEST_IDS


class DiagnosticEvaluator:
    def evaluate(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        status = result.status
        try:
            status = DiagnosticStatus(status)
        except (TypeError, ValueError):
            return DiagnosticEvaluation(
                status=EvaluationStatus.INCONCLUSIVE,
                warnings=[f"Unrecognized diagnostic status: {status}"],
            )

        terminal_outcomes = {
            DiagnosticStatus.WARNING: EvaluationStatus.WARNING,
            DiagnosticStatus.FAILED: EvaluationStatus.FAILED,
            DiagnosticStatus.ERROR: EvaluationStatus.ERROR,
            DiagnosticStatus.SKIPPED: EvaluationStatus.SKIPPED,
            DiagnosticStatus.UNSUPPORTED: EvaluationStatus.UNSUPPORTED,
            DiagnosticStatus.NOT_APPLICABLE: EvaluationStatus.NOT_APPLICABLE,
            DiagnosticStatus.INCONCLUSIVE: EvaluationStatus.INCONCLUSIVE,
            DiagnosticStatus.CANCELLED: EvaluationStatus.CANCELLED,
            DiagnosticStatus.PENDING: EvaluationStatus.INCONCLUSIVE,
            DiagnosticStatus.RUNNING: EvaluationStatus.INCONCLUSIVE,
        }
        if status in terminal_outcomes:
            evaluation_status = terminal_outcomes[status]
            message = result.message or f"Diagnostic outcome: {status.value}"
            return DiagnosticEvaluation(
                status=evaluation_status,
                warnings=(
                    [message]
                    if evaluation_status
                    in {EvaluationStatus.WARNING, EvaluationStatus.INCONCLUSIVE}
                    else []
                ),
                failures=(
                    [message]
                    if evaluation_status is EvaluationStatus.FAILED
                    else []
                ),
            )

        diagnostic_type = result.diagnostic_type.lower()
        if diagnostic_type == "display_diagnostic":
            return self._evaluate_display(result)
        if diagnostic_type == "cpu":
            return self._evaluate_cpu(result)
        if diagnostic_type == "memory":
            return self._evaluate_memory(result)
        if diagnostic_type == "storage":
            return self._evaluate_storage(result)
        if diagnostic_type == "network":
            return self._evaluate_network(result)
        if diagnostic_type == "battery":
            return self._evaluate_battery(result)

        return DiagnosticEvaluation(
            status=EvaluationStatus.INCONCLUSIVE,
            warnings=["No evaluation rules available for this diagnostic"],
        )

    @staticmethod
    def _positive_number(value: object) -> Real | None:
        if (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or value <= 0
        ):
            return None
        try:
            if not math.isfinite(value):
                return None
        except OverflowError:
            return None
        return value

    @staticmethod
    def normalize_measurements(result: DiagnosticResult) -> dict[str, object]:
        details = result.details if isinstance(result.details, dict) else {}
        normalized: dict[str, object] = {}
        memory_mb = DiagnosticEvaluator._positive_number(
            details.get("total_ram_mb")
        )
        if memory_mb is not None:
            normalized["total_memory_bytes"] = memory_mb * 1024**2

        drives = details.get("drives")
        if isinstance(drives, list) and all(
            isinstance(drive, dict) for drive in drives
        ):
            normalized["drive_count"] = len(drives)
        return normalized

    def _evaluate_cpu(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        physical_cores = self._positive_number(
            result.details.get("physical_cores")
        )
        if physical_cores is None:
            return self._inconclusive(
                "A valid physical CPU core count was not available"
            )
        return DiagnosticEvaluation(status=EvaluationStatus.PASSED)

    def _evaluate_memory(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        total_bytes = self.normalize_measurements(result).get("total_memory_bytes")
        if not isinstance(total_bytes, Real) or isinstance(total_bytes, bool):
            return self._inconclusive(
                "A valid installed-memory capacity in MiB was not available"
            )
        try:
            valid_total = math.isfinite(total_bytes) and total_bytes > 0
        except OverflowError:
            valid_total = False
        if not valid_total:
            return self._inconclusive(
                "Installed-memory capacity could not be normalized to bytes"
            )
        return DiagnosticEvaluation(status=EvaluationStatus.PASSED)

    def _evaluate_storage(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        drive_count = self.normalize_measurements(result).get("drive_count")
        if not isinstance(drive_count, int):
            return self._inconclusive(
                "A valid storage-volume inventory was not available"
            )
        if drive_count == 0:
            return self._inconclusive(
                "No storage volumes were reported; physical-drive presence is unverified"
            )
        return DiagnosticEvaluation(status=EvaluationStatus.PASSED)

    def _evaluate_network(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        adapter_count = result.details.get("adapter_count")
        if (
            isinstance(adapter_count, bool)
            or not isinstance(adapter_count, int)
            or adapter_count < 0
        ):
            return self._inconclusive(
                "A valid network-adapter count was not available"
            )
        if adapter_count == 0:
            return self._inconclusive(
                "No network adapters were reported; hardware absence is unverified"
            )
        if result.details.get("connectivity_verified") is not True:
            return self._inconclusive(
                "Network adapter inventory was reported; connectivity was not verified"
            )
        return DiagnosticEvaluation(status=EvaluationStatus.PASSED)

    def _evaluate_battery(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        battery_present = result.details.get("battery_present")
        if not isinstance(battery_present, bool):
            return self._inconclusive(
                "Battery presence could not be determined"
            )
        if not battery_present:
            return DiagnosticEvaluation(
                status=EvaluationStatus.NOT_APPLICABLE,
                warnings=["No battery was reported"],
            )

        percent = result.details.get("percent")
        if percent is None:
            return self._inconclusive(
                "Battery charge percentage was not available"
            )
        if (
            isinstance(percent, bool)
            or not isinstance(percent, Real)
            or not math.isfinite(percent)
            or not 0 <= percent <= 100
        ):
            return self._inconclusive(
                "Battery charge percentage was malformed"
            )
        if percent < 10:
            return DiagnosticEvaluation(
                status=EvaluationStatus.WARNING,
                warnings=["Battery level below 10%"],
                recommendations=["Connect charger"],
            )
        return DiagnosticEvaluation(status=EvaluationStatus.PASSED)

    def _evaluate_display(self, result: DiagnosticResult) -> DiagnosticEvaluation:
        outcomes = result.details.get("test_outcomes")
        if not isinstance(outcomes, list) or len(outcomes) != len(DISPLAY_TEST_IDS):
            return self._inconclusive(
                "All required technician display assessments must be recorded"
            )
        if any(outcome == "failed" for outcome in outcomes):
            return DiagnosticEvaluation(
                status=EvaluationStatus.FAILED,
                failures=["Technician identified a display defect"],
            )
        if all(outcome == "passed" for outcome in outcomes):
            return DiagnosticEvaluation(status=EvaluationStatus.PASSED)
        if all(outcome in {"passed", "skipped", "inconclusive"} for outcome in outcomes):
            return self._inconclusive(
                "One or more display checks were skipped or inconclusive"
            )
        return self._inconclusive("Display test outcomes were invalid")

    @staticmethod
    def _inconclusive(message: str) -> DiagnosticEvaluation:
        return DiagnosticEvaluation(
            status=EvaluationStatus.INCONCLUSIVE,
            warnings=[message],
        )
