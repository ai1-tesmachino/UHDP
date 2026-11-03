from dataclasses import dataclass, field

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.models.diagnostic_summary import DiagnosticSummary
from app.hal.evaluation_status import (
    EvaluationStatus,
)

@dataclass(slots=True)
class DiagnosticResultCollection:
    results: list[DiagnosticResult] = field(
        default_factory=list
    )

    def add(
        self,
        result: DiagnosticResult,
    ) -> None:
        self.results.append(result)

    def extend(
        self,
        results: list[DiagnosticResult],
    ) -> None:
        self.results.extend(results)

    def summary(self) -> DiagnosticSummary:

        valid_results = [
            result
            for result in self.results
            if result is not None
        ]

        summary = DiagnosticSummary(
            total=len(valid_results)
        )

        for result in valid_results:
            outcome = (
                result.evaluation.status
                if result.evaluation is not None
                else result.status
            )
            try:
                outcome = EvaluationStatus(outcome)
            except (TypeError, ValueError):
                try:
                    outcome = DiagnosticStatus(outcome)
                except (TypeError, ValueError):
                    continue

            if outcome == EvaluationStatus.PASSED:
                summary.passed += 1

            elif outcome == EvaluationStatus.WARNING:
                summary.warnings += 1

            elif outcome == EvaluationStatus.FAILED:
                summary.failed += 1

            elif outcome == EvaluationStatus.ERROR:
                summary.errors += 1
            elif outcome == EvaluationStatus.NOT_APPLICABLE:
                summary.not_applicable += 1
            elif outcome == EvaluationStatus.UNSUPPORTED:
                summary.unsupported += 1
            elif outcome == EvaluationStatus.SKIPPED:
                summary.not_run += 1
            elif outcome == EvaluationStatus.CANCELLED:
                summary.cancelled += 1
            elif outcome == EvaluationStatus.INCONCLUSIVE:
                summary.inconclusive += 1
            elif outcome in {DiagnosticStatus.PENDING, DiagnosticStatus.RUNNING}:
                summary.not_run += 1

        return summary


    def get(
        self,
        diagnostic_id: str,
    ) -> DiagnosticResult | None:
        for result in self.results:
            if result.diagnostic_id == diagnostic_id:
                return result

        return None

    def by_type(
        self,
        diagnostic_type: str,
    ) -> list[DiagnosticResult]:
        return [
            result
            for result in self.results
            if result.diagnostic_type == diagnostic_type
        ]

    def clear(self) -> None:
        self.results.clear()

    def __len__(self) -> int:
        return len(self.results)