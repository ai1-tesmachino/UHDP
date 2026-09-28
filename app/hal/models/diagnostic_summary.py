from dataclasses import dataclass


@dataclass(slots=True)
class DiagnosticSummary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0