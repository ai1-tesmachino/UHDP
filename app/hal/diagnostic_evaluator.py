from unittest import result

from app.hal.diagnostic_evaluation import (
    DiagnosticEvaluation,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.evaluation_status import (
    EvaluationStatus,
)


class DiagnosticEvaluator:

    def evaluate(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        diagnostic_type = (
            result.diagnostic_type.lower()
        )

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
            status=EvaluationStatus.UNKNOWN,
            warnings=[
                "No evaluation rules available"
            ],
        )

    def _evaluate_cpu(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        physical_cores = (
            result.details.get(
                "physical_cores",
                0,
            )
        )

        if physical_cores <= 0:
            return DiagnosticEvaluation(
                status=EvaluationStatus.FAILED,
                failures=[
                    "No CPU cores detected"
                ],
            )

        return DiagnosticEvaluation(
            status=EvaluationStatus.PASSED
        )

    def _evaluate_memory(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        total_gb = (
            result.details.get(
                "total_gb",
                0,
            )
        )

        if total_gb <= 0:
            return DiagnosticEvaluation(
                status=EvaluationStatus.FAILED,
                failures=[
                    "No memory detected"
                ],
            )

        if total_gb < 4:
            return DiagnosticEvaluation(
                status=EvaluationStatus.WARNING,
                warnings=[
                    "Less than 4 GB RAM"
                ],
            )

        return DiagnosticEvaluation(
            status=EvaluationStatus.PASSED
        )

    def _evaluate_storage(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        drive_count = (
            result.details.get(
                "drive_count",
                0,
            )
        )

        if drive_count <= 0:
            return DiagnosticEvaluation(
                status=EvaluationStatus.FAILED,
                failures=[
                    "No storage devices detected"
                ],
                recommendations=[
                    "Verify storage device connection"
                ],
            )

        return DiagnosticEvaluation(
            status=EvaluationStatus.PASSED
        )

    def _evaluate_network(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        adapter_count = (
            result.details.get(
                "adapter_count",
                0,
            )
        )

        if adapter_count <= 0:
            return DiagnosticEvaluation(
                status=EvaluationStatus.FAILED,
                failures=[
                    "No network adapters detected"
                ],
            )

        return DiagnosticEvaluation(
            status=EvaluationStatus.PASSED
        )

    def _evaluate_battery(
        self,
        result: DiagnosticResult,
    ) -> DiagnosticEvaluation:

        battery_present = (
            result.details.get(
                "battery_present",
                False,
            )
        )

        if not battery_present:
            return DiagnosticEvaluation(
                status=EvaluationStatus.WARNING,
                warnings=[
                    "Battery not detected"
                ],
            )

        percent = (
            result.details.get(
                "percent",
                0,
            )
        )

        if percent < 10:
            return DiagnosticEvaluation(
                status=EvaluationStatus.WARNING,
                warnings=[
                    "Battery level below 10%"
                ],
                recommendations=[
                    "Connect charger"
                ],
            )

        return DiagnosticEvaluation(
            status=EvaluationStatus.PASSED
        )