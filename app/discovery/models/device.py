from dataclasses import dataclass, field
from typing import Any


@dataclass
class Device:
    device_id: str
    device_type: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)