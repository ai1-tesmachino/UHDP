from dataclasses import dataclass, field

from app.hal.evaluation_status import (
    EvaluationStatus,
)


@dataclass(slots=True)
class DiagnosticEvaluation:

    status: EvaluationStatus

    warnings: list[str] = field(
        default_factory=list
    )

    failures: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )