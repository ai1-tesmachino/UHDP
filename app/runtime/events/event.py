from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import uuid4
from typing import Any


@dataclass(slots=True)
class Event:
    """
    Base runtime event.
    """

    event_type: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )