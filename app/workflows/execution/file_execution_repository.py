from __future__ import annotations

import json

from pathlib import Path

from datetime import datetime

from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.execution_repository import (
    ExecutionRepository,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


class FileExecutionRepository(
    ExecutionRepository,
):

    def __init__(
        self,
        root_path: str | Path,
    ) -> None:
        self._root_path = Path(
            root_path
        )

        self._root_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        record: ExecutionRecord,
    ) -> None:
        path = self._record_path(
            record.execution_id
        )

        path.write_text(
            json.dumps(
                self._serialize(
                    record
                ),
                indent=4,
            ),
            encoding="utf-8",
        )

    def load(
        self,
        execution_id: str,
    ) -> ExecutionRecord:
        path = self._record_path(
            execution_id
        )

        if not path.exists():
            raise FileNotFoundError(
                execution_id
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        return self._deserialize(
            data
        )

    def delete(
        self,
        execution_id: str,
    ) -> None:
        path = self._record_path(
            execution_id
        )

        if path.exists():
            path.unlink()

    def list(
        self,
    ) -> list[ExecutionRecord]:
        records: list[
            ExecutionRecord
        ] = []

        for path in sorted(
            self._root_path.glob(
                "*.json"
            )
        ):
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            records.append(
                self._deserialize(
                    data
                )
            )

        return records

    def exists(
        self,
        execution_id: str,
    ) -> bool:
        return self._record_path(
            execution_id
        ).exists()

    def _record_path(
        self,
        execution_id: str,
    ) -> Path:
        return (
            self._root_path
            / f"{execution_id}.json"
        )

    def _serialize(
        self,
        record: ExecutionRecord,
    ) -> dict[str, object]:
        return {
            "execution_id": record.execution_id,
            "workflow_name": record.workflow_name,
            "status": record.status.value,
            "started_at": (
                record.started_at.isoformat()
                if record.started_at
                else None
            ),
            "completed_at": (
                record.completed_at.isoformat()
                if record.completed_at
                else None
            ),
            "error_message": (
                record.error_message
            ),
            "created_at": (
                record.created_at.isoformat()
            ),
        }

    def _deserialize(
        self,
        data: dict[str, object],
    ) -> ExecutionRecord:
        record = ExecutionRecord(
            workflow_name=str(
                data[
                    "workflow_name"
                ]
            ),
            execution_id=str(
                data[
                    "execution_id"
                ]
            ),
            status=ExecutionStatus(
                str(
                    data[
                        "status"
                    ]
                )
            ),
        )

        if data.get(
            "started_at"
        ):
            record.started_at = (
                datetime.fromisoformat(
                    str(
                        data[
                            "started_at"
                        ]
                    )
                )
            )

        if data.get(
            "completed_at"
        ):
            record.completed_at = (
                datetime.fromisoformat(
                    str(
                        data[
                            "completed_at"
                        ]
                    )
                )
            )

        if data.get(
            "error_message"
        ):
            record.error_message = str(
                data[
                    "error_message"
                ]
            )

        record.created_at = (
            datetime.fromisoformat(
                str(
                    data[
                        "created_at"
                    ]
                )
            )
        )

        return record