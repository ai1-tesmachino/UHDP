from dataclasses import dataclass, field


@dataclass(slots=True)
class DiagnosticProfile:
    name: str
    diagnostics: list[str] = field(default_factory=list)
    description: str = ""