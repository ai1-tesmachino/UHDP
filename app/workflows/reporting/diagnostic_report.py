from dataclasses import dataclass
from typing import Any


@dataclass
class DiagnosticReport:
    data: dict[str, Any]