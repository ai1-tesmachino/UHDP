from __future__ import annotations

import json
from pathlib import Path

from app.workflows.workflow import Workflow

from app.workflows.persistence.repository import (
    WorkflowRepository,
)

from app.workflows.persistence.serializer import (
    WorkflowSerializer,
)

from app.workflows.persistence.default_serializers import (
    create_default_serializer,
)

from app.workflows.validation.validator import (
    WorkflowValidator,
    create_default_validator,
)

from app.workflows.validation.validation_exception import (
    ValidationException,
)


class FileWorkflowRepository(
    WorkflowRepository,
):

    def __init__(
        self,
        root_path: str | Path,
        serializer: WorkflowSerializer | None = None,
        validator: WorkflowValidator | None = None,
    ) -> None:
        self._root_path = Path(
            root_path
        )

        self._root_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._serializer = (
            serializer
            or create_default_serializer()
        )

        self._validator = (
            validator
            or create_default_validator()
        )

    def save(
        self,
        workflow: Workflow,
    ) -> None:
        result = self._validator.validate(
            workflow
        )

        if not result.is_valid:
            raise ValidationException(
                result
            )

        path = self._workflow_path(
            workflow.name
        )

        data = self._serializer.serialize(
            workflow
        )

        path.write_text(
            json.dumps(
                data,
                indent=4,
            ),
            encoding="utf-8",
        )

    def load(
        self,
        name: str,
    ) -> Workflow:
        path = self._workflow_path(
            name
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Workflow not found: {name}"
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return self._serializer.deserialize(
            data
        )

    def delete(
        self,
        name: str,
    ) -> None:
        path = self._workflow_path(
            name
        )

        if not path.exists():
            return

        path.unlink()

    def list(
        self,
    ) -> list[str]:
        return sorted(
            path.stem
            for path in self._root_path.glob(
                "*.json"
            )
        )

    def exists(
        self,
        name: str,
    ) -> bool:
        return self._workflow_path(
            name
        ).exists()

    def _workflow_path(
        self,
        name: str,
    ) -> Path:
        return (
            self._root_path
            / f"{name}.json"
        )