from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from app.core.config import get_settings
from app.persistence.session_serialization import json_value


_SAFE_REPORT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class LocalReportFiles:
    def __init__(self) -> None:
        self._root = Path(get_settings().DATA_DIR) / "Reports"

    def save_revision(
        self,
        report_id: str,
        revision: int,
        payload: dict[str, Any],
        html: str | None,
    ) -> None:
        if not _SAFE_REPORT_ID.fullmatch(report_id) or report_id in {".", ".."}:
            raise ValueError("Report ID contains unsupported filename characters.")
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._root, 0o700)
        report_directory = self._root / report_id
        report_directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(report_directory, 0o700)
        directory = report_directory / f"REV_{revision:06d}"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        serialized = json.dumps(
            json_value(payload),
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        _atomic_write(directory / "report.json", serialized)
        if html is not None:
            _atomic_write(directory / "report.html", html.encode("utf-8"))
        _fsync_directory(directory)
        _fsync_directory(report_directory)
        _fsync_directory(self._root)


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".incoming-",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            os.chmod(temporary_path, 0o600)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
