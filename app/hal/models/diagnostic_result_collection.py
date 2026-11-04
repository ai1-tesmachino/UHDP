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
        if isinstance(result.run_id, str) and result.run_id:
            existing = self.get_by_run_id(result.run_id)
            if existing is result or existing == result:
                return
            if existing is not None:
                raise ValueError(
                    f"Diagnostic run_id already exists: {result.run_id}"
                )
        self.results.append(result)

    def extend(
        self,
        results: list[DiagnosticResult],
    ) -> None:
        for result in results:
            self.add(result)

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
        matches = [
            result
            for result in self.results
            if result.diagnostic_id == diagnostic_id
        ]
        return matches[0] if len(matches) == 1 else None

    def get_by_run_id(self, run_id: str) -> DiagnosticResult | None:
        return next(
            (result for result in self.results if result.run_id == run_id),
            None,
        )

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