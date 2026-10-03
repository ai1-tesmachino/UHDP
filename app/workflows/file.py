from pathlib import Path
from typing import Any
import json


class WorkflowFile:

    def __init__(
        self,
        path: str | Path,
    ) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def save(
        self,
        workflow_id: str,
        data: dict[str, Any],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = dict(data)
        payload.setdefault(
            "workflow_id",
            workflow_id,
        )

        self._path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            raise FileNotFoundError(
                self._path,
            )

        return json.loads(
            self._path.read_text(
                encoding="utf-8",
            )
        )

    def exists(self) -> bool:
        return self._path.exists()

    def delete(self) -> None:
        if self._path.exists():
            self._path.unlink()