from dataclasses import dataclass
from dataclasses import field

from app.diagnostics.models.diagnostic_result import (
    DiagnosticResult,
)


@dataclass(slots=True)
class DiagnosticSessionResult:
    results: list[DiagnosticResult] = field(
        default_factory=list,
    )

    def add_result(
        self,
        result: DiagnosticResult,
    ) -> None:
        self.results.append(result)

    @property
    def passed(
        self,
    ) -> int:
        return len(
            [
                r
                for r in self.results
                if r.status.value == "passed"
            ]
        )

    @property
    def failed(
        self,
    ) -> int:
        return len(
            [
                r
                for r in self.results
                if r.status.value == "failed"
            ]
        )