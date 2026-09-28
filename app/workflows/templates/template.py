from __future__ import annotations

from dataclasses import dataclass

from app.workflows.workflow import Workflow


@dataclass(
    slots=True,
)
class WorkflowTemplate:
    name: str

    description: str

    workflow: Workflow