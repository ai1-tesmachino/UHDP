from dataclasses import dataclass, field

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.models.diagnostic_summary import DiagnosticSummary


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
        summary = DiagnosticSummary(
            total=len(self.results)
        )

        for result in self.results:
            if result.status == DiagnosticStatus.PASSED:
                summary.passed += 1

            elif result.status == DiagnosticStatus.FAILED:
                summary.failed += 1

            elif result.status == DiagnosticStatus.ERROR:
                summary.errors += 1

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