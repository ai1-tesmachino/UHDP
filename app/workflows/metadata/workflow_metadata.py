from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from datetime import UTC
from datetime import datetime

from app.workflows.metadata.workflow_version import (
    WorkflowVersion,
)


@dataclass(
    slots=True,
)
class WorkflowMetadata:
    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )

    version: WorkflowVersion = field(
        default_factory=WorkflowVersion
    )

    def touch(
        self,
    ) -> None:
        self.updated_at = datetime.now(
            UTC
        )