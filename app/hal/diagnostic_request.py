from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DiagnosticRequest:
    diagnostic_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    diagnostic_type: str = ""
    device_id: str = ""
    parameters: dict[str, Any] = field(
        default_factory=dict
    )