from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DiagnosticRequest:
    diagnostic_id: str | None = None
    diagnostic_type: str = ""
    device_id: str = ""
    parameters: dict[str, Any] = field(
        default_factory=dict
    )
    run_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if self.diagnostic_id is None:
            self.diagnostic_id = self.diagnostic_type