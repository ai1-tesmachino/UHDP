from __future__ import annotations

import json

from pathlib import Path

from app.workflows.templates.template import (
    WorkflowTemplate,
)

from app.workflows.templates.template_repository import (
    TemplateRepository,
)

from app.workflows.persistence.serializer import (
    WorkflowSerializer,
)

from app.workflows.persistence.default_serializers import (
    create_default_serializer,
)


class FileTemplateRepository(
    TemplateRepository,
):

    def __init__(
        self,
        root_path: str | Path,
        serializer: WorkflowSerializer | None = None,
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

    def save(
        self,
        template: WorkflowTemplate,
    ) -> None:
        path = self._template_path(
            template.name
        )

        data = {
            "name": template.name,
            "description": template.description,
            "workflow": self._serializer.serialize(
                template.workflow
            ),
        }

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
    ) -> WorkflowTemplate:
        path = self._template_path(
            name
        )

        if not path.exists():
            raise FileNotFoundError(
                name
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return WorkflowTemplate(
            name=str(
                data["name"]
            ),
            description=str(
                data["description"]
            ),
            workflow=self._serializer.deserialize(
                data["workflow"]
            ),
        )

    def delete(
        self,
        name: str,
    ) -> None:
        path = self._template_path(
            name
        )

        if path.exists():
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
        return self._template_path(
            name
        ).exists()

    def _template_path(
        self,
        name: str,
    ) -> Path:
        return (
            self._root_path
            / f"{name}.json"
        )